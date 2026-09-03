import { describe, expect, it } from 'vitest'
import { additionalShowcaseDrafts, showcaseDraft } from '@/features/content/infrastructure/demoSeeds'
import { saveSession } from '@/features/identity/public'
import {
  demoAuthoring,
  demoCaseProblems,
  demoCloneCase,
  demoDecideCaseReview,
  demoDraft,
  demoPublishCase,
  demoReviewQueue,
  demoReviewView,
  demoSaveCaseDraft,
  demoSubmitCaseForReview,
} from '@/features/content/infrastructure/demoCaseContentStore'
import {
  demoComplete,
  demoFind,
  demoMessage,
  demoStart,
  demoSubmit,
} from '@/features/training/infrastructure/demoCaseStore'

const user = (openid: string, role: 'teacher' | 'student', permissions?: string[]) =>
  saveSession({
    openid,
    role,
    nickName: openid,
    avatarUrl: '',
    permissions,
    createdAt: new Date(0).toISOString(),
  })

describe('Demo guided case state machine', () => {
  it('requires review, preserves author isolation and supports clone', () => {
    user('flow-author', 'teacher')
    expect(demoDraft('急性胸痛').title).toContain('急性胸痛')
    const saved = demoSaveCaseDraft(demoDraftTitle('自定义病例', true))
    expect(saved.medicalReviewStatus).toBe('not_submitted')
    expect(demoAuthoring(saved.id)).toBeTruthy()
    user('flow-other-author', 'teacher')
    expect(demoAuthoring(saved.id)).toBeUndefined()
    expect(() => demoSaveCaseDraft(showcaseDraft, saved.id)).toThrow('病例作者')

    user('flow-author', 'teacher')
    expect(demoSubmitCaseForReview(saved.id)?.medicalReviewStatus).toBe('pending')
    expect(() => demoSaveCaseDraft(showcaseDraft, saved.id)).toThrow('审核中的病例')
    user('demo_reviewer', 'teacher', ['medical_review'])
    expect(demoReviewQueue().some((item) => item.id === saved.id)).toBe(true)
    expect(demoReviewView(saved.id)?.caseDefinition).toBeTruthy()
    expect(() => demoDecideCaseReview(saved.id, 'rejected', '退回')).toThrow('至少需要 5')
    expect(demoDecideCaseReview(saved.id, 'rejected', '请补充危险鉴别')).toMatchObject({
      medicalReviewStatus: 'rejected',
    })

    user('flow-author', 'teacher')
    const edited = demoSaveCaseDraft(demoDraftTitle('修改后的病例', true), saved.id)
    expect(edited.medicalReviewStatus).toBe('not_submitted')
    demoSubmitCaseForReview(saved.id)
    user('demo_reviewer', 'teacher', ['medical_review'])
    demoDecideCaseReview(saved.id, 'approved', '')
    user('flow-author', 'teacher')
    expect(demoPublishCase(saved.id)).toMatchObject({ id: saved.id, status: '已发布' })
    expect(() => demoSaveCaseDraft(showcaseDraft, saved.id)).toThrow('已审核病例')
    const clone = demoCloneCase(saved.id)
    expect(clone?.id).not.toBe(saved.id)
    expect(clone?.medicalReviewStatus).toBe('not_submitted')
  })

  it('keeps additional case sessions on their own facts and rubric', () => {
    user('flow-student', 'student')
    const problems = demoCaseProblems()
    expect(problems.map((item) => item.id)).toEqual(
      expect.arrayContaining(['cap-undergraduate-showcase', ...Object.keys(additionalShowcaseDrafts)]),
    )
    const attempt = demoStart('acute-chest-pain-undergraduate-showcase')
    expect(attempt.problemVersion).toBe(1)
    expect(attempt.opening.chiefComplaint).toContain('胸痛')
    const first = demoMessage(attempt.id, '请问心电图结果')
    expect(first.messages.at(-1)?.content).toContain('缺血性')
    const second = demoMessage(attempt.id, '再问一次心电图')
    expect(second.messages.at(-1)?.content).toContain('具体了解')
    demoMessage(attempt.id, '还有什么情况？')
    for (const stage of [
      { stageId: 'history', summary: '病史', keyFindings: [] },
      { stageId: 'problem_representation', summary: '问题表征' },
      {
        stageId: 'differential',
        items: [
          { diagnosis: '急性冠脉综合征', supportingEvidence: [], opposingEvidence: [] },
          { diagnosis: '肺栓塞', supportingEvidence: [], opposingEvidence: [] },
        ],
      },
      { stageId: 'tests', items: [{ testName: '心电图', rationale: '证据', priority: 'necessary' }] },
      { stageId: 'management', items: [{ action: '监护', rationale: '安全' }], safetyConsiderations: ['复评'] },
    ] as never[]) {
      demoSubmit(attempt.id, stage as never)
    }
    const assessment = demoComplete(attempt.id)
    expect(assessment.focusStage).toBeTruthy()
    expect(demoFind(attempt.id)?.assessmentReady).toBe(true)
  })

  it('rejects unauthorised and invalid state transitions', () => {
    user('flow-student', 'student')
    expect(demoAuthoring('cap-undergraduate-showcase')).toBeUndefined()
    expect(() => demoCloneCase('cap-undergraduate-showcase')).toThrow('只有教师')
    expect(() => demoStart('missing-case')).toThrow('病例不存在')
    expect(demoFind('missing-attempt')).toBeUndefined()
    expect(() => demoMessage('missing-attempt', '问题')).toThrow('病史阶段')
    expect(() => demoSubmit('missing-attempt', { stageId: 'history', summary: 'x', keyFindings: [] })).toThrow(
      '训练状态',
    )
    expect(() => demoComplete('missing-attempt')).toThrow('请先完成')
    user('flow-teacher', 'teacher')
    expect(demoPublishCase('missing-case')).toBeUndefined()
    expect(() => demoSubmitCaseForReview('missing-case')).toThrow('病例作者')
    expect(demoReviewQueue('rejected')).toEqual([])
    expect(() => demoReviewView('missing-case')).toThrow('医学审核权限')
    expect(() => demoDecideCaseReview('missing-case', 'approved', '')).toThrow('医学审核权限')
  })
})

function demoDraftTitle(topic: string, source = false) {
  if (source) return structuredClone(showcaseDraft)
  const draft = structuredClone(showcaseDraft)
  draft.title = topic
  return draft
}
