import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import TeacherFinalTestPage from './final-test.vue'

const testId = '7fbbdbd4-365a-4d87-92c8-a94dbde94475'
const routeId = 'c32237ca-b89f-483d-9c91-1508dfbd22bc'
const sourceQuestionId = '71111111-1111-4111-8111-111111111111'
const goalCode = 'pathology.inflammation.vascular'

const hooks = vi.hoisted(() => ({
  load: undefined as undefined | ((query?: Record<string, unknown>) => void),
  show: undefined as undefined | (() => void),
  hide: undefined as undefined | (() => void),
  unload: undefined as undefined | (() => void),
}))
const auth = vi.hoisted(() => ({ allowed: true, session: { role: 'teacher', openid: 'teacher-1' } }))
const api = vi.hoisted(() => ({
  getCatalog: vi.fn(),
  getTest: vi.fn(),
  save: vi.fn(),
  release: vi.fn(),
  changes: vi.fn(),
  retryGeneration: vi.fn(),
  importBankItem: vi.fn(),
  createRequestId: vi.fn(),
  showModal: vi.fn(),
  goDetail: vi.fn(),
  backOrRoute: vi.fn(),
  handleBackPress: vi.fn(),
}))

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
  onBackPress: vi.fn(),
}))
vi.mock('@/features/identity/public', () => ({
  getSession: () => auth.session,
  requireRole: () => auth.allowed,
}))
vi.mock('@/features/learning/public', () => ({
  createLearningRequestId: api.createRequestId,
  getKnowledgeCatalog: api.getCatalog,
  getTeacherFinalTest: api.getTest,
  releaseTeacherFinalTest: api.release,
  requestTeacherTestChanges: api.changes,
  retryTeacherTestGeneration: api.retryGeneration,
  saveTeacherFinalTest: api.save,
  learningGoalLabel: (code: string, catalog: Array<{ code: string; title: string }>) =>
    catalog.find((point) => point.code === code)?.title || code,
}))
vi.mock('@/features/content/public', () => ({ importTeacherQuestionBankItem: api.importBankItem }))
vi.mock('@/platform/navigation', () => ({
  goDetail: api.goDetail,
  backOrRoute: api.backOrRoute,
  handleBackPress: api.handleBackPress,
  ROUTES: {
    teacherWorkspace: '/pages/teacher/index/index',
    teacherPbl: '/pages/teacher/pbl/index',
    teacherTestQueue: '/pages/teacher/pbl/test-queue',
    teacherPblDiagnosticDetail: '/pages/teacher/pbl-diagnostic-detail/pbl-diagnostic-detail',
    teacherQuestionBankImport: '/pages/teacher/content/import-question',
  },
}))

const question = (overrides: Record<string, unknown> = {}) => ({
  id: sourceQuestionId,
  position: 1,
  primaryPointCode: goalCode,
  prompt: '观察到血管扩张，最符合哪项变化？',
  options: ['血流增加', '细胞坏死', '纤维化', '钙化'] as [string, string, string, string],
  correctOption: 0,
  explanation: '血管扩张可导致局部血流增加。',
  sourceDigest: 'a'.repeat(64),
  ...overrides,
})

const teacherTest = (overrides: Record<string, unknown> = {}) => ({
  id: testId,
  routeId,
  title: '炎症课堂最终测试',
  sourceKind: 'classroom',
  classId: 3,
  sessionId: 9,
  studentId: 12,
  currentScopeActive: true,
  diagnosisSummary: {
    diagnosis_outcome: '学生已辨认血管反应。',
    gaps: [{ summary: '解释血流变化' }],
    reasoning_issues: [{ issue: '补充形态依据' }],
  },
  goalPointCodes: [goalCode],
  generationState: 'ready',
  reviewState: 'pending_review',
  reviewKind: 'teacher',
  version: 1,
  draftDigest: 'draft-digest-1',
  questions: [question()],
  feedbackDraft: '',
  ...overrides,
})

