import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import { describe, expect, it, vi } from 'vitest'
import TeacherWorkspaceNav from './TeacherWorkspaceNav.vue'
import TeacherOverview from './TeacherOverview.vue'
import TeacherPblWorkItems from './TeacherPblWorkItems.vue'

vi.mock('@/features/pbl/public', () => ({
  createPblMessageId: () => 'feedback-id',
  getTeacherPblWorkItems: vi.fn(async () => ({
    items: [
      {
        snapshotId: '7',
        sessionId: '4',
        source: 'student_submission',
        status: 'pending',
        student: { id: '3', name: '来源学生' },
        class: { id: '1', name: '病理班' },
        topic: '肾病理',
        knowledgeGapCount: 1,
        reasoningIssueCount: 1,
        nextAction: '审阅并反馈',
      },
    ],
    total: 1,
    summary: { pending: 1, responded: 0, task_published: 0, closed: 0 },
  })),
  getTeacherPblWorkItem: vi.fn(async () => ({
    workItem: undefined,
    diagnostic: {
      studentName: '来源学生',
      className: '病理班',
      phaseEvidenceSummary: '学生证据',
      knowledgeGaps: [],
      reasoningIssues: [],
      recommendedQuestions: [],
    },
    feedbacks: [],
  })),
  sendTeacherPblFeedback: vi.fn(),
}))
vi.mock('@/features/classroom/public', () => ({
  getClassStudents: vi.fn(async () => [
    { id: 3, nickname: '来源学生' },
    { id: 4, nickname: '同班学生' },
  ]),
}))

describe('teacher workspace navigation', () => {
  it('exposes four intent-based destinations and only one current page', async () => {
    const wrapper = mount(TeacherWorkspaceNav, {
      props: { active: 'reports' },
      global: { stubs: { MedIcon: true } },
    })
    expect(wrapper.attributes('aria-label')).toBe('教师主导航')
    expect(wrapper.findAll('button').map((button) => button.text())).toEqual(['待办', '学情', '内容', 'PBL'])
    expect(wrapper.findAll('[aria-current="page"]')).toHaveLength(1)
    expect(wrapper.get('[aria-current="page"]').text()).toBe('学情')
    await wrapper.findAll('button')[2].trigger('click')
    expect(wrapper.emitted('change')).toEqual([['problems']])
  })

  it('supports Enter and Space without relying on a tab widget', async () => {
    const wrapper = mount(TeacherWorkspaceNav, {
      props: { active: 'reports' },
      global: { stubs: { MedIcon: true } },
    })
    await wrapper.findAll('button')[0].trigger('keydown', { key: 'Enter' })
    await wrapper.findAll('button')[2].trigger('keydown', { key: ' ' })
    expect(wrapper.emitted('change')).toEqual([['overview'], ['problems']])
    expect(wrapper.find('[role="tab"]').exists()).toBe(false)
  })
})

describe('teacher overview', () => {
  const props = { loading: false, isReviewer: false, reportError: false, reviewError: false, pblError: false }

  it('distinguishes an empty queue from a failed queue', async () => {
    const wrapper = mount(TeacherOverview, { props: { ...props, pendingReports: 0 } })
    expect(wrapper.text()).toContain('暂无待批阅报告')
    expect(wrapper.find('[role="alert"]').exists()).toBe(false)
    await wrapper.setProps({ pendingReports: undefined, reportError: true })
    expect(wrapper.get('[role="alert"]').text()).toContain('不代表没有待处理内容')
    expect(wrapper.text()).not.toContain('暂无待批阅报告')
    await wrapper.get('.priority-row').trigger('click')
    expect(wrapper.emitted('retry')).toEqual([[]])
    expect(wrapper.emitted('reports')).toBeUndefined()
  })

  it('keeps review entry permission-based and management actions distinct', async () => {
    const wrapper = mount(TeacherOverview, { props })
    expect(wrapper.findAll('.priority-row')).toHaveLength(2)
    await wrapper.setProps({ isReviewer: true, pendingReview: 2 })
    expect(wrapper.findAll('.priority-row')).toHaveLength(3)
    await wrapper.findAll('.priority-row')[1].trigger('click')
    await wrapper.findAll('.priority-row')[2].trigger('click')
    await wrapper.findAll('.management-row')[0].trigger('click')
    await wrapper.findAll('.management-row')[1].trigger('click')
    expect(wrapper.emitted('review')).toEqual([[]])
    expect(wrapper.emitted('pbl')).toEqual([[]])
    expect(wrapper.emitted('classes')).toEqual([[]])
    expect(wrapper.emitted('analytics')).toEqual([[]])
  })
})

describe('teacher PBL work items', () => {
  it('loads publish recipients by name from the selected item class', async () => {
    const wrapper = mount(TeacherPblWorkItems, {
      global: { stubs: { picker: { template: '<div><slot /></div>' }, checkbox: true } },
    })
    await Promise.resolve()
    await nextTick()
    await wrapper.get('.row').trigger('click')
    await Promise.resolve()
    await nextTick()
    expect(wrapper.text()).toContain('来源学生')
    expect(wrapper.text()).toContain('同班学生')
    expect(wrapper.text()).not.toContain('指定学生 ID')
  })
})
