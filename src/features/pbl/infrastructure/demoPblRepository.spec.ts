import { beforeEach, describe, expect, it, vi } from 'vitest'
import { DemoPblRepository, configureDemoLearningRouteCompletion } from './demoPblRepository'
import { saveSession } from '@/features/identity/public'
import { DemoContentRepository } from '@/features/content/infrastructure/demoContentRepository'

const routeId = '11111111-1111-4111-8111-111111111111'
const testId = '22222222-2222-4222-8222-222222222222'
const completion = vi.fn(async () => ({
  learningRouteId: routeId,
  finalTestId: testId,
  routeGenerationState: 'published',
  testGenerationState: 'ready',
}))
function login(role: 'student' | 'teacher', openid: string) {
  saveSession({ role, openid, nickName: openid, avatarUrl: '', createdAt: new Date(0).toISOString() })
}
const repository = () => {
  const repo = new DemoPblRepository(new DemoContentRepository())
  configureDemoLearningRouteCompletion(completion)
  return repo
}
beforeEach(() => {
  vi.clearAllMocks()
  uni.removeStorageSync('pbl:t44-demo')
  configureDemoLearningRouteCompletion(completion)
  login('student', 'demo_student')
})
describe('T44 Demo PBL completion and persistence', () => {
  it('persists participation starts and keeps undated history readonly without manufacturing timestamps', async () => {
    const repo = repository()
    login('student', 'new-discussion-student')
    const joined = await repo.participation('demo-pbl-1')
    expect(joined.startedAt).toBeTruthy()
    const reopened = repository()
    expect((await reopened.participation('demo-pbl-1')).startedAt).toBe(joined.startedAt)
    await expect(reopened.teacherDiscussionRecords()).rejects.toMatchObject({ code: 'FORBIDDEN' })
    login('teacher', 'demo_teacher')
    const facts = await reopened.teacherDiscussionRecords()
    const fresh = facts.find((item) => item.startedAt === joined.startedAt)!
    expect(fresh).toMatchObject({
      startedAt: joined.startedAt,
      phase: 'problem_framing',
      status: 'active',
      completedAt: null,
    })
    expect(facts.every((item) => item.sessionId === 'demo-pbl-1')).toBe(true)
    expect(Object.keys(fresh).sort()).toEqual(
      [
        'participationId',
        'sessionId',
        'classId',
        'studentId',
        'studentName',
        'phase',
        'status',
        'startedAt',
        'completedAt',
      ].sort(),
    )
    const stored = uni.getStorageSync('pbl:t44-demo') as { histories: Array<[string, { startedAt?: string }]> }
    for (const [, participation] of stored.histories) delete participation.startedAt
    uni.setStorageSync('pbl:t44-demo', stored)
    const historical = repository()
    expect((await historical.teacherDiscussionRecords()).every((item) => item.startedAt === null)).toBe(true)
    login('teacher', 'other-teacher')
    await expect(historical.teacherDiscussionRecords()).rejects.toMatchObject({ code: 'RESOURCE_NOT_FOUND' })
  })

  it('projects only effective classroom completion findings for teacher insights', async () => {
    const repo = repository()
    await repo.message('demo-pbl-1', '课堂最终推理', 't53-classroom', 'guided')
    await repo.message('demo-pbl-1', 'PRIVATE FOLLOW UP', 't53-private', 'direct')
    await repo.message('demo-t44-autonomous', 'PRIVATE AUTONOMOUS', 't53-autonomous', 'guided')
    login('teacher', 'demo_teacher')
    const facts = await repo.teacherInsightsRecords()
    expect(facts).toHaveLength(1)
    expect(facts[0]).toMatchObject({ sessionId: 'demo-pbl-1', classId: 1, studentId: 1 })
    expect(facts[0].knowledgeGaps[0]).toEqual({
      code: 'pathology.inflammation.vascular',
      summary: '血管变化的解释不完整',
    })
    expect(JSON.stringify(facts)).not.toMatch(/PRIVATE|evidence_message_ids|evidence_summary|messages/)
    const persisted = uni.getStorageSync('pbl:t44-demo')
    const history = persisted.histories.find(([key]: [string, unknown]) => key === 'demo_student:demo-pbl-1')
    history[1].evidenceCompletedRevision += 1
    uni.setStorageSync('pbl:t44-demo', persisted)
    expect(await repository().teacherInsightsRecords()).toEqual([])
    login('teacher', 'other-teacher')
    expect(await repo.teacherInsightsRecords()).toEqual([])
    login('student', 'demo_student')
    await expect(repo.teacherInsightsRecords()).rejects.toMatchObject({ code: 'ROLE_REQUIRED' })
  })
  it.each([
    ['demo-t44-autonomous', 'autonomous'],
    ['demo-pbl-1', 'classroom'],
  ])('completes the visible synthesis seed %s exactly once', async (id, kind) => {
    const repo = repository()
    const seed = await repo.dialogue(id)
    expect(seed.participation).toMatchObject({
      currentPhase: 'synthesis',
      evidenceLocked: false,
      diagnostic: { schemaVersion: 8 },
    })
    expect(seed.participation?.messages.filter((message) => message.role === 'student')).toHaveLength(3)
    const content = '血管通透性增加导致富含蛋白的渗出，结合组织形态与局部肿胀核对机制，还需确认其他原因。'
    const result = await repo.message(id, content, 'original-completion', 'guided')
    expect(result).toMatchObject({
      currentPhase: 'completed',
      evidenceLocked: true,
      learningRouteId: routeId,
      finalTestId: testId,
      diagnostic: { schemaVersion: 8, recommendedQuestions: [] },
    })
    expect(completion).toHaveBeenCalledWith(
      expect.objectContaining({ sessionId: id, sourceKind: kind, studentOpenid: 'demo_student' }),
    )
    const reopened = repository()
    expect((await reopened.dialogue(id)).participation).toEqual(resultWithoutResponse(result))
    expect(await reopened.message(id, content, 'original-completion', 'guided')).toEqual(result)
    expect(completion).toHaveBeenCalledTimes(1)
    login('teacher', 'demo_teacher')
    expect((await reopened.workItems()).items).toHaveLength(kind === 'classroom' ? 1 : 0)
  })
  it('keeps autonomous history inaccessible to another student and classroom teacher reads', async () => {
    const repo = repository()
    login('student', 'demo_student_b')
    expect((await repo.dialogues()).items.some((item) => item.id === 'demo-t44-autonomous')).toBe(false)
    expect((await repo.active()).some((item) => item.id === 'demo-t44-autonomous')).toBe(false)
    await expect(repo.message('demo-t44-autonomous', '另一个学生的输入', 'foreign', 'guided')).rejects.toMatchObject({
      code: 'RESOURCE_NOT_FOUND',
    })
    login('teacher', 'other-teacher')
    await expect(repo.dashboard('1', 'demo-pbl-1')).rejects.toMatchObject({ code: 'RESOURCE_NOT_FOUND' })
  })
  it('preserves frozen classroom diagnosis during private follow-up and replays after reopening', async () => {
    const repo = repository()
    const done = await repo.message('demo-pbl-1', '整合病理机制和证据', 'finish', 'guided')
    const later = await repo.message('demo-pbl-1', '怎样进一步区分渗出和漏出？', 'private-original', 'direct')
    expect(later).toMatchObject({
      responseKind: 'private_follow_up',
      diagnostic: done.diagnostic,
      evidenceCompletedRevision: done.evidenceCompletedRevision,
    })
    expect(completion).toHaveBeenCalledTimes(1)
    expect(
      await repository().message('demo-pbl-1', '怎样进一步区分渗出和漏出？', 'private-original', 'direct'),
    ).toEqual(later)
    login('teacher', 'demo_teacher')
    const queue = await repository().workItems()
    expect(queue.items).toHaveLength(1)
    expect(queue.items[0].snapshotId).toBe(done.diagnostic?.id)
  })
  it('rejects changed replay payloads and retains new discussion progress across reopening', async () => {
    const repo = repository()
    const created = await repo.createDialogue({
      clientSessionId: 'new-own',
      interactionStyle: 'direct',
      goalPointCodes: ['pathology.inflammation.vascular'],
    })
    const first = await repo.message(created.session.id, '先观察局部病理改变', 'phase-original', 'direct')
    expect(first.currentPhase).toBe('hypothesis')
    const reopened = repository()
    expect((await reopened.dialogue(created.session.id)).participation?.currentPhase).toBe('hypothesis')
    await expect(
      reopened.message(created.session.id, '修改了原始输入', 'phase-original', 'direct'),
    ).rejects.toMatchObject({ code: 'STATE_CONFLICT' })
  })
  it('resets only malformed PBL storage and preserves independent resources', async () => {
    const repo = repository()
    await repo.message('demo-pbl-1', '整合证据', 'complete', 'guided')
    const stored = uni.getStorageSync('pbl:t44-demo')
    stored.responses[0][1].result.diagnostic.schemaVersion = 5
    uni.setStorageSync('pbl:t44-demo', stored)
    uni.setStorageSync('caseAttempts:preserve', { id: 'independent-case' })
    expect((await repository().dialogue('demo-pbl-1')).participation?.currentPhase).toBe('synthesis')
    expect(uni.getStorageSync('caseAttempts:preserve')).toEqual({ id: 'independent-case' })
  })
  it('preserves retired student reads and refuses old double-round execution', async () => {
    const repo = repository()
    expect(await repo.plans()).toEqual([])
    expect((await repo.reports()).items).toEqual([])
    await expect(repo.submitTask(1, 'old-task', { selected_option: 0 })).rejects.toMatchObject({
      code: 'STATE_CONFLICT',
      statusCode: 409,
    })
  })
})
function resultWithoutResponse(value: Awaited<ReturnType<DemoPblRepository['message']>>) {
  const { responseKind: _kind, turnScope: _scope, privateFollowUp: _followup, ...participation } = value
  return participation
}