const mixedTest = (overrides: Record<string, unknown> = {}) =>
  teacherTest({
    formatVersion: 'mixed_v2',
    questions: [
      question({ id: 'mixed-1', position: 1, questionType: 'single_choice', prompt: '哪项最先出现血管扩张？' }),
      question({ id: 'mixed-2', position: 2, questionType: 'single_choice', prompt: '哪种细胞主要参与急性炎症？' }),
      question({ id: 'mixed-3', position: 3, questionType: 'single_choice', prompt: '哪项表现与渗出有关？' }),
      question({
        id: 'mixed-4',
        position: 4,
        questionType: 'multiple_choice',
        prompt: '哪些变化可促进白细胞到达炎症灶？',
        correctOptions: [0, 2],
      }),
      {
        id: 'mixed-5',
        position: 5,
        primaryPointCode: goalCode,
        prompt: '简述急性炎症中白细胞游出的过程。',
        questionType: 'short_answer',
        referenceAnswer: '白细胞边集、滚动、黏附并穿出血管。',
        rubric: [
          { criterionId: 'margination', description: '指出边集与滚动', maxPoints: 10 },
          { criterionId: 'adhesion', description: '指出稳定黏附', maxPoints: 10 },
          { criterionId: 'emigration', description: '指出穿出血管', maxPoints: 10 },
        ],
        explanation: '白细胞经边集、黏附和穿出到达炎症部位。',
        sourceDigest: 'source-digest-5',
      },
    ],
    ...overrides,
  })

function mountPage() {
  return mount(TeacherFinalTestPage, {
    global: {
      config: { compilerOptions: { isCustomElement: (tag: string) => tag === 'switch' } },
      stubs: {
        picker: {
          props: ['range', 'value', 'disabled'],
          emits: ['change'],
          template:
            '<button class="picker" :disabled="disabled" @click="$emit(\'change\', { detail: { value: Number(value) === 0 ? 1 : 0 } })"><slot /></button>',
        },
        'checkbox-group': {
          name: 'CheckboxGroupStub',
          emits: ['change'],
          template: '<div><slot /></div>',
        },
        checkbox: {
          props: ['value', 'checked', 'disabled'],
          template: '<span />',
        },
      },
    },
  })
}

async function showPage(finalTestId = testId) {
  const wrapper = mountPage()
  hooks.load?.({ finalTestId })
  hooks.show?.()
  await flushPromises()
  return wrapper
}

