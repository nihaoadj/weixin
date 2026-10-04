import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import TeacherLearningResultPage from './result.vue'

const resultId = '46e8274d-f99c-41d2-9681-680a0106874a'
const routeId = '43f2b9c2-13be-491c-98a7-dda4cc09e62a'
const mixedResult = {
  id: resultId,
  routeId,
  sourceKind: 'classroom' as const,
  goalPointCodes: ['pathology.inflammation.vascular'],
  routeSummary: { title: '炎症课堂路线' },
  correctCount: 3,
  questionCount: 5,
  score: 65,
  submittedAt: '2026-09-27T08:00:00Z',
  reviewKind: 'teacher' as const,
  studentId: 12,
  classId: 3,
  sessionId: 9,
  formatVersion: 'mixed_v2' as const,
  questions: [
    {
      id: 'question-1',
      position: 1,
      pointCode: 'pathology.inflammation.vascular',
      questionType: 'single_choice' as const,
      prompt: '血管扩张会导致哪项变化？',
      options: ['血流增加', '细胞坏死', '纤维化', '钙化'],
      selectedOption: 0,
      correctOption: 0,
      pointsAwarded: 15,
      pointsPossible: 15,
      explanation: '血管扩张使局部血流增加。',
    },
    {
      id: 'question-2',
      position: 2,
      pointCode: 'pathology.inflammation.vascular',
      questionType: 'single_choice' as const,
      prompt: '哪项不属于急性炎症？',
      options: ['渗出', '血管反应', '肿瘤转移', '白细胞游出'],
      selectedOption: 2,
      correctOption: 1,
      pointsAwarded: 0,
      pointsPossible: 15,
      explanation: '肿瘤转移不是急性炎症反应。',
    },
    {
      id: 'question-3',
      position: 3,
      pointCode: 'pathology.inflammation.vascular',
      questionType: 'single_choice' as const,
      prompt: '炎症渗出常与什么变化有关？',
      options: ['通透性增加', '核固缩', '钙化', '纤维化'],
      selectedOption: 0,
      correctOption: 0,
      pointsAwarded: 15,
      pointsPossible: 15,
      explanation: '血管通透性增加促进血浆成分外渗。',
    },
    {
      id: 'question-4',
      position: 4,
      pointCode: 'pathology.inflammation.vascular',
      questionType: 'multiple_choice' as const,
      prompt: '选择炎症血管反应的表现。',
      options: ['血管扩张', '通透性增加', '干酪样坏死', '纤维化'],
      selectedOptions: [0, 1],
      correctOptions: [0, 1],
      pointsAwarded: 25,
      pointsPossible: 25,
      explanation: '多选题按实际选择集合与答案集合完全匹配判定。',
    },
    {
      id: 'question-5',
      position: 5,
      pointCode: 'pathology.inflammation.vascular',
      questionType: 'short_answer' as const,
      prompt: '说明血管通透性增加的结果。',
      options: [],
      selectedText: '学生提交的原始答案，包含血浆蛋白外渗。',
      referenceAnswer: '血管通透性增高使富含蛋白的液体外渗，形成炎性渗出。',
      rubricResults: [
        { criterionId: 'protein_exudation', earnedPoints: 10, evidence: '提及血浆蛋白外渗。' },
        { criterionId: 'inflammatory_fluid', earnedPoints: 0, evidence: '未说明炎性液体形成。' },
      ],
      gradingFeedback: '部分要点符合。',
      pointsAwarded: 10,
      pointsPossible: 30,
      explanation: '富含蛋白的液体外渗构成炎性渗出。',
    },
  ],
}
const legacyResult = {
  ...mixedResult,
  formatVersion: 'single_choice_v1' as const,
  score: 0,
  correctCount: 0,
  questionCount: 3,
  questions: mixedResult.questions.slice(0, 3).map((question, index) => {
    const correctOption = question.correctOption ?? 0
    return {
      ...question,
      id: `legacy-question-${index + 1}`,
      position: index + 1,
      selectedOption: (correctOption + 1) % 4,
      pointsAwarded: 0,
      pointsPossible: 100 / 3,
    }
  }),
}

const hooks = vi.hoisted(() => ({
  load: undefined as undefined | ((query?: Record<string, unknown>) => void),
  show: undefined as undefined | (() => void),
  hide: undefined as undefined | (() => void),
  unload: undefined as undefined | (() => void),
  back: undefined as undefined | ((event: { from: 'backbutton' | 'navigateBack' }) => boolean),
}))
const state = vi.hoisted(() => ({
  allowed: true,
  session: { role: 'teacher' as string, openid: 'teacher-1' as string },
  stack: [] as unknown[],
}))
const api = vi.hoisted(() => ({
  getCatalog: vi.fn(),
  getResult: vi.fn(),
}))

