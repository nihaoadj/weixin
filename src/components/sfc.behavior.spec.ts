import { mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'

import App from '@/App.vue'
import TeacherReportList from '@/components/TeacherReportList.vue'

const getReportSummariesAsync = vi.hoisted(() => vi.fn())
const ensureDemoData = vi.hoisted(() => vi.fn())
const recordStartupLog = vi.hoisted(() => vi.fn())

vi.mock('@/features/reports/public', () => ({ getReportSummariesAsync }))
vi.mock('@/features/qa/public', () => ({ ensureDemoData }))
vi.mock('@/platform/logs', () => ({ recordStartupLog }))
vi.mock('@dcloudio/uni-app', () => ({ onLaunch: (hook: () => void) => hook() }))

describe('SFC business entry behavior', () => {
  it('runs the application launch contract through the existing uni lifecycle', () => {
    mount(App)
    const launch = vi.mocked(ensureDemoData)
    expect(launch).toHaveBeenCalledTimes(1)
    expect(recordStartupLog).toHaveBeenCalledTimes(1)
  })

  it('loads report summaries, exposes retry and emits stable counts', async () => {
    getReportSummariesAsync.mockResolvedValueOnce({
      items: [
        {
          id: 'report-1',
          studentName: '学生甲',
          status: '待批阅',
          originalIndex: 0,
          messagePreview: '摘要',
          createdAt: '2026-08-31T00:00:00Z',
          messageCount: 1,
        },
      ],
      total: 1,
      pendingCount: 1,
      reviewedCount: 0,
    })
    const wrapper = mount(TeacherReportList)
    await wrapper.vm.$nextTick()
    await (wrapper.vm as unknown as { refresh: () => Promise<void> }).refresh()
    expect(wrapper.text()).toContain('学生甲')
    expect(wrapper.emitted('count')?.at(-1)).toEqual([1])
    expect(wrapper.emitted('reviewed')?.at(-1)).toEqual([0])
  })

  it('turns report loading failures into the visible retry state', async () => {
    getReportSummariesAsync.mockRejectedValueOnce(new Error('请求失败'))
    const wrapper = mount(TeacherReportList)
    await (wrapper.vm as unknown as { refresh: () => Promise<void> }).refresh()
    expect(wrapper.text()).toContain('报告加载失败')
    expect(wrapper.text()).toContain('请求失败')
  })
})
