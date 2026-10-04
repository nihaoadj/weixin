import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import CaseEdit from './case-edit.vue'
import type { CaseDraftGenerateResult } from '@/types/case'

const hooks = vi.hoisted(() => ({
  load: undefined as undefined | ((query?: Record<string, string>) => void),
  show: undefined as undefined | (() => void),
}))
const identity = vi.hoisted(() => ({
  current: { openid: 'teacher-1', role: 'teacher' } as { openid: string; role: string },
}))
const getKnowledgeCatalog = vi.hoisted(() => vi.fn())
const getCaseAuthoringAsync = vi.hoisted(() => vi.fn())
const getGuidedCasesAsync = vi.hoisted(() => vi.fn())
const saveGuidedCaseAsync = vi.hoisted(() => vi.fn())
const generateCaseDraftAsync = vi.hoisted(() => vi.fn())
const showToast = vi.hoisted(() => vi.fn())
const pageScrollTo = vi.hoisted(() => vi.fn())
const backOrRoute = vi.hoisted(() => vi.fn())
const handleBackPress = vi.hoisted(() => vi.fn())

vi.mock('@dcloudio/uni-app', () => ({
  onBackPress: vi.fn(),
  onLoad: (hook: typeof hooks.load) => {
    hooks.load = hook
  },
  onShow: (hook: typeof hooks.show) => {
    hooks.show = hook
  },
}))
vi.mock('@/features/identity/public', () => ({ requireRole: () => true, getSession: () => identity.current }))
vi.mock('@/platform/navigation', () => ({
  backOrRoute,
  handleBackPress,
  ROUTES: { teacherContent: '/content' },
}))
vi.mock('@/features/learning/public', () => ({ getKnowledgeCatalog }))
vi.mock('@/features/content/public', () => ({
  cloneCaseVersionAsync: vi.fn(),
  generateCaseDraftAsync,
  getCaseAuthoringAsync,
  getGuidedCasesAsync,
  publishGuidedCaseAsync: vi.fn(),
  saveGuidedCaseAsync,
  submitGuidedCaseForReviewAsync: vi.fn(),
}))

const draft: CaseDraftGenerateResult = {
  title: '急性胸痛：危险分层与证据推理',
  description: '训练证据推理与安全边界。',
  specialty: '急诊医学',
  difficulty: 'intermediate',
  estimatedMinutes: 20,
  generationMode: 'fallback',
  safetyNotice: '仅供教学讨论，不构成诊疗建议。',
  caseDefinition: {
    schemaVersion: 2,
    opening: { setting: '急诊', patientIntro: '患者胸痛 2 小时。', chiefComplaint: '胸痛伴出汗。' },
    stageInstructions: {
      history: '补充病史。',
      problem_representation: '归纳问题。',
      differential: '列出鉴别诊断。',
      tests: '选择检查。',
      management: '说明处置。',
    },
    facts: [
      {
        id: 'fact_1',
        category: 'history',
        label: '疼痛性质',
        value: '压榨样疼痛。',
        triggers: ['疼痛'],
        revealStage: 'history',
      },
    ],
    referenceReasoning: {
      problemRepresentation: '急性胸痛伴出汗，需要首先排除高危心血管事件。',
      differentials: [{ diagnosis: '急性冠脉综合征', supportingFactIds: ['fact_1'], opposingFactIds: [], priority: 1 }],
      tests: [{ name: '心电图', purpose: '识别缺血改变。', priority: 'necessary', resultFactId: null }],
      management: [{ action: '监测生命体征', rationale: '识别高危变化。', priority: 1, safetyCritical: true }],
    },
  },
  rubric: {
    dimensions: [
      {
        id: 'information_gathering',
        label: '信息采集',
        weight: 20,
        stageIds: ['history'],
        criteria: [
          { id: 'criterion_1', label: '追问疼痛特点', keywords: ['疼痛'], feedback: '继续补充病史。', critical: false },
        ],
      },
    ],
  },
}

