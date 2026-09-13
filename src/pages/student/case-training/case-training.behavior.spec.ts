import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import CaseTraining from './case-training.vue'
import type { CaseAttempt } from '@/types/case'

const hooks = vi.hoisted(() => ({
  load: undefined as undefined | ((query?: Record<string, string>) => void),
}))
const getCaseAttemptAsync = vi.hoisted(() => vi.fn())
const sendPatientMessageAsync = vi.hoisted(() => vi.fn())
const submitCaseStageAsync = vi.hoisted(() => vi.fn())
const completeCaseAttemptAsync = vi.hoisted(() => vi.fn())

vi.mock('@dcloudio/uni-app', () => ({
  onLoad: (hook: (query?: Record<string, string>) => void) => {
    hooks.load = hook
  },
  onBackPress: vi.fn(),
}))
vi.mock('@/features/identity/public', () => ({ requireRole: () => true }))
vi.mock('@/features/training/public', () => ({
  getCaseAttemptAsync,
  sendPatientMessageAsync,
  submitCaseStageAsync,
  completeCaseAttemptAsync,
}))
vi.mock('@/platform/navigation', () => ({
  backOrRoute: vi.fn(),
  goReplace: vi.fn(),
  handleBackPress: vi.fn(),
  ROUTES: {
    studentCases: '/pages/student/question/question',
    studentCaseReport: '/pages/student/case-report/case-report',
  },
}))

const historyAttempt: CaseAttempt = {
  id: 'case-ui-test',
  problemId: 'case-1',
  problemVersion: 1,
  status: 'in_progress',
  currentStage: 'history',
  opening: {
    setting: '门诊',
    patientIntro: '45 岁男性',
    chiefComplaint: '发热伴咳嗽 3 天',
  },
  messages: [
    {
      id: 'patient-1',
      role: 'assistant',
      content: '这三天一直发热，也有咳嗽。',
      createdAt: '2026-09-08T00:00:00Z',
    },
  ],
  submissions: [],
  assessmentReady: false,
  startedAt: '2026-09-08T00:00:00Z',
}
const mountPage = () =>
  mount(CaseTraining, {
    global: {
      stubs: { 'scroll-view': { template: '<div><slot /></div>' } },
    },
  })

describe('case training dialogue workspace', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    Object.assign(uni, { pageScrollTo: vi.fn() })
    hooks.load = undefined
    getCaseAttemptAsync.mockResolvedValue(historyAttempt)
    submitCaseStageAsync.mockResolvedValue(undefined)
  })

  it('keeps the patient dialogue primary and folds the clinical notes until requested', async () => {
    const wrapper = mountPage()
    hooks.load?.({ id: historyAttempt.id })
    await flushPromises()

    expect(wrapper.find('.dialogue-panel').exists()).toBe(true)
    expect(wrapper.get('[role="log"]').attributes('aria-label')).toBe('虚拟患者对话记录')
    expect(wrapper.get('.patient-name').text()).toBe('虚拟患者')
    expect(wrapper.get('.reply-count').text()).toContain('1 次回应')
    expect(wrapper.find('.notes-fields').exists()).toBe(false)
    expect(wrapper.get('.bottom .primary').text()).toBe('整理本次问诊')

    await wrapper.get('.prompt-action').trigger('click')
    expect((wrapper.get('.composer-row input').element as HTMLInputElement).value).toBe('症状从什么时候开始？')

    await wrapper.get('.bottom .primary').trigger('click')
    await flushPromises()
    expect(wrapper.find('.notes-fields').exists()).toBe(true)
    expect(submitCaseStageAsync).not.toHaveBeenCalled()
    expect(uni.pageScrollTo).toHaveBeenCalledWith({ selector: '#history-note-fields', duration: 180 })
  })

  it('submits the history only after the learner opens and completes the notes step', async () => {
    const wrapper = mountPage()
    hooks.load?.({ id: historyAttempt.id })
    await flushPromises()

    await wrapper.get('.bottom .primary').trigger('click')
    await wrapper.get('textarea[aria-label="病史小结"]').setValue('中年男性急性发热伴咳嗽。')
    await wrapper.get('input[aria-label="关键发现"]').setValue('发热 3 天，咳嗽')
    await wrapper.get('.bottom .primary').trigger('click')
    await flushPromises()

    expect(submitCaseStageAsync).toHaveBeenCalledWith(historyAttempt.id, {
      stageId: 'history',
      summary: '中年男性急性发热伴咳嗽。',
      keyFindings: ['发热 3 天', '咳嗽'],
    })
  })
})