describe('teacher final-test review page', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    vi.unstubAllGlobals()
    hooks.load = undefined
    hooks.show = undefined
    hooks.hide = undefined
    hooks.unload = undefined
    auth.allowed = true
    auth.session = { role: 'teacher', openid: 'teacher-1' }
    api.getCatalog.mockResolvedValue([{ code: goalCode, title: '血管反应' }])
    api.getTest.mockResolvedValue(teacherTest())
    api.save.mockResolvedValue(teacherTest({ version: 2, draftDigest: 'draft-digest-2' }))
    api.release.mockResolvedValue({})
    api.changes.mockResolvedValue(
      teacherTest({ version: 2, reviewState: 'needs_changes', feedbackDraft: '补充形态依据' }),
    )
    api.retryGeneration.mockResolvedValue(undefined)
    api.importBankItem.mockResolvedValue({ title: '炎症单选题' })
    api.createRequestId.mockImplementation((operation: string) => `${operation}-stable-request`)
    api.showModal.mockImplementation((options: { success?: (result: { confirm: boolean }) => void }) =>
      options.success?.({ confirm: true }),
    )
    vi.stubGlobal('uni', { showModal: api.showModal })
  })

  it('returns directly to the owning PBL root with validated classroom context', async () => {
    const wrapper = mountPage()
    hooks.load?.({
      finalTestId: testId,
      classId: '99',
      sessionId: '9',
      returnSection: 'classrooms',
      reviewKind: 'needs_changes',
    })
    hooks.show?.()
    await flushPromises()
    await wrapper.get('.back').trigger('click')
    expect(api.backOrRoute).toHaveBeenCalledWith('/pages/teacher/pbl/index', {
      section: 'classrooms',
      classId: 3,
      sessionId: 9,
      reviewKind: 'needs_changes',
    })
  })

  it('returns to the independent queue when opened from todo and retains the review category', async () => {
    const wrapper = mountPage()
    hooks.load?.({ finalTestId: testId, returnSection: 'diagnostics', reviewKind: 'generation_failed', sessionId: '9' })
    hooks.show?.()
    await flushPromises()
    expect(wrapper.get('.back').text()).toBe('返回测试待办')
    await wrapper.get('.back').trigger('click')
    expect(api.backOrRoute).toHaveBeenCalledWith('/pages/teacher/pbl/test-queue', {
      section: 'diagnostics',
      classId: 3,
      sessionId: 9,
      reviewKind: 'generation_failed',
    })
  })

  it('requests changes on the same saved test and retries an uncertain receipt with the same payload', async () => {
    api.changes
      .mockRejectedValueOnce(new Error('退改结果暂未确认'))
      .mockResolvedValueOnce(teacherTest({ version: 2, reviewState: 'needs_changes', feedbackDraft: '补充形态依据' }))
    const wrapper = await showPage()
    await wrapper.get('#test-review-feedback').setValue('补充形态依据')
    await wrapper.get('#request-test-changes').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('退改结果暂未确认')
    expect(wrapper.get('#release-test').attributes('disabled')).toBeDefined()
    await wrapper.get('#request-test-changes').trigger('click')
    await flushPromises()
    expect(api.changes).toHaveBeenCalledTimes(2)
    expect(api.changes.mock.calls[0]).toEqual(api.changes.mock.calls[1])
    expect(api.changes).toHaveBeenLastCalledWith(testId, 'teacher-test-changes-stable-request', 1, '补充形态依据')
    expect(wrapper.get('#test-review-feedback').element).toHaveProperty('value', '补充形态依据')
    expect(api.save).not.toHaveBeenCalled()
    expect(api.release).not.toHaveBeenCalled()
  })

  it('requires question edits to be saved before requesting changes', async () => {
    const wrapper = await showPage()
    await wrapper.get('.question textarea').setValue('本地尚未保存的题干')
    await wrapper.get('#test-review-feedback').setValue('补充形态依据')
    expect(wrapper.get('#request-test-changes').attributes('disabled')).toBeDefined()
    await wrapper.get('#request-test-changes').trigger('click')
    expect(api.changes).not.toHaveBeenCalled()
  })

  it('rejects an invalid test link and denies a teacher without permission before reading data', async () => {
    const invalid = await showPage('not-a-uuid')
    expect(invalid.text()).toContain('最终测试链接无效')
    expect(api.getTest).not.toHaveBeenCalled()

    auth.allowed = false
    const denied = await showPage()
    expect(denied.text()).toContain('教师身份已变化')
    expect(api.getTest).not.toHaveBeenCalled()
  })

  it('shows a recoverable load error and reloads the same test', async () => {
    api.getTest.mockRejectedValueOnce(new Error('暂时无法读取测试')).mockResolvedValueOnce(teacherTest())
    const wrapper = await showPage()

    expect(wrapper.get('.state.error').text()).toContain('暂时无法读取测试')
    await wrapper.get('.state.error button').trigger('click')
    await flushPromises()

    expect(api.getTest).toHaveBeenCalledTimes(2)
    expect(wrapper.get('.title').text()).toBe('炎症课堂最终测试')
  })

  it('edits the fixed mixed question types, validates local answers, and limits bank copies to single choice', async () => {
    api.getTest.mockResolvedValue(mixedTest())
    api.save.mockResolvedValueOnce(mixedTest({ version: 2, draftDigest: 'draft-digest-2' }))
    const wrapper = await showPage()
    const rows = wrapper.findAll('.question')

    expect(wrapper.get('.meta').text()).toContain('单目标混合题 v2')
    expect(rows.map((row) => row.find('.question-type').text())).toEqual([
      '单选题',
      '单选题',
      '单选题',
      '多选题',
      '简答题',
    ])
    expect(wrapper.find('.ordering').exists()).toBe(false)
    expect(wrapper.get('.actions').text()).not.toContain('新增题目')
    expect(rows[3].find('.bank-link').exists()).toBe(false)
    expect(rows[4].find('.bank-link').exists()).toBe(false)

    const group = rows[3].findComponent({ name: 'CheckboxGroupStub' })
    group.vm.$emit('change', { detail: { value: ['0'] } })
    await wrapper.get('#save-test-draft').trigger('click')
    await flushPromises()
    expect(api.save).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('三道单选、一题多选、一题简答')

    group.vm.$emit('change', { detail: { value: ['0', '2'] } })
    await rows[4].get('textarea[placeholder="填写简答题标准答案"]').setValue('白细胞先边集滚动，再黏附并穿出血管。')
    await rows[4].get('textarea[aria-label="第 5 题评分要点 1"]').setValue('说明边集与滚动。')
    await wrapper.get('#save-test-draft').trigger('click')
    await flushPromises()

    expect(api.save).toHaveBeenCalledTimes(1)
    const sentQuestions = api.save.mock.calls[0][3]
    expect(sentQuestions).toHaveLength(5)
    expect(sentQuestions[0]).toMatchObject({ questionType: 'single_choice', correctOption: 0 })
    expect(sentQuestions[3]).toMatchObject({ questionType: 'multiple_choice', correctOptions: [0, 2] })
    expect(sentQuestions[4]).toMatchObject({
      questionType: 'short_answer',
      referenceAnswer: '白细胞先边集滚动，再黏附并穿出血管。',
      rubric: [
        { criterionId: 'margination', description: '说明边集与滚动。', maxPoints: 10 },
        { criterionId: 'adhesion', description: '指出稳定黏附', maxPoints: 10 },
        { criterionId: 'emigration', description: '指出穿出血管', maxPoints: 10 },
      ],
    })
  })

  it('keeps invalid edits local, retries the same save request, and can retry a failed release', async () => {
    const saved = teacherTest({ version: 2, draftDigest: 'draft-digest-2' })
    const released = teacherTest({
      version: 3,
      draftDigest: 'released-digest-3',
      reviewState: 'released',
      releasedAt: '2026-09-27T08:00:00Z',
    })
    api.getTest.mockResolvedValueOnce(teacherTest()).mockResolvedValueOnce(released)
    api.save.mockRejectedValueOnce(new Error('网络未确认')).mockResolvedValueOnce(saved)
    api.release.mockRejectedValueOnce(new Error('开放请求未确认')).mockResolvedValueOnce({})
    const wrapper = await showPage()

    expect(wrapper.get('.goals').text()).toContain('血管反应')
    expect(wrapper.get('.diagnosis').text()).toContain('学生已辨认血管反应。')
    await wrapper.find('textarea.textarea').setValue('')
    await wrapper.get('#save-test-draft').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('请补全题干、四个选项、答案、解析')
    expect(api.save).not.toHaveBeenCalled()

    await wrapper.find('textarea.textarea').setValue('更新后的血管反应题干？')
    await wrapper.get('#save-test-draft').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('网络未确认')
    expect(wrapper.text()).toContain('重试同一保存请求')
    expect(wrapper.find('textarea.textarea').attributes('disabled')).toBeDefined()
    await wrapper.get('#save-test-draft').trigger('click')
    await flushPromises()

    expect(api.save).toHaveBeenCalledTimes(2)
    expect(api.save.mock.calls[0]).toEqual(api.save.mock.calls[1])
    expect(api.save.mock.calls[1]).toMatchObject([
      testId,
      'teacher-test-save-stable-request',
      1,
      [{ prompt: '更新后的血管反应题干？', primaryPointCode: goalCode }],
      '',
    ])

    await wrapper.get('.actions .primary').trigger('click')
    expect(api.release).not.toHaveBeenCalled()
    await wrapper.get('#confirm-test-release').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('开放请求未确认')
    expect(wrapper.get('.actions .primary').text()).toBe('重试开放请求')
    expect(wrapper.get('.actions .primary').attributes('disabled')).toBeUndefined()
    expect(wrapper.find('textarea.textarea').attributes('disabled')).toBeDefined()
    await wrapper.get('.actions .primary').trigger('click')
    await wrapper.get('#confirm-test-release').trigger('click')
    await flushPromises()

    expect(api.release).toHaveBeenCalledTimes(2)
    expect(api.release.mock.calls[0]).toEqual(api.release.mock.calls[1])
    expect(api.release.mock.calls[1]).toEqual([testId, 'teacher-test-release-stable-request', 2, 'draft-digest-2', ''])
    expect(wrapper.get('.released').text()).toContain('已开放')
    expect(wrapper.find('.actions').exists()).toBe(false)
    expect(wrapper.get('textarea.textarea').attributes('disabled')).toBeDefined()
  })

  it('retries generation for the same test instead of creating another classroom task', async () => {
    api.getTest
      .mockResolvedValueOnce(teacherTest({ generationState: 'failed', questions: [] }))
      .mockResolvedValueOnce(teacherTest())
    const wrapper = await showPage()

    expect(wrapper.text()).toContain('最终测试生成失败')
    await wrapper.get('.warning button').trigger('click')
    await flushPromises()

    expect(api.retryGeneration).toHaveBeenCalledWith(testId, 'teacher-test-retry-stable-request')
    expect(api.getTest).toHaveBeenCalledTimes(2)
    expect(wrapper.get('.title').text()).toBe('炎症课堂最终测试')
  })

  it('reloads under the new teacher identity and ignores the previous teacher response', async () => {
    let resolveOld!: (value: ReturnType<typeof teacherTest>) => void
    api.getTest
      .mockReturnValueOnce(new Promise((resolve) => (resolveOld = resolve)))
      .mockResolvedValueOnce(teacherTest({ title: '新教师可审阅的测试' }))
    const wrapper = mountPage()
    hooks.load?.({ finalTestId: testId })
    hooks.show?.()
    await flushPromises()

    auth.session = { role: 'teacher', openid: 'teacher-2' }
    hooks.show?.()
    await flushPromises()
    resolveOld(teacherTest({ title: '旧教师测试' }))
    await flushPromises()

    expect(api.getTest).toHaveBeenCalledTimes(2)
    expect(wrapper.get('.title').text()).toBe('新教师可审阅的测试')
  })

  it('polls a generating test while visible and stops polling after hide', async () => {
    vi.useFakeTimers()
    api.getTest.mockResolvedValue(teacherTest({ generationState: 'generating', questions: [] }))
    const wrapper = await showPage()

    expect(wrapper.text()).toContain('最终测试正在生成')
    expect(api.getTest).toHaveBeenCalledTimes(1)
    await vi.advanceTimersByTimeAsync(3000)
    await flushPromises()
    expect(api.getTest).toHaveBeenCalledTimes(2)

    hooks.hide?.()
    await vi.advanceTimersByTimeAsync(6000)
    await flushPromises()
    expect(api.getTest).toHaveBeenCalledTimes(2)
    vi.useRealTimers()
  })

  it('confirms before discarding a local draft after a version conflict', async () => {
    api.save.mockRejectedValueOnce(new Error('VERSION_CONFLICT: 测试版本已变化'))
    const wrapper = await showPage()
    await wrapper.find('textarea.textarea').setValue('本地仍保留的题干')
    await wrapper.get('#save-test-draft').trigger('click')
    await flushPromises()

    expect(wrapper.get('.conflict').text()).toContain('你的本地编辑仍保留')
    await wrapper.get('.conflict button').trigger('click')
    await flushPromises()

    expect(api.showModal).toHaveBeenCalledWith(expect.objectContaining({ title: '重新加载最新版本' }))
    expect(api.getTest).toHaveBeenCalledTimes(2)
    expect(wrapper.find('.conflict').exists()).toBe(false)
    expect(wrapper.find('textarea.textarea').element).toHaveProperty('value', question().prompt)
  })

  it('opens the standalone source-copy page for a saved single-choice question without writing Content', async () => {
    const wrapper = await showPage()

    await wrapper.get('.bank-link').trigger('click')
    expect(api.goDetail).toHaveBeenCalledWith('/pages/teacher/content/import-question', {
      sourceId: sourceQuestionId,
      finalTestId: testId,
    })
    expect(api.importBankItem).not.toHaveBeenCalled()
    expect(api.save).not.toHaveBeenCalled()
    expect(wrapper.find('.bank-editor').exists()).toBe(false)
  })

  it('keeps inactive classroom history readable and removes review writes', async () => {
    api.getTest.mockResolvedValue(teacherTest({ currentScopeActive: false }))
    const wrapper = await showPage()
    expect(wrapper.text()).toContain('班级已归档或学生已离班')
    expect(wrapper.get('textarea.textarea').element).toHaveProperty('value', question().prompt)
    expect(wrapper.get('textarea.textarea').attributes('disabled')).toBeDefined()
    expect(wrapper.find('#save-test-draft').exists()).toBe(false)
    expect(wrapper.find('#request-test-changes').exists()).toBe(false)
    expect(wrapper.find('#release-test').exists()).toBe(false)
    expect(api.save).not.toHaveBeenCalled()
    expect(api.changes).not.toHaveBeenCalled()
    expect(api.release).not.toHaveBeenCalled()
  })

  it('does not offer generation retry on inactive history or assume missing scope is writable', async () => {
    api.getTest.mockResolvedValue(teacherTest({ currentScopeActive: false, generationState: 'failed', questions: [] }))
    const wrapper = await showPage()
    expect(wrapper.text()).not.toContain('重试生成测试')
    expect(api.retryGeneration).not.toHaveBeenCalled()
    wrapper.unmount()
    api.getTest.mockResolvedValue(teacherTest({ currentScopeActive: undefined }))
    const withoutScope = await showPage()
    expect(withoutScope.find('#save-test-draft').exists()).toBe(false)
    expect(withoutScope.find('#release-test').exists()).toBe(false)
  })

  it('hides the copy action for a question without a persisted UUID and digest', async () => {
    api.getTest.mockResolvedValue(teacherTest({ questions: [question({ id: null, sourceDigest: undefined })] }))
    const wrapper = await showPage()

    expect(wrapper.find('.bank-link').exists()).toBe(false)
    expect(wrapper.text()).toContain('此题没有可用的已保存来源，暂不能复制。')
    expect(api.importBankItem).not.toHaveBeenCalled()
  })

  it('requires a clean saved test before opening the copy workflow', async () => {
    const wrapper = await showPage()
    await wrapper.find('textarea.textarea').setValue('尚未保存的来源题干')

    expect(wrapper.find('.bank-link').exists()).toBe(false)
    expect(wrapper.text()).toContain('先保存测试，才能复制已确认的题目来源。')
    expect(api.goDetail).not.toHaveBeenCalled()
    expect(api.importBankItem).not.toHaveBeenCalled()
  })
})
