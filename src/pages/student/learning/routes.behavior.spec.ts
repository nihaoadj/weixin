import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import Reading from './route-reading.vue'
import Case from './route-case.vue'
import FinalTest from './final-test.vue'
import Result from './learning-result.vue'
import Plans from './plans.vue'
import Detail from './plan-detail.vue'

const state = vi.hoisted(() => ({
  identity: 'student-a',
  hooks: {} as Record<string, (options?: Record<string, string>) => void>,
  getLearningRouteStep: vi.fn(),
  saveRouteReadingProgress: vi.fn(),
  completeRouteReading: vi.fn(),
  getRouteCase: vi.fn(),
  sendRouteCaseMessage: vi.fn(),
  startFinalTest: vi.fn(),
  saveFinalTestDraft: vi.fn(),
  submitFinalTest: vi.fn(),
  getFinalTestGrading: vi.fn(),
  retryFinalTestGrading: vi.fn(),
  getLearningRouteResult: vi.fn(),
  getLearningResultTutor: vi.fn(),
  sendLearningResultTutorMessage: vi.fn(),
  getLearningRoutes: vi.fn(),
  getLearningRoute: vi.fn(),
  retryLearningRouteGeneration: vi.fn(),
  goDetail: vi.fn(),
  goReplace: vi.fn(),
  backOrRoute: vi.fn(),
  sequence: 0,
}))
vi.mock('@dcloudio/uni-app', () =>
  Object.fromEntries(
    ['onLoad', 'onShow', 'onHide', 'onUnload', 'onBackPress'].map((name) => [
      name,
      (hook: (options?: Record<string, string>) => void) => {
        state.hooks[name] = hook
      },
    ]),
  ),
)
vi.mock('@/features/identity/public', () => ({
  requireRole: () => Boolean(state.identity),
  getSession: () => ({ role: 'student', openid: state.identity }),
}))
vi.mock('@/features/learning/public', async () => ({
  ROUTE_CASE_STAGES: (await import('@/features/learning/domain/routeCases')).ROUTE_CASE_STAGES,
  getLearningRouteStep: state.getLearningRouteStep,
  saveRouteReadingProgress: state.saveRouteReadingProgress,
  completeRouteReading: state.completeRouteReading,
  getRouteCase: state.getRouteCase,
  sendRouteCaseMessage: state.sendRouteCaseMessage,
  startFinalTest: state.startFinalTest,
  getFinalTest: vi.fn(),
  saveFinalTestDraft: state.saveFinalTestDraft,
  submitFinalTest: state.submitFinalTest,
  getFinalTestGrading: state.getFinalTestGrading,
  retryFinalTestGrading: state.retryFinalTestGrading,
  getLearningRouteResult: state.getLearningRouteResult,
  getLearningResultTutor: state.getLearningResultTutor,
  sendLearningResultTutorMessage: state.sendLearningResultTutorMessage,
  getLearningRoutes: state.getLearningRoutes,
  getLearningRoute: state.getLearningRoute,
  retryLearningRouteGeneration: state.retryLearningRouteGeneration,
  learningGoalLabel: (code: string) => code,
  createLearningRequestId: (prefix: string) => `${prefix}-${++state.sequence}`,
}))
vi.mock('@/platform/navigation', () => ({
  backOrRoute: state.backOrRoute,
  goDetail: state.goDetail,
  goReplace: state.goReplace,
  handleBackPress: vi.fn(),
  ROUTES: {
    studentLearningPlanDetail: '/plan',
    studentLearningResult: '/result',
    studentLearningPlans: '/plans',
    studentPbl: '/pbl',
    studentFinalTest: '/test',
    studentRouteReading: '/reading',
    studentRouteCase: '/case',
  },
}))
const routeId = '11111111-1111-4111-8111-111111111111'
const itemId = '22222222-2222-4222-8222-222222222222'
function reading() {
  return {
    routeId,
    step: { id: itemId, position: 1, kind: 'reading', title: '细胞损伤资料', status: 'pending' },
    sources: [],
    aiGuide: '联系病例理解损伤机制',
    sections: [],
    learningPoints: [],
    readingProgress: { accumulatedSeconds: 0 },
  }
}
function caseRead() {
  return {
    id: itemId,
    routeId,
    syntheticCase: { title: '合成病例', publicScenario: '教学情境', caseFacts: ['组织改变'] },
    phase: 'pathology_recognition',
    revision: 0,
    status: 'in_progress',
    goals: [],
    stages: [
      {
        phase: 'pathology_recognition',
        goals: [{ goalId: 'recognition-1', objective: '识别这例组织改变的形态线索' }],
        prompt: '这例组织改变最关键的形态证据是什么？',
      },
      {
        phase: 'mechanism_explanation',
        goals: [{ goalId: 'mechanism-1', objective: '解释这例组织改变的发生机制' }],
        prompt: '这些形态变化是怎样形成的？',
      },
      {
        phase: 'evidence_judgment',
        goals: [{ goalId: 'evidence-1', objective: '用这例的证据支持病理判断' }],
        prompt: '哪些具体事实支持你的判断？',
      },
      {
        phase: 'summary_reflection',
        goals: [{ goalId: 'reflection-1', objective: '总结推理并提出下一次改进方法' }],
        prompt: '回顾推理中仍不确定的地方。',
      },
    ],
    messages: [],
    nextPrompt: '说明依据',
    safetyNotice: '仅供教学',
  }
}
function finalTest() {
  return {
    id: itemId,
    title: '最终测试',
    releasedDigest: 'frozen-digest',
    questions: [
      { id: 'q1', position: 1, pointCode: 'point', prompt: '选择病理依据', options: ['甲', '乙', '丙', '丁'] },
      { id: 'q2', position: 2, pointCode: 'point', prompt: '选择机制', options: ['甲', '乙', '丙', '丁'] },
    ],
    attempt: {
      id: 'attempt',
      status: 'in_progress',
      version: 3,
      answers: { q1: 0, q2: 1 },
      savedAt: '2026-09-27T00:00:00Z',
    },
  }
}
async function open(
  component: typeof Reading | typeof Case | typeof FinalTest | typeof Result | typeof Plans | typeof Detail,
  key: string,
) {
  const wrapper = mount(component)
  state.hooks.onLoad({ routeId, [key]: itemId })
  state.hooks.onShow()
  await flushPromises()
  return wrapper
}
describe('single round student learning pages', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.useFakeTimers()
    state.identity = 'student-a'
    state.hooks = {}
    state.sequence = 0
    state.getLearningRouteStep.mockResolvedValue(reading())
    state.saveRouteReadingProgress.mockImplementation(async (_id, action) => ({
      accumulatedSeconds: 0,
      leaseToken: action === 'pause' ? undefined : 'lease-a',
    }))
    state.completeRouteReading.mockResolvedValue({})
    state.getRouteCase.mockResolvedValue(caseRead())
    state.startFinalTest.mockResolvedValue(finalTest())
    state.saveFinalTestDraft.mockResolvedValue({ ...finalTest().attempt, version: 4, answers: { q1: 2, q2: 1 } })
    state.submitFinalTest.mockResolvedValue({ id: 'result-id' })
    state.getFinalTestGrading.mockResolvedValue({ status: 'grading', testId: itemId, routeId, retryAllowed: false })
    state.retryFinalTestGrading.mockResolvedValue({ status: 'grading', testId: itemId, routeId, retryAllowed: false })
    state.getLearningResultTutor.mockResolvedValue({
      resultId: itemId,
      revision: 0,
      processingState: 'idle',
      messages: [],
    })
    state.sendLearningResultTutorMessage.mockResolvedValue({
      resultId: itemId,
      revision: 2,
      processingState: 'idle',
      messages: [],
    })
    state.getLearningRoutes.mockResolvedValue({ items: [], total: 0, limit: 20, offset: 0 })
    state.getLearningRoute.mockResolvedValue({
      summary: {
        id: routeId,
        title: '课堂学习路线',
        sourceKind: 'classroom',
        sessionLocator: '课堂研讨',
        nextAction: 'wait_teacher',
        progress: { completedSteps: 2, totalSteps: 2 },
      },
      diagnosisSummary: {},
      steps: [],
      testSummary: { id: itemId, questionCount: 3, reviewState: 'pending_review', canStart: false },
      canStartTest: false,
      lockReasons: ['TEST_NOT_RELEASED'],
    })
    state.getLearningRouteResult.mockResolvedValue({
      id: itemId,
      routeId,
      sourceKind: 'autonomous',
      routeSummary: { title: '完成记录' },
      correctCount: 0,
      questionCount: 2,
      score: 0,
      submittedAt: '2026-09-27T00:00:00Z',
      reviewKind: 'ai_direct',
      questions: [],
    })
    vi.stubGlobal('uni', { showModal: vi.fn(({ success }) => success({ confirm: true })) })
  })
  afterEach(() => {
    vi.clearAllTimers()
    vi.useRealTimers()
    vi.unstubAllGlobals()
  })

  it('pauses the reading lease on hide and stops background heartbeats', async () => {
    const wrapper = await open(Reading, 'stepId')
    expect(state.saveRouteReadingProgress).toHaveBeenCalledWith(itemId, 'start', expect.any(String), undefined)
    state.hooks.onHide()
    await flushPromises()
    expect(state.saveRouteReadingProgress).toHaveBeenLastCalledWith(itemId, 'pause', expect.any(String), 'lease-a')
    await vi.advanceTimersByTimeAsync(60_000)
    expect(state.saveRouteReadingProgress).toHaveBeenCalledTimes(2)
    wrapper.unmount()
  })
  it('allows explicit completion at zero seconds and retries with the original request', async () => {
    state.completeRouteReading.mockRejectedValueOnce(new Error('响应未确认')).mockResolvedValueOnce({})
    const wrapper = await open(Reading, 'stepId')
    await wrapper.get('button.primary').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('响应未确认')
    await wrapper.get('button.primary').trigger('click')
    await flushPromises()
    expect(state.completeRouteReading.mock.calls[1]).toEqual(state.completeRouteReading.mock.calls[0])
    expect(state.backOrRoute).toHaveBeenCalledWith('/plan', { routeId })
    wrapper.unmount()
  })
  it('discards a previous student reading response after identity changes', async () => {
    let resolve!: (value: ReturnType<typeof reading>) => void
    state.getLearningRouteStep
      .mockReturnValueOnce(
        new Promise((done) => {
          resolve = done
        }),
      )
      .mockResolvedValueOnce({ ...reading(), step: { ...reading().step, title: '新学生资料' } })
    const wrapper = await open(Reading, 'stepId')
    state.identity = 'student-b'
    state.hooks.onShow()
    await flushPromises()
    resolve(reading())
    await flushPromises()
    expect(wrapper.text()).toContain('新学生资料')
    expect(wrapper.text()).not.toContain('细胞损伤资料')
    wrapper.unmount()
  })
  it('opens the case-specific stage goals as numbered points and keeps future stages locked', async () => {
    const wrapper = await open(Case, 'caseId')
    expect(wrapper.find('.composer').exists()).toBe(false)
    expect(wrapper.text()).toContain('学习说明')
    await wrapper.get('.start-button').trigger('click')
    expect(wrapper.text()).toContain('第 1 个阶段：病理识别')
    expect(wrapper.get('.goals-list').text()).toContain('1识别这例组织改变的形态线索')
    expect(wrapper.get('.stage-prompt').text()).toBe('这例组织改变最关键的形态证据是什么？')
    expect(wrapper.findAll('.stage-tab')).toHaveLength(4)
    expect(wrapper.findAll('swiper-item')).toHaveLength(1)
    await wrapper.findAll('.stage-tab')[3].trigger('click')
    expect(wrapper.text()).toContain('完成当前阶段目标后')
    expect(wrapper.find('.stage-tab.selected').text()).toContain('病理识别')
    await wrapper.get('.case-summary').trigger('click')
    expect(wrapper.get('.expanded-facts').text()).toContain('组织改变')
    wrapper.unmount()
  })
  it('switches stage chat views without sending or losing the active draft and retains saved openings', async () => {
    state.getRouteCase.mockResolvedValue({
      ...caseRead(),
      phase: 'mechanism_explanation',
      revision: 2,
      messages: [
        { id: 'm1', role: 'student', content: '第一阶段依据', revision: 1, phase: 'pathology_recognition' },
        { id: 'm2', role: 'assistant', content: '第一阶段反馈', revision: 1, phase: 'pathology_recognition' },
        { id: 'm3', role: 'student', content: '第二阶段机制', revision: 2, phase: 'mechanism_explanation' },
      ],
    })
    const wrapper = await open(Case, 'caseId')
    await wrapper.get('.start-button').trigger('click')
    await wrapper.get('textarea').setValue('待提交草稿')
    const chats = wrapper.findAll('.conversation')
    expect(chats[0].text()).toContain('第一阶段依据')
    expect(chats[0].text()).toContain('识别这例组织改变的形态线索')
    expect(chats[0].text()).not.toContain('第二阶段机制')
    expect(chats[1].text()).toContain('第 2 个阶段：机制解释')
    expect(chats[1].text()).toContain('解释这例组织改变的发生机制')
    expect(chats[1].text()).not.toContain('第一阶段反馈')
    await wrapper.findAll('.stage-tab')[0].trigger('click')
    expect(wrapper.get('textarea').attributes('disabled')).toBeDefined()
    await wrapper.get('swiper').trigger('change', { detail: { current: 1 } })
    expect(wrapper.find('.stage-tab.selected').text()).toContain('机制解释')
    expect((wrapper.get('textarea').element as HTMLTextAreaElement).value).toBe('待提交草稿')
    expect(state.sendRouteCaseMessage).not.toHaveBeenCalled()
    wrapper.unmount()
  })
  it('reopens a completed case with all four saved stage openings available for review', async () => {
    state.getRouteCase.mockResolvedValue({ ...caseRead(), phase: 'completed', status: 'completed' })
    const wrapper = await open(Case, 'caseId')
    await wrapper.get('.start-button').trigger('click')
    expect(wrapper.findAll('swiper-item')).toHaveLength(4)
    expect(wrapper.findAll('.conversation')[3].text()).toContain('总结推理并提出下一次改进方法')
    await wrapper.findAll('.stage-tab')[0].trigger('click')
    expect(wrapper.findAll('.conversation')[0].text()).toContain('识别这例组织改变的形态线索')
    expect(wrapper.find('.composer').exists()).toBe(false)
    wrapper.unmount()
  })
  it('keeps feedback in the stage just answered while unlocking the next chat', async () => {
    const wrapper = await open(Case, 'caseId')
    await wrapper.get('.start-button').trigger('click')
    expect(wrapper.get('.chat-scroll').attributes('scroll-into-view')).toBe('')
    state.sendRouteCaseMessage.mockResolvedValue({})
    state.getRouteCase.mockResolvedValue({
      ...caseRead(),
      phase: 'mechanism_explanation',
      revision: 1,
      messages: [
        { id: 'm1', role: 'student', content: '血管扩张与组织水肿', revision: 1, phase: 'pathology_recognition' },
        { id: 'm2', role: 'assistant', content: '识别目标已达成', revision: 1, phase: 'pathology_recognition' },
      ],
    })
    await wrapper.get('textarea').setValue('血管扩张与组织水肿')
    await wrapper.get('.send-button').trigger('click')
    await flushPromises()
    expect(wrapper.get('.stage-tab.selected').text()).toContain('病理识别')
    expect(wrapper.findAll('swiper-item')).toHaveLength(2)
    expect(wrapper.findAll('.conversation')[0].text()).toContain('识别目标已达成')
    await wrapper.get('.stage-completed button').trigger('click')
    expect(wrapper.get('.stage-tab.selected').text()).toContain('机制解释')
    expect(wrapper.findAll('.chat-scroll')[1].attributes('scroll-into-view')).toBe('')
    wrapper.unmount()
  })
  it('preserves a failed draft and releases retry state after polling confirms the original message', async () => {
    const wrapper = await open(Case, 'caseId')
    await wrapper.get('.start-button').trigger('click')
    state.sendRouteCaseMessage.mockRejectedValue(new Error('响应未确认'))
    await wrapper.get('textarea').setValue('保留病例依据')
    await wrapper.get('.send-button').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('响应未确认')
    expect((wrapper.get('textarea').element as HTMLTextAreaElement).value).toBe('保留病例依据')
    state.getRouteCase.mockResolvedValue({
      ...caseRead(),
      revision: 1,
      messages: [
        { id: 'm1', role: 'student', content: '保留病例依据', revision: 1, phase: 'pathology_recognition' },
        { id: 'm2', role: 'assistant', content: '请补充形态证据', revision: 1, phase: 'pathology_recognition' },
      ],
    })
    state.hooks.onShow()
    await flushPromises()
    expect(wrapper.find('.pending').exists()).toBe(false)
    expect(wrapper.get('textarea').attributes('disabled')).toBeUndefined()
    expect(state.sendRouteCaseMessage).toHaveBeenCalledTimes(1)
    wrapper.unmount()
  })
  it('recovers a pending case message using its persisted id, content and revision', async () => {
    state.getRouteCase.mockResolvedValue({
      ...caseRead(),
      messages: [{ id: 'message', role: 'student', content: '原始病例依据', revision: 0 }],
      pendingMessage: {
        clientMessageId: 'original-message',
        requestRevision: 0,
        processingState: 'failed',
        retryAllowed: true,
      },
    })
    state.sendRouteCaseMessage.mockResolvedValue({})
    const wrapper = await open(Case, 'caseId')
    await wrapper.get('.start-button').trigger('click')
    await wrapper.get('.pending button').trigger('click')
    await flushPromises()
    expect(state.sendRouteCaseMessage).toHaveBeenCalledWith(itemId, '原始病例依据', 'original-message', 0)
    wrapper.unmount()
  })
  it('polls pending case status without resending and stops polling on hide', async () => {
    state.getRouteCase.mockResolvedValue({
      ...caseRead(),
      pendingMessage: {
        clientMessageId: 'original-message',
        requestRevision: 0,
        processingState: 'processing',
        retryAllowed: false,
      },
    })
    const wrapper = await open(Case, 'caseId')
    await wrapper.get('.start-button').trigger('click')
    expect(wrapper.get('.pending button').attributes('disabled')).toBeDefined()
    await vi.advanceTimersByTimeAsync(3000)
    await flushPromises()
    expect(state.getRouteCase).toHaveBeenCalledTimes(2)
    expect(state.sendRouteCaseMessage).not.toHaveBeenCalled()
    state.hooks.onHide()
    await vi.advanceTimersByTimeAsync(30_000)
    expect(state.getRouteCase).toHaveBeenCalledTimes(2)
    wrapper.unmount()
  })
  it('restores drafts and saves an edited answer when leaving before debounce', async () => {
    const wrapper = await open(FinalTest, 'testId')
    expect(wrapper.get('.muted').text()).toContain('2 单选')
    expect(wrapper.findAll('.question-heading')).toHaveLength(2)
    expect(wrapper.findAll('.option.selected')).toHaveLength(2)
    await wrapper.findAll('.option')[2].trigger('click')
    expect(wrapper.get('button.primary').attributes('disabled')).toBeDefined()
    state.hooks.onHide()
    await flushPromises()
    expect(state.saveFinalTestDraft).toHaveBeenCalledWith(itemId, expect.any(String), 3, 'frozen-digest', {
      q1: 2,
      q2: 1,
    })
    expect(wrapper.text()).toContain('草稿已同步')
    wrapper.unmount()
  })
  it('keeps answers locked and reuses one whole submission after an uncertain response', async () => {
    state.submitFinalTest.mockRejectedValueOnce(new Error('提交响应未确认')).mockResolvedValueOnce({ id: 'result-id' })
    const wrapper = await open(FinalTest, 'testId')
    await wrapper.get('button.primary').trigger('click')
    expect(state.submitFinalTest).not.toHaveBeenCalled()
    await wrapper.get('#confirm-test-submit').trigger('click')
    await flushPromises()
    await wrapper.findAll('.option')[3].trigger('click')
    await wrapper.get('button.primary').trigger('click')
    await flushPromises()
    expect(state.submitFinalTest.mock.calls[1]).toEqual(state.submitFinalTest.mock.calls[0])
    expect(state.submitFinalTest.mock.calls[0]).toEqual([
      itemId,
      expect.any(String),
      3,
      'frozen-digest',
      { q1: 0, q2: 1 },
    ])
    expect(state.goReplace).toHaveBeenCalledWith('/result', { routeId, resultId: 'result-id' })
    wrapper.unmount()
  })

  it('closes an unconfirmed submission when the student identity changes', async () => {
    const wrapper = await open(FinalTest, 'testId')
    await wrapper.get('button.primary').trigger('click')
    expect(wrapper.find('#confirm-test-submit').exists()).toBe(true)
    state.identity = 'student-b'
    state.hooks.onShow()
    await flushPromises()
    expect(wrapper.find('#confirm-test-submit').exists()).toBe(false)
    expect(state.submitFinalTest).not.toHaveBeenCalled()
    wrapper.unmount()
  })

  it('keeps saved answers editable when submission confirmation is cancelled', async () => {
    const wrapper = await open(FinalTest, 'testId')
    await wrapper.get('button.primary').trigger('click')
    await wrapper.get('.confirm-cancel').trigger('click')
    expect(wrapper.find('#confirm-test-submit').exists()).toBe(false)
    expect(wrapper.findAll('.option.selected')).toHaveLength(2)
    expect(state.submitFinalTest).not.toHaveBeenCalled()
    wrapper.unmount()
  })

  it('shows a completed zero-score result without a retest or pass threshold', async () => {
    const wrapper = await open(Result, 'resultId')
    expect(wrapper.get('.score').text()).toBe('0分')
    expect(wrapper.text()).toContain('导学助手')
    expect(wrapper.text()).not.toMatch(/补考|达标|重考/)
    await wrapper.get('button.back-button').trigger('click')
    expect(state.goReplace).toHaveBeenCalledWith('/plan', { routeId })
    expect(state.backOrRoute).not.toHaveBeenCalled()
    wrapper.unmount()
  })

  it('rejects a result locator that belongs to a different route', async () => {
    state.getLearningRouteResult.mockResolvedValue({ id: itemId, routeId: 'another-route' })
    const wrapper = await open(Result, 'resultId')
    expect(wrapper.text()).toContain('学习结果不属于当前路线')
    expect(wrapper.find('.summary').exists()).toBe(false)
    wrapper.unmount()
  })

  it('saves mixed-choice and short-answer changes in the whole-test draft', async () => {
    state.startFinalTest.mockResolvedValue({
      ...finalTest(),
      formatVersion: 'mixed_v2',
      questions: [
        {
          id: 'q1',
          position: 1,
          pointCode: 'point',
          prompt: '单选一',
          questionType: 'single_choice',
          options: ['甲', '乙', '丙', '丁'],
        },
        {
          id: 'q2',
          position: 2,
          pointCode: 'point',
          prompt: '单选二',
          questionType: 'single_choice',
          options: ['甲', '乙', '丙', '丁'],
        },
        {
          id: 'q3',
          position: 3,
          pointCode: 'point',
          prompt: '单选三',
          questionType: 'single_choice',
          options: ['甲', '乙', '丙', '丁'],
        },
        {
          id: 'q4',
          position: 4,
          pointCode: 'point',
          prompt: '多选',
          questionType: 'multiple_choice',
          options: ['甲', '乙', '丙', '丁'],
        },
        { id: 'q5', position: 5, pointCode: 'point', prompt: '简答', questionType: 'short_answer', options: [] },
      ],
      attempt: { ...finalTest().attempt, answers: { q1: 0, q2: 1, q3: 2 } },
    })
    state.saveFinalTestDraft.mockImplementation(async (_id, _requestId, version, _digest, answers) => ({
      id: 'attempt',
      status: 'in_progress',
      version: version + 1,
      answers,
    }))
    const wrapper = await open(FinalTest, 'testId')
    expect(wrapper.get('.muted').text()).toContain('3 单选 · 1 多选 · 1 简答')
    expect(wrapper.findAll('.question-heading')).toHaveLength(5)
    const fourth = wrapper.findAll('.question')[3]
    await fourth.findAll('.option')[0].trigger('click')
    await fourth.findAll('.option')[2].trigger('click')
    await wrapper.get('.answer-input').setValue('血管扩张与渗出，结合机制解释。')
    await vi.advanceTimersByTimeAsync(600)
    await flushPromises()
    expect(state.saveFinalTestDraft).toHaveBeenCalledWith(itemId, expect.any(String), 3, 'frozen-digest', {
      q1: 0,
      q2: 1,
      q3: 2,
      q4: [0, 2],
      q5: '血管扩张与渗出，结合机制解释。',
    })
    expect(wrapper.get('button.primary').attributes('disabled')).toBeUndefined()
    wrapper.unmount()
  })

  it('waits for mixed grading before navigating to the result', async () => {
    state.submitFinalTest.mockResolvedValue({ status: 'grading', testId: itemId, routeId, retryAllowed: false })
    state.getFinalTestGrading.mockResolvedValue({
      status: 'completed',
      testId: itemId,
      routeId,
      resultId: itemId,
      retryAllowed: false,
    })
    const wrapper = await open(FinalTest, 'testId')
    await wrapper.get('button.primary').trigger('click')
    await wrapper.get('#confirm-test-submit').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('正在综合判分')
    expect(state.goReplace).not.toHaveBeenCalled()
    await vi.advanceTimersByTimeAsync(2500)
    expect(state.goReplace).toHaveBeenCalledWith('/result', { routeId, resultId: itemId })
    wrapper.unmount()
  })

  it('reopens a submitted test at grading status rather than trapping the student on an error', async () => {
    state.startFinalTest.mockRejectedValue(new Error('ALREADY_SUBMITTED'))
    state.getFinalTestGrading.mockResolvedValue({ status: 'grading', testId: itemId, routeId, retryAllowed: true })
    const wrapper = await open(FinalTest, 'testId')
    expect(wrapper.text()).toContain('判分暂未完成')
    expect(wrapper.text()).toContain('重新判分')
    expect(wrapper.text()).not.toContain('ALREADY_SUBMITTED')
    wrapper.unmount()
  })

  it('opens pending grading from the plan detail', async () => {
    const initial = await state.getLearningRoute.getMockImplementation()!()
    state.getLearningRoute.mockResolvedValue({
      ...initial,
      summary: { ...initial.summary, status: 'grading', nextAction: 'wait_grade' },
      testSummary: { ...initial.testSummary, canStart: false, lockReason: 'GRADING_IN_PROGRESS' },
    })
    const wrapper = await open(Detail, 'unused')
    expect(wrapper.text()).toContain('查看判分进度')
    await wrapper.get('button.primary').trigger('click')
    expect(state.goDetail).toHaveBeenCalledWith('/test', { routeId, testId: itemId })
    wrapper.unmount()
  })

  it('keeps one tutor transcript while question changes anchor the next message', async () => {
    state.getLearningRouteResult.mockResolvedValue({
      id: itemId,
      routeId,
      sourceKind: 'autonomous',
      routeSummary: { title: '完成记录' },
      correctCount: 1,
      questionCount: 2,
      score: 50,
      submittedAt: '2026-09-27T00:00:00Z',
      reviewKind: 'ai_direct',
      formatVersion: 'mixed_v2',
      questions: [
        {
          id: 'q1',
          position: 1,
          pointCode: 'point',
          prompt: '第一题',
          questionType: 'single_choice',
          options: ['甲', '乙'],
          selectedOption: 0,
          correctOption: 0,
          explanation: '第一题解析',
        },
        {
          id: 'q2',
          position: 2,
          pointCode: 'point',
          prompt: '第二题',
          questionType: 'short_answer',
          options: [],
          selectedText: '学生答案',
          referenceAnswer: '标准答案',
          explanation: '第二题解析',
        },
      ],
    })
    state.sendLearningResultTutorMessage.mockResolvedValue({
      resultId: itemId,
      revision: 2,
      processingState: 'idle',
      messages: [
        { id: 'm1', role: 'student', questionId: 'q2', sequence: 1, content: '为什么这样评分？' },
        { id: 'm2', role: 'assistant', questionId: 'q2', sequence: 2, content: '依据评分要点说明。' },
      ],
    })
    const wrapper = await open(Result, 'resultId')
    await wrapper.get('swiper').trigger('change', { detail: { current: 1 } })
    await wrapper.get('.composer-input').setValue('为什么这样评分？')
    await wrapper.get('.send-button').trigger('click')
    await flushPromises()
    expect(state.sendLearningResultTutorMessage).toHaveBeenCalledWith(
      itemId,
      expect.any(String),
      'q2',
      0,
      '为什么这样评分？',
    )
    await wrapper.get('swiper').trigger('change', { detail: { current: 0 } })
    expect(wrapper.get('.chat-log').text()).toContain('依据评分要点说明。')
    expect(wrapper.find('.tutor-head').exists()).toBe(false)
    expect(wrapper.get('#result-question-1-dot-1').classes()).toContain('active')
    expect(wrapper.get('.chat-message:not(.own) .message-meta').text()).toContain('AI 导学助手 · 第 2 题')
    expect(wrapper.get('.chat-message:not(.own) .message-meta-row .message-avatar').text()).toBe('✱')
    expect(wrapper.get('.chat-message.own .message-meta').text()).toBe('第 2 题')
    wrapper.unmount()
  })

  it('keeps the question card fixed while longer questions scroll inside and suggestions follow the selected question', async () => {
    state.getLearningRouteResult.mockResolvedValue({
      id: itemId,
      routeId,
      sourceKind: 'autonomous',
      routeSummary: { title: '完成记录' },
      score: 50,
      submittedAt: '2026-09-27T00:00:00Z',
      reviewKind: 'ai_direct',
      questions: [
        { id: 'q1', position: 1, pointCode: 'point', prompt: '第一题', questionType: 'single_choice', options: [] },
        { id: 'q2', position: 2, pointCode: 'point', prompt: '第二题', questionType: 'single_choice', options: [] },
      ],
    })
    const wrapper = await open(Result, 'resultId')
    expect(wrapper.get('.question-section').attributes('style')).toBeUndefined()
    await wrapper.get('#result-question-1-dot-2').trigger('click')
    await flushPromises()
    expect(wrapper.get('#result-question-1-dot-2').classes()).toContain('active')
    expect(wrapper.get('.question-section').attributes('style')).toBeUndefined()
    expect(wrapper.findAll('.question-scroll')[1].attributes('scroll-y')).toBeDefined()
    await wrapper.findAll('.suggestion')[0].trigger('click')
    await flushPromises()
    expect(state.sendLearningResultTutorMessage).toHaveBeenCalledWith(
      itemId,
      expect.any(String),
      'q2',
      0,
      '请解释一下这个题目的思路。',
    )
    wrapper.unmount()
  })

  it('uses an actionable empty active list and a separate completed empty state', async () => {
    const wrapper = await open(Plans, 'unused')
    expect(wrapper.text()).toContain('目前没有待完成')
    await wrapper.get('button.primary').trigger('click')
    expect(state.goDetail).toHaveBeenCalledWith('/pbl')
    await wrapper.findAll('.tabs button')[1].trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('还没有已完成')
    expect(wrapper.find('button.primary').exists()).toBe(false)
    expect(state.getLearningRoutes).toHaveBeenLastCalledWith('completed', 20, 0)
    wrapper.unmount()
  })

  it('waits for teacher release after route completion without navigating to questions', async () => {
    state.getLearningRoute.mockResolvedValue({
      summary: {
        id: routeId,
        title: '课堂学习路线',
        sourceKind: 'classroom',
        sessionLocator: '课堂研讨',
        nextAction: 'wait_teacher',
        progress: { completedSteps: 2, totalSteps: 2 },
      },
      diagnosisSummary: {},
      steps: [
        { id: 'reading', position: 1, kind: 'reading', title: '资料学习', status: 'completed' },
        { id: 'case', position: 2, kind: 'case', title: '病例学习', status: 'completed', caseId: itemId },
      ],
      testSummary: { id: itemId, questionCount: 3, reviewState: 'pending_review', canStart: false },
      canStartTest: false,
      lockReasons: ['TEST_NOT_RELEASED'],
    })
    const wrapper = await open(Detail, 'unused')
    expect(wrapper.text()).toContain('等待教师开放测试')
    expect(wrapper.get('.page').classes()).toContain('page-three-steps')
    expect(wrapper.get('.route-scroll').attributes('scroll-y')).toBe('false')
    expect(wrapper.get('.route-progress').text()).toBe('2/3')
    expect(wrapper.get('button.primary').attributes('disabled')).toBeDefined()
    await wrapper.get('button.primary').trigger('click')
    expect(state.goDetail).not.toHaveBeenCalled()
    wrapper.unmount()
  })

  it('renders every resource before the final test and uses the expanded progress total', async () => {
    state.getLearningRoute.mockResolvedValue({
      summary: {
        id: routeId,
        title: '多资源学习计划',
        sourceKind: 'autonomous',
        sessionLocator: '自主研讨',
        nextAction: 'case',
        status: 'learning',
        progress: { completedSteps: 2, totalSteps: 4 },
      },
      diagnosisSummary: {},
      steps: [
        { id: 'reading-b', position: 3, kind: 'reading', title: '资料二', status: 'locked' },
        { id: 'case-a', position: 2, kind: 'case', title: '病例一', status: 'available', caseId: itemId },
        { id: 'reading-a', position: 1, kind: 'reading', title: '资料一', status: 'completed' },
        { id: 'case-b', position: 4, kind: 'case', title: '病例二', status: 'locked', caseId: 'another-case' },
      ],
      testSummary: {
        id: itemId,
        questionCount: 3,
        reviewState: 'not_required',
        reviewKind: 'ai_direct',
        canStart: false,
      },
      canStartTest: false,
      lockReasons: ['ROUTE_INCOMPLETE'],
    })
    const wrapper = await open(Detail, 'unused')
    expect(wrapper.get('.page').classes()).toContain('page-multi-steps')
    expect(wrapper.get('.route-scroll').attributes('scroll-y')).toBe('true')
    const items = wrapper.findAll('.timeline-item')
    expect(items).toHaveLength(5)
    expect(items.map((item) => item.find('.step-title').text())).toEqual([
      '资料一',
      '病例一',
      '资料二',
      '病例二',
      '最终测试',
    ])
    expect(wrapper.get('.route-progress').text()).toBe('1/5')
    expect(items[4].find('.step-link').attributes('disabled')).toBeDefined()
    await items[1].find('.step-link').trigger('click')
    expect(state.goDetail).toHaveBeenCalledWith('/case', { routeId, caseId: itemId })
    wrapper.unmount()
  })
})
