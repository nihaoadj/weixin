import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ReportDetail from '@/pages/teacher/detail/detail.vue'
import ReportReference from './ReportReference.vue'
import type { Report } from '@/types/domain'

const { findReport, reviewReport, backOrRoute, handleBackPress } = vi.hoisted(() => ({
  findReport: vi.fn(),
  reviewReport: vi.fn(),
  backOrRoute: vi.fn(),
  handleBackPress: vi.fn(),
}))
vi.mock('@/features/reports/public', () => ({ findReportAsync: findReport, reviewReportAsync: reviewReport }))
vi.mock('@/features/identity/public', () => ({ requireRole: () => true }))
vi.mock('@/platform/navigation', () => ({
  backOrRoute,
  handleBackPress,
  ROUTES: { teacherWorkspace: '/workspace' },
}))
vi.mock('@dcloudio/uni-app', () => ({
  onLoad: (hook: (query: object) => void) => hook({ reportId: 'report-review-test' }),
  onBackPress: vi.fn(),
}))

function exampleReport(): Report {
  return {
    id: 'report-review-test',
    conversationId: 'conversation-test',
    studentId: 'student-test',
    studentName: '测试学生',
    status: '待批阅',
    createdAt: '2026-08-31T00:00:00Z',
    messages: [
      { id: 'm1', role: 'user', content: '第一行原文\n第二行依据', timestamp: '2026-08-31T00:00:00Z' },
      { id: 'm2', role: 'assistant', content: '教学参考意见', timestamp: '2026-08-31T00:01:00Z' },
    ],
    analysis: {
      score: 78,
      summary: '仅供教师核验的摘要',
      errors: [{ content: '需补充依据', suggestion: '说明推理过程' }],
      strengths: ['已经表达主要判断'],
      generalSuggestions: ['下一步梳理证据'],
    },
  }
}

beforeEach(() => {
  findReport.mockReset().mockResolvedValue(exampleReport())
  reviewReport.mockReset()
})