const uniApi = {
  reLaunch: vi.fn((options: { success?: () => void; complete?: () => void }) => {
    options.success?.()
    options.complete?.()
  }),
  navigateBack: vi.fn((options: { success?: () => void; complete?: () => void }) => {
    options.success?.()
    options.complete?.()
  }),
  showToast: vi.fn(),
}

vi.mock('@dcloudio/uni-app', () => ({
  onLoad: (hook: (query?: Record<string, unknown>) => void) => {
    hooks.load = hook
  },
  onShow: (hook: () => void) => {
    hooks.show = hook
  },
  onHide: (hook: () => void) => {
    hooks.hide = hook
  },
  onUnload: (hook: () => void) => {
    hooks.unload = hook
  },
  onBackPress: (hook: (event: { from: 'backbutton' | 'navigateBack' }) => boolean) => {
    hooks.back = hook
  },
}))
vi.mock('@/features/identity/public', () => ({
  getSession: () => state.session,
  requireRole: () => state.allowed,
}))
vi.mock('@/features/learning/public', () => ({
  getKnowledgeCatalog: api.getCatalog,
  getTeacherRouteResult: api.getResult,
  learningGoalLabel: (code: string, catalog: Array<{ code: string; title: string }>) =>
    catalog.find((point) => point.code === code)?.title || code,
}))
vi.mock('@/platform/runtime', () => ({ getRuntimeMode: () => 'api' }))

function mountPage() {
  return mount(TeacherLearningResultPage, {
    global: {
      stubs: {
        MedState: {
          props: ['title', 'description', 'actionLabel', 'secondaryActionLabel'],
          emits: ['action', 'secondary-action'],
          template:
            '<div class="med-state"><text>{{ title }}</text><text>{{ description }}</text><button class="state-action" @click="$emit(\'action\')">{{ actionLabel }}</button><button class="state-secondary" @click="$emit(\'secondary-action\')">{{ secondaryActionLabel }}</button></div>',
        },
      },
    },
  })
}

async function showPage(id = resultId, context: Record<string, string> = {}) {
  const wrapper = mountPage()
  hooks.load?.({ resultId: id, ...context })
  hooks.show?.()
  await flushPromises()
  return wrapper
}