function mountEditor(query: Record<string, string> = {}) {
  const wrapper = mount(CaseEdit, {
    global: { stubs: { picker: { template: '<div class="knowledge-stub"><slot /></div>' } } },
  })
  hooks.load?.(query)
  return wrapper
}

const catalog = [
  { code: 'pathology.cell.injury', title: '细胞损伤', systemLabel: '细胞损伤与适应' },
  { code: 'pathology.inflammation.vascular', title: '炎症血管反应', systemLabel: '炎症' },
]
async function toSaveStep(wrapper: ReturnType<typeof mountEditor>) {
  for (let index = 0; index < 4; index += 1) {
    await wrapper
      .findAll('button')
      .find((button) => button.text() === '下一步')
      ?.trigger('click')
  }
}

beforeEach(() => {
  getKnowledgeCatalog.mockReset()
  getKnowledgeCatalog.mockResolvedValue(catalog)
  identity.current = { openid: 'teacher-1', role: 'teacher' }
  hooks.load = undefined
  hooks.show = undefined
  getCaseAuthoringAsync.mockReset()
  getGuidedCasesAsync.mockReset()
  saveGuidedCaseAsync.mockReset()
  getGuidedCasesAsync.mockResolvedValue([
    {
      id: 'case-1',
      slug: 'case-slug',
      status: '已发布',
      medicalReviewStatus: 'approved',
      allowedActions: ['edit', 'delete'],
      knowledgePointCodes: ['pathology.cell.injury'],
    },
  ])
  getCaseAuthoringAsync.mockResolvedValue(structuredClone(draft))
  saveGuidedCaseAsync.mockResolvedValue({ id: 'case-1', slug: 'case-slug' })
  vi.stubGlobal('uni', { showToast, pageScrollTo, showModal: vi.fn() })
  generateCaseDraftAsync.mockReset()
  showToast.mockReset()
  pageScrollTo.mockReset()
  backOrRoute.mockReset()
  handleBackPress.mockReset()
})

