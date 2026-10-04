import { readTeacherTestFixtures } from '@/test/demoTeacherTestFixtures'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const versionKey = 'learningRoutes:t44-demo:seed-version'
const routeKey = 'learningRoutes:t44-demo'
const uuid = (suffix: string) => `10000000-0000-4000-8000-${suffix.padStart(12, '0')}`

async function loadDemo(openid = 'demo_student', role: 'student' | 'teacher' = 'student') {
  vi.resetModules()
  const [routeModule, identity] = await Promise.all([
    import('./demoLearningRoutes'),
    import('@/features/identity/public'),
  ])
  identity.saveSession({
    openid,
    role,
    nickName: '演示学生',
    avatarUrl: '',
    createdAt: new Date(0).toISOString(),
  })
  return routeModule
}

describe('T44 Demo learning routes adapter', () => {
  beforeEach(() => vi.clearAllMocks())

  it('completes a mixed five-question route and shares one tutor thread across questions', async () => {
    const demo = await loadDemo()
    const created = await demo.ensureDemoLearningRouteForCompletion({
      goalPointCodes: ['pathology.inflammation.acute'],
      sessionId: 'demo-t48-mixed-session',
      studentOpenid: 'demo_student',
      sourceKind: 'autonomous',
    })
    let route = await demo.demoLearningRoutes.getLearningRoute(created.learningRouteId)
    await demo.demoLearningRoutes.completeRouteReading(route.steps[0].id, 't48-reading')
    const caseId = route.steps.find((step) => step.kind === 'case')!.caseId!
    const caseAnswers = [
      '局部红肿伴血管扩张和中性粒细胞聚集，是急性炎症的形态变化。',
      '小动脉扩张增加血流，通透性升高引起蛋白液渗出和组织水肿。',
      '组织水肿和中性粒细胞是支持急性炎症判断的证据，需要核对来源。',
      '总结血管扩张、渗出与炎症细胞证据，仍有不确定之处，后续改进需核对资料。',
    ]
    for (const [index, answer] of caseAnswers.entries()) {
      const current = await demo.demoLearningRoutes.getRouteCase(caseId)
      await demo.demoLearningRoutes.sendRouteCaseMessage(caseId, answer, `t48-case-${index}`, current.revision)
    }
    route = await demo.demoLearningRoutes.getLearningRoute(created.learningRouteId)
    expect(route.canStartTest).toBe(true)
    const test = await demo.demoLearningRoutes.startFinalTest(created.finalTestId, 't48-start')
    expect(test.formatVersion).toBe('mixed_v2')
    expect(test.questions.map((question) => question.questionType)).toEqual([
      'single_choice',
      'single_choice',
      'single_choice',
      'multiple_choice',
      'short_answer',
    ])
    const answers = Object.fromEntries(
      test.questions.map((question) => [
        question.id,
        question.questionType === 'multiple_choice'
          ? [0, 2]
          : question.questionType === 'short_answer'
            ? '小动脉扩张、通透性增加引起渗出和水肿，中性粒细胞支持急性炎症。'
            : 0,
      ]),
    )
    const submitted = await demo.demoLearningRoutes.submitFinalTest(
      test.id,
      't48-submit',
      test.attempt!.version,
      test.releasedDigest,
      answers,
    )
    if (!('id' in submitted)) throw new Error('Demo should finish deterministic grading')
    expect(submitted.questions.map((question) => question.pointsPossible)).toEqual([15, 15, 15, 25, 30])
    expect(submitted.score).toBe(100)
    const first = await demo.demoLearningRoutes.sendLearningResultTutorMessage(
      submitted.id,
      't48-tutor-1',
      test.questions[0].id,
      0,
      '为什么第一题选A？',
    )
    expect(first.revision).toBe(2)
    const second = await demo.demoLearningRoutes.sendLearningResultTutorMessage(
      submitted.id,
      't48-tutor-2',
      test.questions[4].id,
      2,
      '与第一题的依据有什么联系？',
    )
    expect(second.revision).toBe(4)
    expect(second.messages.map((message) => message.questionId)).toEqual([
      test.questions[0].id,
      test.questions[0].id,
      test.questions[4].id,
      test.questions[4].id,
    ])
    const reopened = await loadDemo()
    expect(await reopened.demoLearningRoutes.getLearningResultTutor(submitted.id)).toEqual(second)
  }, 15_000)

  it('supports D01–D10 route scenarios, persists completion idempotently, and preserves real zero scores', async () => {
    const demo = await loadDemo()
    const common = { goalPointCodes: ['pathology.inflammation.vascular'] }
    const d01 = await demo.ensureDemoLearningRouteForCompletion({
      ...common,
      sessionId: 'demo-d01-session',
      studentOpenid: 'demo_student',
      sourceKind: 'autonomous',
    })
    expect(
      await demo.ensureDemoLearningRouteForCompletion({
        ...common,
        sessionId: 'demo-d01-session',
        studentOpenid: 'demo_student',
        sourceKind: 'autonomous',
      }),
    ).toEqual(d01)
    const d02 = await demo.ensureDemoLearningRouteForCompletion({
      ...common,
      sessionId: 'demo-pbl-1',
      studentOpenid: 'demo_student',
      sourceKind: 'classroom',
    })
    expect(d02.learningRouteId).not.toBe(d01.learningRouteId)
    const d02Detail = await demo.demoLearningRoutes.getLearningRoute(d02.learningRouteId)
    expect(d02Detail.summary.goalPointCodes).toEqual(common.goalPointCodes)
    await demo.demoLearningRoutes.completeRouteReading(d02Detail.steps[0].id, 'd02-reading-complete')
    const openedD02Detail = await demo.demoLearningRoutes.getLearningRoute(d02.learningRouteId)
    expect(openedD02Detail.summary.progress).toEqual({ completedSteps: 1, totalSteps: 2 })
    const persisted = uni.getStorageSync(routeKey) as Array<{
      summary: { id: string; progress: { completedSteps: number } }
      detail: { summary: { progress: { completedSteps: number } } }
    }>
    const savedD02 = persisted.find((route) => route.summary.id === d02.learningRouteId)!
    savedD02.summary.progress.completedSteps = 0
    savedD02.detail.summary.progress.completedSteps = 0
    uni.setStorageSync(routeKey, persisted)
    const reloadedStudent = await loadDemo()
    expect(
      (await reloadedStudent.demoLearningRoutes.getLearningRoute(d02.learningRouteId)).summary.progress.completedSteps,
    ).toBe(1)
    expect(
      (await reloadedStudent.demoLearningRoutes.getLearningRoutes('active', 20, 0)).items.find(
        (route) => route.id === d02.learningRouteId,
      )?.progress.completedSteps,
    ).toBe(1)
    const d02CaseStep = openedD02Detail.steps.find((step) => step.kind === 'case')!
    expect((await demo.demoLearningRoutes.getRouteCase(d02CaseStep.caseId!)).syntheticCase.targetPointCodes).toEqual(
      common.goalPointCodes,
    )
    const teacher = await loadDemo('demo_teacher', 'teacher')
    const d02TeacherTest = await readTeacherTestFixtures(teacher, 1, 'demo-pbl-1')
    expect(d02TeacherTest.items.find((test) => test.id === d02.finalTestId)).toMatchObject({
      sessionId: 1,
      goalPointCodes: common.goalPointCodes,
      questions: expect.arrayContaining([
        expect.objectContaining({ primaryPointCode: 'pathology.inflammation.vascular' }),
      ]),
    })

    const student = await loadDemo()
    const knownRouteIds = [3, 4, 5, 7, 8, 10].map((value) => uuid(String(value)))
    const allRoutes = [
      ...(await student.demoLearningRoutes.getLearningRoutes('active', 20, 0)).items,
      ...(await student.demoLearningRoutes.getLearningRoutes('completed', 20, 0)).items,
    ]
    expect(allRoutes.map((route) => route.id)).toEqual(
      expect.arrayContaining([
        d01.learningRouteId,
        d02.learningRouteId,
        ...knownRouteIds.filter((id) => id !== uuid('9')),
      ]),
    )

    const d03 = await student.demoLearningRoutes.getLearningRoute(uuid('3'))
    expect(d03.steps.map((step) => step.kind)).toEqual(['reading', 'case'])
    const d04 = await student.demoLearningRoutes.getLearningRoute(uuid('4'))
    const d04Case = d04.steps.find((step) => step.kind === 'case')!
    const before = await student.demoLearningRoutes.getRouteCase(d04Case.caseId!)
    const originalMessageId = 'd04-original-message'
    const first = await student.demoLearningRoutes.sendRouteCaseMessage(
      before.id,
      '红肿。',
      originalMessageId,
      before.revision,
    )
    const replay = await student.demoLearningRoutes.sendRouteCaseMessage(
      before.id,
      '红肿。',
      originalMessageId,
      before.revision,
    )
    expect(replay).toEqual(first)
    expect(
      (await student.demoLearningRoutes.getRouteCase(before.id)).messages.filter(
        (message) => message.role === 'student',
      ),
    ).toHaveLength(1)

    const d05 = await student.demoLearningRoutes.getLearningRoute(uuid('5'))
    await expect(student.demoLearningRoutes.startFinalTest(d05.testSummary.id, 'd05-start')).rejects.toMatchObject({
      code: 'STATE_CONFLICT',
    })
    const studentBDemo = await loadDemo('demo_student_b')
    const d06 = await studentBDemo.demoLearningRoutes.getLearningRoute(uuid('6'))
    await expect(studentBDemo.demoLearningRoutes.startFinalTest(d06.testSummary.id, 'd06-start')).rejects.toMatchObject(
      { code: 'STATE_CONFLICT' },
    )

    const studentDemo = await loadDemo('demo_student')
    const d07 = await studentDemo.demoLearningRoutes.getLearningRoute(uuid('7'))
    expect(d07.testSummary.questionCount).toBe(5)
    const started = await studentDemo.demoLearningRoutes.startFinalTest(d07.testSummary.id, 'd07-start')
    expect(started.questions.map((question) => question.questionType)).toEqual([
      'single_choice',
      'single_choice',
      'single_choice',
      'multiple_choice',
      'short_answer',
    ])
    const draftAnswers = { [started.questions[0].id]: 2 }
    const draft = await studentDemo.demoLearningRoutes.saveFinalTestDraft(
      started.id,
      'd07-draft',
      started.attempt!.version,
      started.releasedDigest,
      draftAnswers,
    )
    const reopened = await studentDemo.demoLearningRoutes.getFinalTest(d07.summary.id)
    expect(reopened.attempt).toEqual(draft)
    expect(reopened.attempt?.answers).toEqual(draftAnswers)

    const d08 = await studentDemo.demoLearningRoutes.getLearningRoute(uuid('8'))
    await expect(studentDemo.demoLearningRoutes.getLearningRouteResult(d08.summary.id)).resolves.toMatchObject({
      score: 75,
      correctCount: 3,
      questionCount: 5,
    })

    const studentB = await loadDemo('demo_student_b')
    const d09 = await studentB.demoLearningRoutes.getLearningRoute(uuid('9'))
    await expect(studentB.demoLearningRoutes.getLearningRouteResult(d09.summary.id)).resolves.toMatchObject({
      score: 0,
      correctCount: 0,
      questionCount: 5,
    })

    const d10Demo = await loadDemo('demo_student')
    const d10 = await d10Demo.demoLearningRoutes.getLearningRoute(uuid('10'))
    await expect(
      d10Demo.demoLearningRoutes.retryLearningRouteGeneration(d10.summary.id, 'route', 'd10-route-retry'),
    ).resolves.toMatchObject({ routeId: d10.summary.id, component: 'route', generationState: 'published' })
    await expect(
      d10Demo.demoLearningRoutes.retryLearningRouteGeneration(d10.summary.id, 'test', 'd10-test-retry'),
    ).resolves.toMatchObject({ routeId: d10.summary.id, component: 'test', generationState: 'ready' })
  }, 20_000)

  it('validates nested replay receipts and resets only the versioned T44 namespace when one is malformed', async () => {
    const demo = await loadDemo()
    await demo.demoLearningRoutes.getLearningRoutes('active', 20, 0)
    const routes = uni.getStorageSync(routeKey) as Array<Record<string, unknown>>
    const firstRoute = routes[0]
    firstRoute.receipts = { malformed: { fingerprint: '{}', value: { unexpected: ['not', 'a', 'receipt'] } } }
    uni.setStorageSync(routeKey, routes)
    uni.setStorageSync(versionKey, 5)
    uni.setStorageSync('caseAttempts:preserve-me', { attemptId: 'case-17' })

    const reloadedDemo = await loadDemo()
    const reloaded = await reloadedDemo.demoLearningRoutes.getLearningRoutes('active', 20, 0)
    expect(reloaded.items.map((route) => route.id)).toContain(uuid('3'))
    expect(uni.getStorageSync(versionKey)).toBe(5)
    expect((uni.getStorageSync(routeKey) as Array<{ receipts: Record<string, unknown> }>)[0].receipts).toEqual({})
    expect(uni.getStorageSync('caseAttempts:preserve-me')).toEqual({ attemptId: 'case-17' })
  })

  it('upgrades an older T44 marker without clearing independent case, question-bank, or identity data', async () => {
    const demo = await loadDemo()
    await demo.demoLearningRoutes.getLearningRoutes('active', 20, 0)
    const oldRoutes = uni.getStorageSync(routeKey) as Array<{ summary: { id: string; title: string } }>
    oldRoutes[0].summary.title = '过期版本数据'
    uni.setStorageSync(routeKey, oldRoutes)
    uni.setStorageSync(versionKey, 2)
    uni.setStorageSync('caseAttempts:preserve-upgrade', { attemptId: 'case-18' })
    uni.setStorageSync('questionBank:preserve-upgrade', { itemId: 'bank-9' })

    const upgradedDemo = await loadDemo()
    const upgraded = await upgradedDemo.demoLearningRoutes.getLearningRoutes('active', 20, 0)
    expect(upgraded.items.find((route) => route.id === uuid('3'))?.title).not.toBe('过期版本数据')
    expect(uni.getStorageSync(versionKey)).toBe(5)
    expect(uni.getStorageSync('caseAttempts:preserve-upgrade')).toEqual({ attemptId: 'case-18' })
    expect(uni.getStorageSync('questionBank:preserve-upgrade')).toEqual({ itemId: 'bank-9' })
    expect((await import('@/features/identity/public')).getSession()?.openid).toBe('demo_student')
  })

  it('resets version 3 preset test records while keeping case progress and synthetic tutor history', async () => {
    const demo = await loadDemo()
    await demo.demoLearningRoutes.getLearningRoutes('active', 20, 0)
    const completed = await demo.demoLearningRoutes.getLearningRouteResult(uuid('8'))
    await demo.demoLearningRoutes.sendLearningResultTutorMessage(
      completed.id,
      'preset-tutor-before-upgrade',
      completed.questions[0].id,
      0,
      '为什么选这个答案？',
    )
    const routes = uni.getStorageSync(routeKey) as Array<{
      summary: { id: string; testSummary: { questionCount: number } }
      detail: { testSummary: { questionCount: number } }
      cases: Record<string, { revision: number }>
      test: {
        formatVersion: string
        questions: Array<{ id: string }>
        attempt: null | { id: string; status: string; version: number; answers: Record<string, number> }
      }
      teacherTest?: { formatVersion: string; questions: Array<{ id: string }> }
      gradingQuestions: Array<{ id: string }>
      result?: {
        id: string
        formatVersion: string
        questions: Array<{ id: string }>
        questionCount: number
        correctCount: number
        score: number
      }
      submissions: Record<string, { fingerprint: string; resultId: string }>
    }>
    const downgrade = (route: (typeof routes)[number]) => {
      route.test.formatVersion = 'single_choice_v1'
      route.test.questions = route.test.questions.slice(0, 3)
      route.summary.testSummary.questionCount = 3
      route.detail.testSummary.questionCount = 3
      route.gradingQuestions = route.gradingQuestions.slice(0, 3)
      if (route.teacherTest) {
        route.teacherTest.formatVersion = 'single_choice_v1'
        route.teacherTest.questions = route.teacherTest.questions.slice(0, 3)
      }
      if (route.result) {
        route.result.formatVersion = 'single_choice_v1'
        route.result.questions = route.result.questions.slice(0, 3)
        route.result.questionCount = 3
        route.result.correctCount = 2
        route.result.score = 66.7
      }
    }
    const route4 = routes.find((route) => route.summary.id === uuid('4'))!
    const route7 = routes.find((route) => route.summary.id === uuid('7'))!
    const route8 = routes.find((route) => route.summary.id === uuid('8'))!
    const route9 = routes.find((route) => route.summary.id === uuid('9'))!
    for (const route of [route4, route7, route8, route9]) downgrade(route)
    const caseId = Object.keys(route4.cases)[0]
    route4.cases[caseId].revision = 4
    const firstAnswerId = route7.test.questions[0].id
    route7.test.attempt = { id: uuid('700'), status: 'in_progress', version: 2, answers: { [firstAnswerId]: 1 } }
    route9.result!.id = uuid('999')
    route9.test.attempt = {
      id: uuid('900'),
      status: 'submitted',
      version: 2,
      answers: { [route9.test.questions[0].id]: 1 },
    }
    route9.submissions = { 'old-submit': { fingerprint: '{}', resultId: uuid('999') } }
    uni.setStorageSync(routeKey, routes)
    uni.setStorageSync(versionKey, 3)

    const upgraded = await loadDemo()
    const activeRoute = await upgraded.demoLearningRoutes.getLearningRoute(uuid('4'))
    expect(activeRoute.testSummary.questionCount).toBe(5)
    expect((await upgraded.demoLearningRoutes.getRouteCase(caseId)).revision).toBe(4)
    const draft = await upgraded.demoLearningRoutes.getFinalTest(uuid('7'))
    expect(draft.questions).toHaveLength(5)
    expect(draft.attempt).toBeNull()
    const upgradedResult = await upgraded.demoLearningRoutes.getLearningRouteResult(uuid('8'))
    expect(upgradedResult).toMatchObject({ id: completed.id, formatVersion: 'mixed_v2', questionCount: 5, score: 75 })
    expect((await upgraded.demoLearningRoutes.getLearningResultTutor(completed.id)).messages).toHaveLength(2)
    const studentB = await loadDemo('demo_student_b')
    await expect(studentB.demoLearningRoutes.getLearningRouteResult(uuid('9'))).rejects.toMatchObject({
      code: 'RESOURCE_NOT_FOUND',
    })
    const resetTest = await studentB.demoLearningRoutes.getFinalTest(uuid('9'))
    expect(resetTest).toMatchObject({ formatVersion: 'mixed_v2', attempt: null })
    expect(resetTest.questions).toHaveLength(5)
    expect(uni.getStorageSync(versionKey)).toBe(5)
  })

  it('resets a submitted version 4 preset test without clearing its completed learning steps', async () => {
    const demo = await loadDemo()
    const route = await demo.demoLearningRoutes.getLearningRoute(uuid('7'))
    const started = await demo.demoLearningRoutes.startFinalTest(route.testSummary.id, 'preset-old-start')
    const answers = Object.fromEntries(
      started.questions.map((question) => [
        question.id,
        question.questionType === 'multiple_choice'
          ? [0, 2]
          : question.questionType === 'short_answer'
            ? '小动脉扩张和通透性升高引起渗出，出现水肿与中性粒细胞。'
            : 0,
      ]),
    )
    const submitted = await demo.demoLearningRoutes.submitFinalTest(
      started.id,
      'preset-old-submit',
      started.attempt!.version,
      started.releasedDigest,
      answers,
    )
    if (!('id' in submitted)) throw new Error('Demo submission should finish')
    await demo.demoLearningRoutes.sendLearningResultTutorMessage(
      submitted.id,
      'preset-old-tutor',
      started.questions[0].id,
      0,
      '如何理解第一题？',
    )
    const routes = uni.getStorageSync(routeKey) as Array<{
      summary: { id: string; testSummary: { questionCount: number } }
      detail: { testSummary: { questionCount: number } }
      test: { formatVersion: string; questions: Array<{ id: string }> }
      result?: { formatVersion: string; questions: Array<{ id: string }>; questionCount: number }
      tutor?: unknown
      submissions: Record<string, unknown>
    }>
    const old = routes.find((item) => item.summary.id === uuid('7'))!
    old.test.formatVersion = 'single_choice_v1'
    old.test.questions = old.test.questions.slice(0, 3)
    old.result!.formatVersion = 'single_choice_v1'
    old.result!.questions = old.result!.questions.slice(0, 3)
    old.result!.questionCount = 3
    old.summary.testSummary.questionCount = 3
    old.detail.testSummary.questionCount = 3
    uni.setStorageSync(routeKey, routes)
    uni.setStorageSync(versionKey, 4)

    const reopened = await loadDemo()
    const resetRoute = await reopened.demoLearningRoutes.getLearningRoute(uuid('7'))
    expect(resetRoute.steps.every((step) => step.status === 'completed')).toBe(true)
    expect(resetRoute.testSummary).toMatchObject({ questionCount: 5, canStart: true })
    await expect(reopened.demoLearningRoutes.getLearningRouteResult(uuid('7'))).rejects.toMatchObject({
      code: 'RESOURCE_NOT_FOUND',
    })
    await expect(reopened.demoLearningRoutes.getLearningResultTutor(submitted.id)).rejects.toMatchObject({
      code: 'RESOURCE_NOT_FOUND',
    })
    const resetTest = await reopened.demoLearningRoutes.getFinalTest(uuid('7'))
    expect(resetTest).toMatchObject({ formatVersion: 'mixed_v2', attempt: null })
    expect(resetTest.questions).toHaveLength(5)
    const saved = (uni.getStorageSync(routeKey) as typeof routes).find((item) => item.summary.id === uuid('7'))!
    expect(saved.tutor).toBeUndefined()
    expect(saved.submissions).toEqual({})
    expect(uni.getStorageSync(versionKey)).toBe(5)
  })

  it('accepts exactly one learning goal for a newly created Demo route', async () => {
    const demo = await loadDemo()
    await expect(
      demo.ensureDemoLearningRouteForCompletion({
        goalPointCodes: ['pathology.inflammation.acute', 'pathology.inflammation.vascular'],
        sessionId: 'demo-two-goals',
        studentOpenid: 'demo_student',
        sourceKind: 'autonomous',
      }),
    ).rejects.toMatchObject({ code: 'VALIDATION_ERROR' })
  })

  it('enforces role and route ownership and requires active classroom scope before retry', async () => {
    const demo = await loadDemo('demo_student_b')
    await expect(demo.demoLearningRoutes.getLearningRoute(uuid('3'))).rejects.toMatchObject({
      code: 'RESOURCE_NOT_FOUND',
    })
    await expect(readTeacherTestFixtures(demo, 1)).rejects.toMatchObject({ code: 'RESOURCE_NOT_FOUND' })

    const classroom = await demo.demoLearningRoutes.getLearningRoute(uuid('6'))
    const inactiveDemo = await loadDemo('demo_student_b')
    expect((await inactiveDemo.demoLearningRoutes.getLearningRoute(classroom.summary.id)).summary.scopeStatus).toBe(
      'inactive',
    )
    await expect(
      inactiveDemo.demoLearningRoutes.retryLearningRouteGeneration(
        classroom.summary.id,
        'route',
        'inactive-route-retry',
      ),
    ).rejects.toMatchObject({ code: 'STATE_CONFLICT', message: expect.stringContaining('CLASSROOM_SCOPE_INACTIVE') })
    await expect(
      inactiveDemo.demoLearningRoutes.retryLearningRouteGeneration(classroom.summary.id, 'test', 'inactive-test-retry'),
    ).rejects.toMatchObject({ code: 'STATE_CONFLICT', message: expect.stringContaining('CLASSROOM_SCOPE_INACTIVE') })
  })

  it('keeps questions and source digests unchanged when feedback requests changes, including receipt replay', async () => {
    const teacher = await loadDemo('demo_teacher', 'teacher')
    const queue = await teacher.demoLearningRoutes.getTeacherFinalTestReviewQueue({ kind: 'pending_review', limit: 1 })
    const original = await teacher.demoLearningRoutes.getTeacherFinalTest(queue.items[0].id)
    const updated = await teacher.demoLearningRoutes.requestTeacherTestChanges(
      original.id,
      't53-feedback-changes',
      original.version,
      '补充形态依据',
    )
    expect(updated).toMatchObject({
      reviewState: 'needs_changes',
      feedbackDraft: '补充形态依据',
      version: original.version + 1,
      draftDigest: original.draftDigest,
    })
    expect(updated.questions).toEqual(original.questions)
    const replay = await teacher.demoLearningRoutes.requestTeacherTestChanges(
      original.id,
      't53-feedback-changes',
      original.version,
      '补充形态依据',
    )
    expect(replay).toEqual(updated)
  })

  it('projects current active scope on TeacherTest reads and write responses', async () => {
    const teacher = await loadDemo('demo_teacher', 'teacher')
    const activeId = `f0000000-0000-4000-8000-000000000005`
    const inactiveId = `f0000000-0000-4000-8000-000000000006`
    const active = await teacher.demoLearningRoutes.getTeacherFinalTest(activeId)
    expect(active.currentScopeActive).toBe(true)

    const page = await readTeacherTestFixtures(teacher, 1)
    expect(page.items.find((test) => test.id === activeId)?.currentScopeActive).toBe(true)
    expect(page.items.find((test) => test.id === inactiveId)?.currentScopeActive).toBe(false)

    const questions = active.questions.map((question, index) =>
      index === 0 ? { ...question, explanation: '补充活动范围内的教学依据。' } : question,
    )
    const saved = await teacher.demoLearningRoutes.saveTeacherFinalTest(
      activeId,
      'scope-active-save',
      active.version,
      questions,
      '',
    )
    expect(saved.currentScopeActive).toBe(true)
    const changed = await teacher.demoLearningRoutes.requestTeacherTestChanges(
      activeId,
      'scope-active-changes',
      saved.version,
      '继续补充依据',
    )
    expect(changed.currentScopeActive).toBe(true)

    const inactive = await teacher.demoLearningRoutes.getTeacherFinalTest(inactiveId)
    expect(inactive.currentScopeActive).toBe(false)
    await expect(
      teacher.demoLearningRoutes.saveTeacherFinalTest(
        inactiveId,
        'scope-inactive-save',
        inactive.version,
        inactive.questions,
        '',
      ),
    ).rejects.toMatchObject({ code: 'STATE_CONFLICT', message: 'CLASSROOM_SCOPE_INACTIVE' })
    await expect(
      teacher.demoLearningRoutes.requestTeacherTestChanges(
        inactiveId,
        'scope-inactive-changes',
        inactive.version,
        '重审',
      ),
    ).rejects.toMatchObject({ code: 'STATE_CONFLICT', message: 'CLASSROOM_SCOPE_INACTIVE' })
  })

  it('keeps inactive classroom tests readable while rejecting teacher mutations after scope loss', async () => {
    const teacher = await loadDemo('demo_teacher', 'teacher')
    const testId = `f0000000-0000-4000-8000-000000000006`
    const original = await teacher.demoLearningRoutes.getTeacherFinalTest(testId)
    expect(original.questions).toHaveLength(5)
    await expect(
      teacher.demoLearningRoutes.saveTeacherFinalTest(
        testId,
        'inactive-save',
        original.version,
        original.questions,
        '',
      ),
    ).rejects.toMatchObject({ code: 'STATE_CONFLICT', message: 'CLASSROOM_SCOPE_INACTIVE' })
    await expect(
      teacher.demoLearningRoutes.requestTeacherTestChanges(testId, 'inactive-changes', original.version, '重审'),
    ).rejects.toMatchObject({ code: 'STATE_CONFLICT', message: 'CLASSROOM_SCOPE_INACTIVE' })
    await expect(teacher.demoLearningRoutes.retryTeacherTestGeneration(testId, 'inactive-retry')).rejects.toMatchObject(
      {
        code: 'STATE_CONFLICT',
        message: 'CLASSROOM_SCOPE_INACTIVE',
      },
    )
    await expect(
      teacher.demoLearningRoutes.releaseTeacherFinalTest(
        testId,
        'inactive-release',
        original.version,
        original.draftDigest,
        '',
      ),
    ).rejects.toMatchObject({ code: 'STATE_CONFLICT', message: 'CLASSROOM_SCOPE_INACTIVE' })
    expect(await teacher.demoLearningRoutes.getTeacherFinalTest(testId)).toEqual(original)
  })

  it('rejects invalid teacher question edits without changing the draft and releases one valid frozen test', async () => {
    const teacher = await loadDemo('demo_teacher', 'teacher')
    const testId = `f0000000-0000-4000-8000-000000000005`
    const original = await teacher.demoLearningRoutes.getTeacherFinalTest(testId)
    const duplicateOptions = original.questions.map((question, index) =>
      index === 0 && question.questionType !== 'short_answer'
        ? { ...question, options: ['A', ' A ', 'C', 'D'] as [string, string, string, string] }
        : question,
    )
    const foreignQuestion = original.questions.map((question, index) =>
      index === 0 ? { ...question, id: uuid('999') } : question,
    )
    for (const [requestId, questions] of [
      ['duplicate-options', duplicateOptions],
      ['foreign-question', foreignQuestion],
    ] as const) {
      await expect(
        teacher.demoLearningRoutes.saveTeacherFinalTest(testId, requestId, original.version, questions, ''),
      ).rejects.toMatchObject({ code: 'VALIDATION_ERROR' })
      expect(await teacher.demoLearningRoutes.getTeacherFinalTest(testId)).toEqual(original)
    }

    const edited = original.questions.map((question, index) =>
      index === 0 ? { ...question, explanation: '血管扩张与通透性变化对应不同形态证据。' } : question,
    )
    const saved = await teacher.demoLearningRoutes.saveTeacherFinalTest(
      testId,
      'valid-save',
      original.version,
      edited,
      '请核对解释',
    )
    expect(saved.version).toBe(original.version + 1)
    expect(saved.questions[0].explanation).toBe(edited[0].explanation)
    const release = await teacher.demoLearningRoutes.releaseTeacherFinalTest(
      testId,
      'valid-release',
      saved.version,
      saved.draftDigest,
      '已审阅',
    )
    expect(
      await teacher.demoLearningRoutes.releaseTeacherFinalTest(
        testId,
        'valid-release',
        saved.version,
        saved.draftDigest,
        '已审阅',
      ),
    ).toEqual(release)
    expect((await teacher.demoLearningRoutes.getTeacherFinalTest(testId)).reviewState).toBe('released')
    const student = await loadDemo()
    const route = await student.demoLearningRoutes.getLearningRoute(uuid('5'))
    expect(route.testSummary.canStart).toBe(true)
    expect((await student.demoLearningRoutes.startFinalTest(testId, 'released-start')).reviewKind).toBe('teacher')
  })

  it('never reopens a submitted test through an earlier start receipt', async () => {
    const student = await loadDemo()
    const route = await student.demoLearningRoutes.getLearningRoute(uuid('7'))
    const started = await student.demoLearningRoutes.startFinalTest(route.testSummary.id, 'start-before-submit')
    const answers = Object.fromEntries(
      started.questions.map((question) => [
        question.id,
        question.questionType === 'multiple_choice'
          ? [0, 2]
          : question.questionType === 'short_answer'
            ? '小动脉扩张，通透性增加引起渗出和水肿，中性粒细胞聚集。'
            : 0,
      ]),
    )
    const submitted = await student.demoLearningRoutes.submitFinalTest(
      started.id,
      'submit-once',
      started.attempt!.version,
      started.releasedDigest,
      answers,
    )
    expect(
      await student.demoLearningRoutes.submitFinalTest(
        started.id,
        'submit-once',
        started.attempt!.version,
        started.releasedDigest,
        answers,
      ),
    ).toEqual(submitted)
    await expect(student.demoLearningRoutes.startFinalTest(started.id, 'start-before-submit')).rejects.toMatchObject({
      code: 'STATE_CONFLICT',
      message: 'ALREADY_SUBMITTED',
    })
    await expect(student.demoLearningRoutes.startFinalTest(started.id, 'start-after-submit')).rejects.toMatchObject({
      code: 'STATE_CONFLICT',
      message: 'ALREADY_SUBMITTED',
    })
    if (!('id' in submitted)) throw new Error('Legacy demo test should return a completed result')
    expect((await student.demoLearningRoutes.getLearningRoute(uuid('7'))).summary.resultId).toBe(submitted.id)
  })

  it('returns the current case state on replay and closes input after the last phase', async () => {
    const student = await loadDemo()
    const route = await student.demoLearningRoutes.getLearningRoute(uuid('4'))
    const caseId = route.steps.find((step) => step.kind === 'case')!.caseId!
    const first = await student.demoLearningRoutes.getRouteCase(caseId)
    expect(first.stages.map((stage) => stage.phase)).toEqual([
      'pathology_recognition',
      'mechanism_explanation',
      'evidence_judgment',
      'summary_reflection',
    ])
    expect(first.stages[0].goals[0].objective).toContain('局部红、热')
    const mechanism = '小血管扩张增加血流，通透性增加造成组织渗出和水肿，解释病例的红肿。'
    const advanced = await student.demoLearningRoutes.sendRouteCaseMessage(
      caseId,
      mechanism,
      'mechanism-once',
      first.revision,
    )
    expect(advanced.phase).toBe('evidence_judgment')
    const afterAdvance = await student.demoLearningRoutes.getRouteCase(caseId)
    expect(afterAdvance.goals).toEqual(afterAdvance.stages[2].goals)
    expect(afterAdvance.stages[0].goals).toEqual(first.stages[0].goals)
    const evidence = '组织水肿和中性粒细胞聚集是关键证据，支持急性炎症的判断。'
    const reflection = await student.demoLearningRoutes.sendRouteCaseMessage(
      caseId,
      evidence,
      'evidence-once',
      advanced.revision,
    )
    expect(reflection.phase).toBe('summary_reflection')
    expect(reflection.status).toBe('in_progress')
    const insufficient = await student.demoLearningRoutes.sendRouteCaseMessage(
      caseId,
      '总结：我已经掌握了本次病例的病理分析。',
      'reflection-insufficient',
      reflection.revision,
    )
    expect(insufficient.decision).toBe('stay')
    const completed = await student.demoLearningRoutes.sendRouteCaseMessage(
      caseId,
      '总结血管扩张与渗出支持炎症判断，但渗出与漏出仍不确定，准备查阅资料核对并改进推理。',
      'reflection-once',
      insufficient.revision,
    )
    expect(completed.status).toBe('completed')
    const replay = await student.demoLearningRoutes.sendRouteCaseMessage(
      caseId,
      mechanism,
      'mechanism-once',
      first.revision,
    )
    expect(replay).toMatchObject({
      reply: advanced.reply,
      decision: advanced.decision,
      requestRevision: advanced.requestRevision,
      phase: 'completed',
      status: 'completed',
      revision: completed.revision,
    })
    await expect(
      student.demoLearningRoutes.sendRouteCaseMessage(caseId, evidence, 'new-after-completion', completed.revision),
    ).rejects.toMatchObject({ code: 'STATE_CONFLICT', message: 'CASE_COMPLETED' })
    const review = await student.demoLearningRoutes.getRouteCase(caseId)
    expect(review.messages).toHaveLength(first.messages.length + 8)
    expect(review.stages[0].prompt).toBe(first.stages[0].prompt)
    expect(review.stages[3].goals).toHaveLength(2)
  })

  it('rotates reading leases, ignores expired elapsed time, and keeps a started test in testing state', async () => {
    vi.useFakeTimers()
    try {
      vi.setSystemTime(new Date('2026-09-27T08:00:00Z'))
      const student = await loadDemo()
      const readingRoute = await student.demoLearningRoutes.getLearningRoute(uuid('3'))
      const stepId = readingRoute.steps.find((step) => step.kind === 'reading')!.id
      const first = await student.demoLearningRoutes.saveRouteReadingProgress(stepId, 'start', 'lease-first')
      vi.advanceTimersByTime(1000)
      const second = await student.demoLearningRoutes.saveRouteReadingProgress(stepId, 'start', 'lease-second')
      expect(second.leaseToken).not.toBe(first.leaseToken)
      await expect(
        student.demoLearningRoutes.saveRouteReadingProgress(stepId, 'heartbeat', 'old-lease', first.leaseToken),
      ).rejects.toMatchObject({ code: 'STATE_CONFLICT', message: 'READING_LEASE_INVALID' })
      vi.advanceTimersByTime(31_000)
      const expired = await student.demoLearningRoutes.saveRouteReadingProgress(
        stepId,
        'heartbeat',
        'expired-lease',
        second.leaseToken,
      )
      expect(expired.accumulatedSeconds).toBe(0)

      const ready = await student.demoLearningRoutes.getLearningRoute(uuid('7'))
      await student.demoLearningRoutes.startFinalTest(ready.testSummary.id, 'testing-status-start')
      expect((await student.demoLearningRoutes.getLearningRoute(uuid('7'))).summary.status).toBe('testing')
    } finally {
      vi.useRealTimers()
    }
  })

  it('does not retry test generation before the route has been published', async () => {
    const student = await loadDemo()
    const routeId = uuid('10')
    const before = await student.demoLearningRoutes.getLearningRoute(routeId)
    expect(before.summary.generationState).toBe('generation_failed')
    await expect(
      student.demoLearningRoutes.retryLearningRouteGeneration(routeId, 'test', 'test-before-route'),
    ).rejects.toMatchObject({ code: 'STATE_CONFLICT', message: 'ROUTE_NOT_PUBLISHED' })
    expect((await student.demoLearningRoutes.getLearningRoute(routeId)).testSummary.generationState).toBe('failed')
    await student.demoLearningRoutes.retryLearningRouteGeneration(routeId, 'route', 'publish-route')
    expect((await student.demoLearningRoutes.getLearningRoute(routeId)).testSummary.generationState).toBe('failed')
    const published = await student.demoLearningRoutes.getLearningRoute(routeId)
    await student.demoLearningRoutes.completeRouteReading(published.steps[0].id, 'failed-test-reading')
    const caseId = published.steps[1].caseId!
    const answers = [
      '局部发红肿胀且小血管扩张，通透性增加，组织间有液体渗出和中性粒细胞聚集。',
      '小血管扩张增加血流，通透性增加使蛋白液体渗出，形成组织水肿。',
      '组织水肿及中性粒细胞聚集是病理证据，支持急性炎症的判断。',
      '总结血管扩张与渗出支持炎症判断，但渗出与漏出仍不确定，准备查阅资料核对并改进推理。',
    ]
    for (const [index, answer] of answers.entries()) {
      const currentCase = await student.demoLearningRoutes.getRouteCase(caseId)
      await student.demoLearningRoutes.sendRouteCaseMessage(
        caseId,
        answer,
        `failed-test-case-${index}`,
        currentCase.revision,
      )
    }
    const waiting = await student.demoLearningRoutes.getLearningRoute(routeId)
    expect(waiting.summary.status).toBe('waiting_test_generation')
    expect(waiting.testSummary.canStart).toBe(false)
    await expect(
      student.demoLearningRoutes.startFinalTest(waiting.testSummary.id, 'blocked-start'),
    ).rejects.toMatchObject({ code: 'STATE_CONFLICT', message: 'TEST_NOT_GENERATED' })
    await expect(
      student.demoLearningRoutes.retryLearningRouteGeneration(routeId, 'test', 'retry-test-after-route'),
    ).resolves.toMatchObject({ generationState: 'ready' })
    expect((await student.demoLearningRoutes.getLearningRoute(routeId)).summary.status).toBe('ready_for_test')
  })
})
