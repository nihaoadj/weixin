import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import CaseEdit from './case-edit.vue'
import type { CaseDraftGenerateResult } from '@/types/case'

const generateCaseDraftAsync = vi.hoisted(() => vi.fn())
const showToast = vi.hoisted(() => vi.fn())
const pageScrollTo = vi.hoisted(() => vi.fn())
const backOrRoute = vi.hoisted(() => vi.fn())
const handleBackPress = vi.hoisted(() => vi.fn())

vi.mock('@dcloudio/uni-app', () => ({ onBackPress: vi.fn(), onLoad: vi.fn() }))
vi.mock('@/features/identity/public', () => ({ requireRole: () => true }))
vi.mock('@/platform/navigation', () => ({
  backOrRoute,
  handleBackPress,
  ROUTES: { teacherWorkspace: '/workspace' },
}))
vi.mock('@/features/content/public', () => ({
  cloneCaseVersionAsync: vi.fn(),
  generateCaseDraftAsync,
  getCaseAuthoringAsync: vi.fn(),
  getGuidedCasesAsync: vi.fn(),
  publishGuidedCaseAsync: vi.fn(),
  saveGuidedCaseAsync: vi.fn(),
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

beforeEach(() => {
  generateCaseDraftAsync.mockReset()
  showToast.mockReset()
  pageScrollTo.mockReset()
  backOrRoute.mockReset()
  handleBackPress.mockReset()
})

describe('case authoring flow', () => {
  it('offers a stack-safe exit before a new case has been generated', async () => {
    const wrapper = mount(CaseEdit)
    const returnButton = wrapper.findAll('button').find((button) => button.text() === '返回内容列表')
    await returnButton?.trigger('click')
    expect(backOrRoute).toHaveBeenCalledWith('/workspace', { tab: 'problems' })
  })

  it('confirms before discarding a generated case that has not been saved', async () => {
    const showModal = vi.fn()
    generateCaseDraftAsync.mockResolvedValue(structuredClone(draft))
    vi.stubGlobal('uni', { showToast, showModal, pageScrollTo })
    const wrapper = mount(CaseEdit)

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
    const wrapper = mount(CaseEdit)

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
})
