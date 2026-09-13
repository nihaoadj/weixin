import { flushPromises, mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import TeacherContentWorkspace from './TeacherContentWorkspace.vue'
import TeacherInsightsWorkspace from './TeacherInsightsWorkspace.vue'
import TeacherPblQueue from './TeacherPblQueue.vue'
import { normalizeTeacherWorkspaceQuery, ownedTeacherClassId } from './teacherWorkspaceRouting'

const baseProps = {
  classes: [{ id: 1, name: '病理学演示班' }],
  classLoading: false,
  classError: '',
}

describe('teacher workspace routing compatibility', () => {
  it.each([
    ['work-items', 'problems', 'pbl-diagnostics'],
    ['diagnostics', 'problems', 'pbl-diagnostics'],
    ['follow-ups', 'reports', 'pbl-follow-ups'],
    ['results', 'reports', 'pbl-follow-ups'],
    ['classrooms', 'pbl', undefined],
    ['sessions', 'pbl', undefined],
  ])('normalizes legacy PBL section %s', (section, workspace, normalizedSection) => {
    const target = normalizeTeacherWorkspaceQuery({ tab: 'pbl', section })
    expect(target.workspace).toBe(workspace)
    expect(target.contentSection || target.insightsSection).toBe(normalizedSection)
  })

  it('keeps stable new defaults and only accepts positive follow-up filters', () => {
    expect(normalizeTeacherWorkspaceQuery({ tab: 'problems' })).toMatchObject({
      workspace: 'problems',
      contentSection: 'pbl-diagnostics',
    })
    expect(normalizeTeacherWorkspaceQuery({ tab: 'reports' })).toMatchObject({
      workspace: 'reports',
      insightsSection: 'pbl-follow-ups',
    })
    expect(
      normalizeTeacherWorkspaceQuery({
        tab: 'reports',
        section: 'pbl-follow-ups',
        sessionId: '8',
        studentId: '-1',
        planId: '3',
      }).followUpContext,
    ).toEqual({ sessionId: '8', studentId: undefined, planId: 3 })
  })

  it('keeps only owned positive class and snapshot context', () => {
    expect(
      normalizeTeacherWorkspaceQuery({
        tab: 'problems',
        section: 'pbl-diagnostics',
        classId: '12',
        snapshotId: '31',
      }),
    ).toMatchObject({ workspace: 'problems', classId: 12, snapshotId: '31' })
    expect(
      normalizeTeacherWorkspaceQuery({
        tab: 'pbl',
        section: 'diagnostics',
        classId: '0',
        snapshotId: '../31',
      }),
    ).toEqual({
      workspace: 'problems',
      classId: undefined,
      contentSection: 'pbl-diagnostics',
      snapshotId: undefined,
    })
    expect(ownedTeacherClassId(12, [{ id: 12 }, { id: 13 }])).toBe(12)
    expect(ownedTeacherClassId(99, [{ id: 12 }, { id: 13 }])).toBeUndefined()
  })
})

describe('teacher workspace responsibility containers', () => {
  it('opens content on diagnostics and keeps one active subsection', async () => {
    const wrapper = mount(TeacherContentWorkspace, {
      props: { ...baseProps, isReviewer: false },
      global: {
        stubs: {
          TeacherClassScope: true,
          TeacherPblWorkItems: { template: '<div class="diagnostics-stub" />' },
          TeacherProblemList: { template: '<div class="resources-stub" />' },
        },
      },
    })
    expect(wrapper.findAll('.record-index__item').map((button) => button.text())).toEqual(['诊断建议0', '教学资源'])
    expect(wrapper.get('[aria-current="page"]').text()).toBe('诊断建议0')
    expect(wrapper.find('.resources-stub').exists()).toBe(false)
    await wrapper.findAll('.record-index__item')[1].trigger('click')
    await flushPromises()
    expect(wrapper.get('[aria-current="page"]').text()).toBe('教学资源')
    expect(wrapper.find('.resources-stub').exists()).toBe(true)
    expect(wrapper.get('#teacher-content-panel-resources-heading').attributes('tabindex')).toBe('-1')
    await wrapper.findAll('.record-index__item')[0].trigger('click')
    expect(wrapper.find('.resources-stub').exists()).toBe(true)
    expect(wrapper.findAll('[aria-current="page"]')).toHaveLength(1)
    wrapper.unmount()
  })

  it('opens insights on PBL follow-up and preserves three distinct subsections', async () => {
    const wrapper = mount(TeacherInsightsWorkspace, {
      props: { ...baseProps, classScopeLoaded: true },
      global: {
        stubs: {
          TeacherClassScope: true,
          TeacherPblFollowUps: { template: '<div class="follow-ups-stub" />' },
          TeacherAnalyticsOverview: { template: '<div class="analytics-stub" />' },
          TeacherReportList: { template: '<div class="records-stub" />' },
        },
      },
    })
    expect(wrapper.findAll('.record-index__item').map((button) => button.text())).toEqual([
      'PBL 跟进',
      '学情总览',
      '学习记录',
    ])
    expect(wrapper.get('[aria-current="page"]').text()).toBe('PBL 跟进')
    expect(wrapper.find('.records-scope').exists()).toBe(false)
    await wrapper.findAll('.record-index__item')[1].trigger('click')
    await flushPromises()
    expect(wrapper.get('#teacher-insights-panel-analytics-heading').attributes('tabindex')).toBe('-1')
    wrapper.unmount()
  })

  it('mounts only the requested cold-start subsection for deep links', () => {
    const content = mount(TeacherContentWorkspace, {
      props: { ...baseProps, isReviewer: false, initialSection: 'resources' },
      global: {
        stubs: {
          TeacherClassScope: true,
          TeacherPblWorkItems: { template: '<div class="diagnostics-stub" />' },
          TeacherProblemList: { template: '<div class="resources-stub" />' },
        },
      },
    })
    expect(content.find('.diagnostics-stub').exists()).toBe(false)
    expect(content.find('.resources-stub').exists()).toBe(true)

    const insights = mount(TeacherInsightsWorkspace, {
      props: { ...baseProps, classScopeLoaded: true, initialSection: 'analytics' },
      global: {
        stubs: {
          TeacherClassScope: true,
          TeacherPblFollowUps: { template: '<div class="follow-ups-stub" />' },
          TeacherAnalyticsOverview: { template: '<div class="analytics-stub" />' },
          TeacherReportList: { template: '<div class="records-stub" />' },
        },
      },
    })
    expect(insights.find('.follow-ups-stub').exists()).toBe(false)
    expect(insights.find('.analytics-stub').exists()).toBe(true)
  })

  it('keeps PBL limited to classroom operations', () => {
    const wrapper = mount(TeacherPblQueue, {
      props: baseProps,
      global: {
        stubs: {
          TeacherClassScope: true,
          TeacherPblClassrooms: { template: '<div class="classrooms-stub" />' },
        },
      },
    })
    expect(wrapper.text()).toContain('创建、运行和关闭课堂')
    expect(wrapper.find('.classrooms-stub').exists()).toBe(true)
    expect(wrapper.text()).not.toContain('待处理')
    expect(wrapper.text()).not.toContain('跟进')
  })
})
