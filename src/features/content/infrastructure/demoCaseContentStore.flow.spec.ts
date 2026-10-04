import { describe, expect, it } from 'vitest'
import { additionalShowcaseDrafts, showcaseDraft } from '@/features/content/infrastructure/demoSeeds'
import { saveSession } from '@/features/identity/public'
import {
  demoAuthoring,
  demoCaseProblems,
  demoCloneCase,
  demoDecideCaseReview,
  demoPublishCase,
  demoReviewQueue,
  demoReviewView,
  demoSaveCaseDraft,
  demoDeleteCase,
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
  it('saves usable cases directly, permits author edits and hides deleted resources', () => {
    user('flow-author', 'teacher')
    const saved = demoSaveCaseDraft(demoDraftTitle('自定义病例', true))
    expect(saved).toMatchObject({ status: '已发布', medicalReviewStatus: 'not_required' })
    expect(demoAuthoring(saved.id)).toBeTruthy()
    expect(demoCaseProblems().find((item) => item.id === saved.id)?.allowedActions).toEqual(['edit', 'delete'])
    user('flow-other-author', 'teacher')
    expect(demoAuthoring(saved.id)).toBeUndefined()
    expect(() => demoSaveCaseDraft(showcaseDraft, saved.id)).toThrow('病例作者')
    expect(() => demoDeleteCase(saved.id)).toThrow('病例作者')
    expect(() => demoDeleteCase('pathology.cell-injury-showcase')).toThrow('系统病例只读')

    user('flow-author', 'teacher')
    const edited = demoSaveCaseDraft({ ...showcaseDraft, title: '修改后的病例' }, saved.id)
    expect(edited).toMatchObject({ id: saved.id, version: 2, medicalReviewStatus: 'not_required' })
    expect(() => demoPublishCase(saved.id)).toThrow('流程已退役')
    expect(() => demoSubmitCaseForReview(saved.id)).toThrow('流程已退役')
    const clone = demoCloneCase(saved.id)
    expect(clone?.id).not.toBe(saved.id)
    expect(clone?.medicalReviewStatus).toBe('not_required')
    demoDeleteCase(saved.id)
    expect(demoCaseProblems().some((item) => item.id === saved.id)).toBe(false)
    expect(demoAuthoring(saved.id)).toBeUndefined()
    expect(() => demoDeleteCase(saved.id)).not.toThrow()
    expect(() => demoSaveCaseDraft(showcaseDraft, saved.id)).toThrow('病例不存在')
    user('flow-student', 'student')
    expect(() => demoStart(saved.id)).toThrow('病例不存在')
  })

  it('keeps additional case sessions on their own facts and rubric', () => {
    user('flow-student', 'student')
    const problems = demoCaseProblems()
    expect(problems.map((item) => item.id)).toEqual(
      expect.arrayContaining(['pathology.cell-injury-showcase', ...Object.keys(additionalShowcaseDrafts)]),
    )
    const attempt = demoStart('pathology.inflammation-showcase')
    expect(attempt.problemVersion).toBe(1)
    expect(attempt.opening.chiefComplaint).toContain('证据')
    const first = demoMessage(attempt.id, '请问形态观察')
    expect(first.messages.at(-1)?.content).toContain('血流')
    const second = demoMessage(attempt.id, '再问一次形态')
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
      { stageId: 'tests', items: [{ testName: '形态', rationale: '证据', priority: 'necessary' }] },
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
    expect(demoAuthoring('pathology.cell-injury-showcase')).toBeUndefined()
    expect(() => demoCloneCase('pathology.cell-injury-showcase')).toThrow('只有教师')
    expect(() => demoStart('missing-case')).toThrow('病例不存在')
    expect(demoFind('missing-attempt')).toBeUndefined()
    expect(() => demoMessage('missing-attempt', '问题')).toThrow('病史阶段')
    expect(() => demoSubmit('missing-attempt', { stageId: 'history', summary: 'x', keyFindings: [] })).toThrow(
      '训练状态',
    )
    expect(() => demoComplete('missing-attempt')).toThrow('请先完成')
    user('flow-teacher', 'teacher')
    expect(() => demoPublishCase('missing-case')).toThrow('流程已退役')
    expect(() => demoSubmitCaseForReview('missing-case')).toThrow('流程已退役')
    expect(() => demoReviewQueue('rejected')).toThrow('医学审核权限')
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