describe('teacher report review document', () => {
  it('renders the original transcript and all reference sections without nested cards', async () => {
    const wrapper = mount(ReportDetail)
    await flushPromises()
    expect(findReport).toHaveBeenCalledWith('report-review-test')
    expect(wrapper.get('[aria-level="1"]').text()).toBe('测试学生的推理记录')
    expect(wrapper.findAll('.transcript-entry')).toHaveLength(2)
    expect(wrapper.findAll('.speaker').map((item) => item.text())).toEqual(['学生', 'AI 教学助手'])
    expect(wrapper.get('.entry-content').text()).toContain('第一行原文\n第二行依据')
    for (const text of ['仅供教师核验的摘要', '已经表达主要判断', '需补充依据', '下一步梳理证据']) {
      expect(wrapper.text()).toContain(text)
    }
    expect(wrapper.find('.card').exists()).toBe(false)
    expect(wrapper.get('label[for="teacher-score"]').text()).toContain('0–100')
    expect(wrapper.get('label[for="teacher-feedback"]').text()).toContain('选填')
  })

  it('keeps validation visible and never submits a missing or out-of-range score', async () => {
    const wrapper = mount(ReportDetail)
    await flushPromises()
    await wrapper.get('.submit-button').trigger('click')
    await flushPromises()
    expect(wrapper.get('#teacher-score-error').text()).toContain('请填写')
    expect(wrapper.get('input').attributes('aria-invalid')).toBe('true')
    await wrapper.get('input').setValue('101')
    await wrapper.get('.submit-button').trigger('click')
    await flushPromises()
    expect(wrapper.get('#teacher-score-error').text()).toContain('0–100')
    expect(reviewReport).not.toHaveBeenCalled()
  })

  it('preserves entered feedback after a failed save and allows explicit retry', async () => {
    reviewReport.mockRejectedValueOnce(new Error('网络暂不可用'))
    const wrapper = mount(ReportDetail)
    await flushPromises()
    await wrapper.get('input').setValue('88')
    await wrapper.get('textarea').setValue('请补充推理依据。')
    await wrapper.get('.submit-button').trigger('click')
    await flushPromises()
    expect(wrapper.get('.submit-error').text()).toBe('网络暂不可用')
    expect((wrapper.get('input').element as HTMLInputElement).value).toBe('88')
    expect((wrapper.get('textarea').element as HTMLTextAreaElement).value).toBe('请补充推理依据。')
    expect(backOrRoute).not.toHaveBeenCalled()
    reviewReport.mockResolvedValueOnce({ ...exampleReport(), status: '已批阅' })
    await wrapper.get('.submit-button').trigger('click')
    await flushPromises()
    expect(reviewReport).toHaveBeenLastCalledWith('report-review-test', 88, '请补充推理依据。', [])
    expect(backOrRoute).toHaveBeenCalledWith('/workspace', { tab: 'reports', section: 'records' })
  })

  it('keeps reviewed reports editable and disables duplicate submissions', async () => {
    findReport.mockResolvedValueOnce({
      ...exampleReport(),
      status: '已批阅',
      teacherScore: 90,
      teacherFeedback: '已有反馈',
    })
    let resolveSave: (report: Report) => void = () => {}
    reviewReport.mockImplementationOnce(
      () =>
        new Promise<Report>((resolve) => {
          resolveSave = resolve
        }),
    )
    const wrapper = mount(ReportDetail)
    await flushPromises()
    expect(wrapper.get('.submit-button').text()).toBe('更新批阅')
    expect((wrapper.get('input').element as HTMLInputElement).value).toBe('90')
    expect(wrapper.get('input').attributes('disabled')).toBeUndefined()
    await wrapper.get('.submit-button').trigger('click')
    expect(wrapper.get('.submit-button').attributes('disabled')).toBeDefined()
    expect(wrapper.get('.submit-button').attributes('aria-disabled')).toBe('true')
    expect(wrapper.get('textarea').attributes('disabled')).toBeDefined()
    await wrapper.get('.submit-button').trigger('click')
    expect(reviewReport).toHaveBeenCalledTimes(1)
    resolveSave({ ...exampleReport(), status: '已批阅' })
    await flushPromises()
  })

  it('exposes a retryable loading error and a safe return for unsubmitted reports', async () => {
    findReport.mockRejectedValueOnce(new Error('无法读取报告'))
    const wrapper = mount(ReportDetail)
    await flushPromises()
    expect(wrapper.text()).toContain('报告加载失败')
    expect(wrapper.find('.feedback-form').exists()).toBe(false)
    findReport.mockResolvedValueOnce({ ...exampleReport(), status: '草稿' })
    await wrapper.get('button').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('报告暂不可批阅')
    expect(backOrRoute).not.toHaveBeenCalled()
    await wrapper.get('.med-state__action').trigger('click')
    expect(backOrRoute).toHaveBeenCalledWith('/workspace', { tab: 'reports', section: 'records' })
    expect(reviewReport).not.toHaveBeenCalled()
  })

  it('keeps state conflicts explicit without claiming a successful save', async () => {
    reviewReport.mockResolvedValueOnce(null)
    const wrapper = mount(ReportDetail)
    await flushPromises()
    await wrapper.get('input').setValue('85')
    await wrapper.get('.submit-button').trigger('click')
    await flushPromises()
    expect(wrapper.get('.submit-error').text()).toContain('状态已变化')
    expect(backOrRoute).not.toHaveBeenCalled()
  })

  it('does not imply correctness when reference lists are empty', () => {
    const wrapper = mount(ReportReference, { props: { analysis: { score: 0, summary: '', errors: [] } } })
    expect(wrapper.text()).toContain('暂无摘要')
    expect(wrapper.text()).toContain('仍需教师核对')
    expect(wrapper.find('.analysis-group').exists()).toBe(false)
  })
})