describe('case authoring flow', () => {
  it('offers a stack-safe exit before a new case has been generated', async () => {
    const wrapper = mountEditor()
    const returnButton = wrapper.findAll('button').find((button) => button.text() === '返回内容列表')
    await returnButton?.trigger('click')
    expect(backOrRoute).toHaveBeenCalledWith('/content', { resource: 'cases' })
  })

  it('confirms before discarding a generated case that has not been saved', async () => {
    const showModal = vi.fn()
    generateCaseDraftAsync.mockResolvedValue(structuredClone(draft))
    vi.stubGlobal('uni', { showToast, showModal, pageScrollTo })
    const wrapper = mountEditor()

    await wrapper
      .findAll('button')
      .find((button) => button.text() === '生成病例草稿')
      ?.trigger('click')
    await flushPromises()
    await wrapper
      .findAll('button')
      .find((button) => button.text() === '返回内容列表')
      ?.trigger('click')

    expect(showModal).toHaveBeenCalledWith(expect.objectContaining({ title: '离开病例编排？', confirmText: '离开' }))
    expect(backOrRoute).not.toHaveBeenCalled()
  })

  it('keeps the current reference text as the step-three validation source', async () => {
    generateCaseDraftAsync.mockResolvedValue(structuredClone(draft))
    vi.stubGlobal('uni', { showToast, pageScrollTo })
    const wrapper = mountEditor()

    await wrapper
      .findAll('button')
      .find((button) => button.text() === '生成病例草稿')
      ?.trigger('click')
    await flushPromises()
    await wrapper
      .findAll('button')
      .find((button) => button.text() === '下一步')
      ?.trigger('click')
    await wrapper
      .findAll('button')
      .find((button) => button.text() === '下一步')
      ?.trigger('click')
    expect(wrapper.text()).toContain('参考推理')

    await wrapper.get('textarea[name="case-reference-representation"]').setValue('')
    await wrapper
      .findAll('button')
      .find((button) => button.text() === '下一步')
      ?.trigger('click')
    expect(wrapper.text()).toContain('参考推理')
    expect(showToast).toHaveBeenCalledWith({ title: '请补充参考表征和至少一项鉴别诊断', icon: 'none' })
    expect(pageScrollTo).toHaveBeenCalledWith({ selector: '.step-overview', duration: 0 })
  })

  it.each(['pending', 'approved', 'rejected'])(
    'edits a legacy %s case in place and saves without lifecycle controls',
    async (medicalReviewStatus) => {
      getGuidedCasesAsync.mockResolvedValue([
        {
          id: 'case-1',
          slug: 'case-slug',
          status: '已发布',
          medicalReviewStatus,
          allowedActions: ['edit', 'delete'],
          knowledgePointCodes: ['pathology.cell.injury'],
        },
      ])
      const wrapper = mountEditor({ id: 'case-1', keyword: '胸痛', status: 'approved' })
      await flushPromises()
      expect(getCaseAuthoringAsync).toHaveBeenCalledWith('case-1')
      expect(wrapper.get('input[name="case-title"]').attributes('disabled')).toBeUndefined()
      expect(wrapper.text()).not.toMatch(/医学审核|发布病例|草稿，|只读查看/)
      await wrapper.get('input[name="case-title"]').setValue('更新后的病例')
      for (let index = 0; index < 4; index += 1) {
        await wrapper
          .findAll('button')
          .find((button) => button.text() === '下一步')
          ?.trigger('click')
      }
      await wrapper
        .findAll('button')
        .find((button) => button.text() === '保存病例')
        ?.trigger('click')
      await flushPromises()
      expect(saveGuidedCaseAsync).toHaveBeenCalledWith(expect.objectContaining({ title: '更新后的病例' }), 'case-1', {
        slug: 'case-slug',
        knowledgePointCodes: ['pathology.cell.injury'],
      })
      expect(showToast).toHaveBeenCalledWith({ title: '病例已保存', icon: 'success' })
    },
  )

  it('discards a pending authoring response when the teacher changes', async () => {
    let resolveDraft!: (value: CaseDraftGenerateResult) => void
    getCaseAuthoringAsync.mockReturnValue(
      new Promise<CaseDraftGenerateResult>((resolve) => {
        resolveDraft = resolve
      }),
    )
    const wrapper = mountEditor({ id: 'case-1' })
    await flushPromises()
    identity.current = { openid: 'teacher-2', role: 'teacher' }
    hooks.show?.()
    resolveDraft(structuredClone(draft))
    await flushPromises()
    expect(wrapper.text()).toContain('教师账号已变更')
    expect(wrapper.text()).not.toContain(draft.title)
    expect(saveGuidedCaseAsync).not.toHaveBeenCalled()
  })

  it('blocks editor access without owner edit permission', async () => {
    getGuidedCasesAsync.mockResolvedValue([{ id: 'case-1', allowedActions: [] }])
    const wrapper = mountEditor({ id: 'case-1' })
    await flushPromises()
    expect(wrapper.text()).toContain('当前账号无权编辑此病例')
    expect(getCaseAuthoringAsync).not.toHaveBeenCalled()
  })

  it('sends only one save and suppresses late success after the teacher changes', async () => {
    let resolveSave!: (value: { id: string; slug: string }) => void
    saveGuidedCaseAsync.mockReturnValue(
      new Promise<{ id: string; slug: string }>((resolve) => {
        resolveSave = resolve
      }),
    )
    const wrapper = mountEditor({ id: 'case-1' })
    await flushPromises()
    for (let index = 0; index < 4; index += 1) {
      await wrapper
        .findAll('button')
        .find((button) => button.text() === '下一步')
        ?.trigger('click')
    }
    const saveButton = wrapper.findAll('button').find((button) => button.text() === '保存病例')!
    await saveButton.trigger('click')
    await saveButton.trigger('click')
    expect(saveGuidedCaseAsync).toHaveBeenCalledTimes(1)
    identity.current = { openid: 'teacher-2', role: 'teacher' }
    hooks.show?.()
    resolveSave({ id: 'case-1', slug: 'case-slug' })
    await flushPromises()
    expect(showToast).not.toHaveBeenCalled()
    expect(backOrRoute).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('教师账号已变更')
  })

  it('retains the edited case on a failed save and asks before leaving', async () => {
    const showModal = vi.fn()
    vi.stubGlobal('uni', { showToast, pageScrollTo, showModal })
    saveGuidedCaseAsync.mockRejectedValueOnce(new Error('暂时无法保存'))
    const wrapper = mountEditor({ id: 'case-1' })
    await flushPromises()
    await wrapper.get('input[name="case-title"]').setValue('保留的编辑')
    for (let index = 0; index < 4; index += 1) {
      await wrapper
        .findAll('button')
        .find((button) => button.text() === '下一步')
        ?.trigger('click')
    }
    await wrapper
      .findAll('button')
      .find((button) => button.text() === '保存病例')
      ?.trigger('click')
    await flushPromises()
    expect(showToast).toHaveBeenCalledWith({ title: '暂时无法保存', icon: 'none' })
    await wrapper
      .findAll('button')
      .find((button) => button.text() === '返回内容列表')
      ?.trigger('click')
    expect(showModal).toHaveBeenCalledWith(expect.objectContaining({ title: '离开病例编排？' }))
    expect(backOrRoute).not.toHaveBeenCalled()
  })

  it('requires an explicit knowledge point for a new case and sends the selection on save', async () => {
    generateCaseDraftAsync.mockResolvedValue(structuredClone(draft))
    const wrapper = mountEditor()
    await wrapper
      .findAll('button')
      .find((button) => button.text() === '生成病例草稿')
      ?.trigger('click')
    await flushPromises()
    expect(wrapper.get('.knowledge-picker').text()).toContain('请选择知识点')
    await toSaveStep(wrapper)
    const saveButton = wrapper.findAll('button').find((button) => button.text() === '保存病例')!
    expect(saveButton.attributes('disabled')).toBeDefined()
    await saveButton.trigger('click')
    expect(saveGuidedCaseAsync).not.toHaveBeenCalled()
    await wrapper.get('.knowledge-stub').trigger('change', { detail: { value: 2 } })
    expect(wrapper.get('.knowledge-picker').text()).toContain('炎症血管反应')
    await saveButton.trigger('click')
    await flushPromises()
    expect(saveGuidedCaseAsync).toHaveBeenCalledWith(expect.anything(), undefined, {
      slug: undefined,
      knowledgePointCodes: ['pathology.inflammation.vascular'],
    })
  })

  it('preserves all existing knowledge bindings until the teacher explicitly selects a new point', async () => {
    getGuidedCasesAsync.mockResolvedValue([
      {
        id: 'case-1',
        slug: 'case-slug',
        allowedActions: ['edit'],
        knowledgePointCodes: catalog.map((point) => point.code),
      },
    ])
    const wrapper = mountEditor({ id: 'case-1' })
    await flushPromises()
    expect(wrapper.get('.knowledge-picker').text()).toContain('细胞损伤、炎症血管反应')
    await toSaveStep(wrapper)
    await wrapper
      .findAll('button')
      .find((button) => button.text() === '保存病例')
      ?.trigger('click')
    await flushPromises()
    expect(saveGuidedCaseAsync).toHaveBeenLastCalledWith(expect.anything(), 'case-1', {
      slug: 'case-slug',
      knowledgePointCodes: catalog.map((point) => point.code),
    })
    await wrapper.get('.knowledge-stub').trigger('change', { detail: { value: 1 } })
    await wrapper
      .findAll('button')
      .find((button) => button.text() === '保存病例')
      ?.trigger('click')
    await flushPromises()
    expect(saveGuidedCaseAsync).toHaveBeenLastCalledWith(expect.anything(), 'case-1', {
      slug: 'case-slug',
      knowledgePointCodes: ['pathology.cell.injury'],
    })
  })

  it('keeps catalog errors visible and allows a guarded retry before saving', async () => {
    getKnowledgeCatalog.mockRejectedValueOnce(new Error('目录暂不可读'))
    const wrapper = mountEditor({ id: 'case-1' })
    await flushPromises()
    expect(wrapper.text()).toContain('目录暂不可读')
    await toSaveStep(wrapper)
    const saveButton = wrapper.findAll('button').find((button) => button.text() === '保存病例')!
    expect(saveButton.attributes('disabled')).toBeDefined()
    await saveButton.trigger('click')
    expect(saveGuidedCaseAsync).not.toHaveBeenCalled()
    await wrapper.get('.binding-retry').trigger('click')
    await flushPromises()
    expect(getKnowledgeCatalog).toHaveBeenCalledTimes(2)
    expect(wrapper.text()).not.toContain('目录暂不可读')
    expect(wrapper.get('.knowledge-picker').text()).toContain('细胞损伤')
  })

  it('blocks saving when the catalog is empty or still loading', async () => {
    let resolveCatalog!: (value: typeof catalog) => void
    getKnowledgeCatalog.mockReturnValueOnce(
      new Promise<typeof catalog>((resolve) => {
        resolveCatalog = resolve
      }),
    )
    const wrapper = mountEditor({ id: 'case-1' })
    await flushPromises()
    expect(wrapper.text()).toContain('正在读取知识点目录')
    await toSaveStep(wrapper)
    expect(
      wrapper
        .findAll('button')
        .find((button) => button.text() === '保存病例')!
        .attributes('disabled'),
    ).toBeDefined()
    resolveCatalog([])
    await flushPromises()
    expect(wrapper.text()).toContain('知识点目录为空')
    expect(saveGuidedCaseAsync).not.toHaveBeenCalled()
  })

  it('discards a late catalog result after the teacher identity changes', async () => {
    let resolveCatalog!: (value: typeof catalog) => void
    getKnowledgeCatalog.mockReturnValueOnce(
      new Promise<typeof catalog>((resolve) => {
        resolveCatalog = resolve
      }),
    )
    const wrapper = mountEditor({ id: 'case-1' })
    await flushPromises()
    identity.current = { openid: 'teacher-2', role: 'teacher' }
    hooks.show?.()
    resolveCatalog(catalog)
    await flushPromises()
    expect(wrapper.text()).toContain('教师账号已变更')
    expect(wrapper.text()).not.toContain('细胞损伤')
    expect(wrapper.find('.knowledge-picker').exists()).toBe(false)
  })

  it('blocks legacy bindings above the API limit without truncating and saves only after explicit reselection', async () => {
    const legacyCatalog = Array.from({ length: 6 }, (_, index) => ({
      code: `pathology.legacy.${index}`,
      title: `旧知识点${index}`,
      systemLabel: '病理学',
    }))
    getKnowledgeCatalog.mockResolvedValue(legacyCatalog)
    getGuidedCasesAsync.mockResolvedValue([
      {
        id: 'case-1',
        slug: 'case-slug',
        allowedActions: ['edit'],
        knowledgePointCodes: legacyCatalog.map((point) => point.code),
      },
    ])
    const wrapper = mountEditor({ id: 'case-1' })
    await flushPromises()
    expect(wrapper.get('.knowledge-picker').text()).toContain(
      '旧知识点0、旧知识点1、旧知识点2、旧知识点3、旧知识点4、旧知识点5',
    )
    await toSaveStep(wrapper)
    const saveButton = wrapper.findAll('button').find((button) => button.text() === '保存病例')!
    await saveButton.trigger('click')
    await flushPromises()
    expect(saveGuidedCaseAsync).not.toHaveBeenCalled()
    expect(showToast).toHaveBeenCalledWith({ title: '请选择最多3个知识点', icon: 'none' })
    expect(wrapper.get('.knowledge-picker').text()).toContain('旧知识点5')
    await wrapper.get('.knowledge-stub').trigger('change', { detail: { value: 1 } })
    await saveButton.trigger('click')
    await flushPromises()
    expect(saveGuidedCaseAsync).toHaveBeenCalledWith(expect.anything(), 'case-1', {
      slug: 'case-slug',
      knowledgePointCodes: ['pathology.legacy.0'],
    })
  })
})