describe('teacher learning result page', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    hooks.load = undefined
    hooks.show = undefined
    hooks.hide = undefined
    hooks.unload = undefined
    hooks.back = undefined
    state.allowed = true
    state.session = { role: 'teacher', openid: 'teacher-1' }
    state.stack = []
    api.getCatalog.mockResolvedValue([{ code: 'pathology.inflammation.vascular', title: '血管反应' }])
    api.getResult.mockResolvedValue(mixedResult)
    uniApi.reLaunch.mockImplementation((options) => {
      options.success?.()
      options.complete?.()
    })
    uniApi.navigateBack.mockImplementation((options) => {
      options.success?.()
      options.complete?.()
    })
    vi.stubGlobal('uni', uniApi)
    vi.stubGlobal('getCurrentPages', () => state.stack)
  })

  afterEach(() => vi.unstubAllGlobals())

  it('renders mixed single-choice, multiple-choice and full short-answer evidence read-only', async () => {
    const invalid = await showPage('invalid-id')
    expect(invalid.text()).toContain('学习结果链接无效')
    expect(api.getResult).not.toHaveBeenCalled()

    const wrapper = await showPage()
    expect(api.getResult).toHaveBeenCalledWith(resultId)
    expect(wrapper.get('.format-label').text()).toContain('混合题型')
    expect(wrapper.get('.score').text()).toContain('65')
    expect(wrapper.get('.question-title').text()).toContain('单选题')
    expect(wrapper.get('.question-goal').text()).toContain('血管反应')
    expect(wrapper.text()).toContain('学生选择：A（血管扩张）、B（通透性增加）')
    expect(wrapper.text()).toContain('正确答案：A（血管扩张）、B（通透性增加）')
    expect(wrapper.get('.match-note').text()).toContain('完全一致')
    expect(wrapper.text()).toContain('学生原答案')
    expect(wrapper.text()).toContain('学生提交的原始答案，包含血浆蛋白外渗。')
    expect(wrapper.text()).toContain('血管通透性增高使富含蛋白的液体外渗，形成炎性渗出。')
    expect(wrapper.text()).toContain('protein_exudation · 得分 10')
    expect(wrapper.text()).toContain('inflammatory_fluid · 得分 0')
    expect(wrapper.text()).toContain('未说明炎性液体形成。')
    expect(wrapper.text()).toContain('0 / 15 分')
    expect(wrapper.text()).toContain('富含蛋白的液体外渗构成炎性渗出。')
    expect(wrapper.find('textarea').exists()).toBe(false)
    expect(wrapper.find('input').exists()).toBe(false)
    expect(wrapper.findAll('button').map((button) => button.text())).toEqual(['返回学情'])
  })

  it('renders legacy single-choice results and displays a real zero score without filling missing values', async () => {
    api.getResult.mockResolvedValue(legacyResult)
    const wrapper = await showPage()

    expect(wrapper.get('.format-label').text()).toContain('历史单选题型')
    expect(wrapper.get('.score').text()).toContain('0')
    expect(wrapper.get('.question-points').text()).toContain('0 / 33.33 分')
    expect(wrapper.findAll('.question')).toHaveLength(3)
    expect(wrapper.find('.match-note').exists()).toBe(false)
    expect(wrapper.text()).not.toContain('学生原答案')

    api.getResult.mockResolvedValueOnce({
      ...legacyResult,
      questions: [{ ...legacyResult.questions[0], pointsAwarded: undefined, pointsPossible: undefined }],
    })
    const withoutScore = await showPage()
    expect(withoutScore.get('.question-points').text()).toContain('未提供 / 未提供')
  })

  it('preserves the frozen overall grade while explaining missing short-answer scoring facts', async () => {
    const shortAnswer = mixedResult.questions[4]
    api.getResult.mockResolvedValue({
      ...mixedResult,
      questions: [
        ...mixedResult.questions.slice(0, 4),
        {
          ...shortAnswer,
          pointsAwarded: undefined,
          pointsPossible: undefined,
          rubricResults: undefined,
        },
      ],
    })
    const wrapper = await showPage()

    expect(wrapper.text()).toContain('部分逐题判分记录缺失或不一致')
    expect(wrapper.get('.score').text()).toContain(String(mixedResult.score))
    expect(wrapper.findAll('.question-points')[4].text()).toContain('未提供 / 未提供')
    expect(wrapper.text()).toContain('结果中未提供评分要点。')
  })

  it('keeps an explicitly earned short-answer zero when every recorded rubric item is zero', async () => {
    const shortAnswer = mixedResult.questions[4]
    api.getResult.mockResolvedValue({
      ...mixedResult,
      score: 55,
      correctCount: 2,
      questions: [
        ...mixedResult.questions.slice(0, 4),
        {
          ...shortAnswer,
          rubricResults: shortAnswer.rubricResults?.map((item) => ({ ...item, earnedPoints: 0 })),
          pointsAwarded: 0,
        },
      ],
    })
    const wrapper = await showPage()

    expect(wrapper.get('.score').text()).toContain('55')
    expect(wrapper.findAll('.question-points').at(-1)?.text()).toContain('0 / 30 分')
    expect(wrapper.text()).toContain('protein_exudation · 得分 0')
  })

  it('explains a multi-select mismatch and refuses a fallback zero without both answer sets', async () => {
    const multipleChoice = mixedResult.questions[3]
    api.getResult.mockResolvedValue({
      ...mixedResult,
      score: 40,
      questions: [
        ...mixedResult.questions.slice(0, 3),
        { ...multipleChoice, selectedOptions: [0], pointsAwarded: 0 },
        mixedResult.questions[4],
      ],
    })
    const wrapper = await showPage()

    expect(wrapper.get('.match-note').text()).toContain('不完全一致')
    expect(wrapper.text()).toContain('学生选择：A（血管扩张）')
    expect(wrapper.text()).toContain('正确答案：A（血管扩张）、B（通透性增加）')

    api.getResult.mockResolvedValueOnce({
      ...mixedResult,
      questions: [
        ...mixedResult.questions.slice(0, 3),
        { ...multipleChoice, selectedOptions: undefined, correctOptions: undefined, pointsAwarded: 0 },
        mixedResult.questions[4],
      ],
    })
    const incomplete = await showPage()
    expect(incomplete.get('.score').text()).toContain(String(mixedResult.score))
    expect(incomplete.findAll('.question-points')[3].text()).toContain('0 / 25')
    expect(incomplete.get('.match-note').text()).toContain('集合未记录')
  })

  it('keeps an unavailable result retryable without showing a score while the read fails', async () => {
    api.getResult.mockRejectedValueOnce(new Error('简答题判分尚未完成')).mockResolvedValueOnce(mixedResult)
    const wrapper = await showPage()

    expect(wrapper.get('.med-state').text()).toContain('简答题判分尚未完成')
    expect(wrapper.find('.score').exists()).toBe(false)
    await wrapper.get('.state-action').trigger('click')
    await flushPromises()

    expect(api.getResult).toHaveBeenCalledTimes(2)
    expect(wrapper.get('.score').text()).toContain('65')
  })

  it('keeps an inline retry when a refresh fails after a prior authorized read', async () => {
    const wrapper = await showPage()
    api.getResult.mockRejectedValueOnce(new Error('结果服务暂不可用'))
    hooks.show?.()
    await flushPromises()

    expect(wrapper.get('.inline-error').text()).toContain('结果服务暂不可用')
    expect(wrapper.get('.score').text()).toContain('65')
    await wrapper.get('.retry-inline').trigger('click')
    await flushPromises()
    expect(api.getResult).toHaveBeenCalledTimes(3)
    expect(wrapper.find('.inline-error').exists()).toBe(false)
  })

  it('does not render an autonomous or private result through the classroom detail page', async () => {
    api.getResult.mockResolvedValue({ ...mixedResult, sourceKind: 'autonomous' as const })
    const wrapper = await showPage()

    expect(wrapper.get('.med-state').text()).toContain('仅能查看已授权课堂')
    expect(wrapper.find('.score').exists()).toBe(false)
  })

  it('clears a pending result when teacher authorization is lost', async () => {
    let resolvePending!: (value: typeof mixedResult) => void
    api.getResult.mockReturnValueOnce(
      new Promise<typeof mixedResult>((resolve) => {
        resolvePending = resolve
      }),
    )
    const wrapper = mountPage()
    hooks.load?.({ resultId })
    hooks.show?.()
    await flushPromises()
    expect(wrapper.text()).toContain('正在读取课堂学习结果')

    state.allowed = false
    hooks.show?.()
    resolvePending(mixedResult)
    await flushPromises()

    expect(wrapper.text()).toContain('教师身份已变化')
    expect(wrapper.find('.score').exists()).toBe(false)
  })

  it('ignores an old teacher response after the authenticated teacher changes', async () => {
    let resolveOld!: (value: typeof mixedResult) => void
    api.getResult
      .mockReturnValueOnce(
        new Promise<typeof mixedResult>((resolve) => {
          resolveOld = resolve
        }),
      )
      .mockResolvedValueOnce({ ...mixedResult, score: 80 })
    const wrapper = mountPage()
    hooks.load?.({ resultId })
    hooks.show?.()
    await flushPromises()

    state.session = { role: 'teacher', openid: 'teacher-2' }
    hooks.show?.()
    await flushPromises()
    resolveOld({ ...mixedResult, score: 20 })
    await flushPromises()

    expect(api.getResult).toHaveBeenCalledTimes(2)
    expect(wrapper.get('.score').text()).toContain('80')
    expect(wrapper.get('.score').text()).not.toContain('20')
  })

  it('rejects a response for a different result id and lets the teacher retry', async () => {
    api.getResult.mockResolvedValueOnce({ ...mixedResult, id: 'b034c633-7f50-4389-a606-adb9e55c078b' })
    const wrapper = await showPage()

    expect(wrapper.get('.med-state').text()).toContain('结果编号与当前链接不一致')
    api.getResult.mockResolvedValueOnce(mixedResult)
    await wrapper.get('.state-action').trigger('click')
    await flushPromises()

    expect(wrapper.get('.score').text()).toContain('65')
    expect(api.getResult).toHaveBeenCalledTimes(2)
  })

  it('uses parsed, validated insights context for a no-stack fallback and preserves native back in a stack', async () => {
    const wrapper = await showPage(resultId, {
      tab: 'insights',
      panel: 'students',
      classId: '3',
      sessionId: '9',
      dateFrom: '2026-09-01',
      dateTo: '2026-09-30',
    })
    expect(hooks.back?.({ from: 'navigateBack' })).toBe(false)
    expect(uniApi.reLaunch).not.toHaveBeenCalled()

    expect(hooks.back?.({ from: 'backbutton' })).toBe(true)
    expect(uniApi.reLaunch).toHaveBeenCalledWith(
      expect.objectContaining({
        url: '/pages/teacher/insights/index?panel=students&classId=3&sessionId=9&dateFrom=2026-09-01&dateTo=2026-09-30',
      }),
    )

    state.stack = [{ route: 'teacher/insights/index' }, { route: 'teacher/learning/result' }]
    await wrapper.get('.back').trigger('click')
    expect(uniApi.navigateBack).toHaveBeenCalledWith(expect.objectContaining({ delta: 1 }))
  })

  it('drops invalid return filters and falls back to the insights progress panel', async () => {
    const wrapper = await showPage(resultId, {
      tab: 'insights',
      panel: 'pbl',
      classId: '0',
      sessionId: 'invalid',
      dateFrom: '2026-09-30',
      dateTo: '2026-09-01',
    })
    await wrapper.get('.back').trigger('click')

    expect(uniApi.reLaunch).toHaveBeenCalledWith(
      expect.objectContaining({
        url: '/pages/teacher/insights/index?panel=progress&classId=3&sessionId=9',
      }),
    )
  })
})
