import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import TeacherPblClassrooms from './TeacherPblClassrooms.vue'
import TeacherPblFollowUps from './TeacherPblFollowUps.vue'
import TeacherPblWorkItems from './TeacherPblWorkItems.vue'

const uniComponents = {
  stubs: {
    picker: { template: '<div><slot /></div>' },
    checkbox: true,
  },
}

const mocks = vi.hoisted(() => ({
  getWorkItems: vi.fn(),
  getWorkItem: vi.fn(),
  sendFeedback: vi.fn(),
  getFollowUps: vi.fn(),
  getFollowUp: vi.fn(),
  sendFollowUpFeedback: vi.fn(),
  getSessionPage: vi.fn(),
  getDashboard: vi.fn(),
  createSession: vi.fn(),
  closeSession: vi.fn(),
  getClassStudents: vi.fn(),
  getCases: vi.fn(),
  getKnowledgeCatalog: vi.fn(),
}))

vi.mock('@/features/pbl/public', () => ({
  createPblMessageId: () => 'client-message-id',
  getTeacherPblWorkItems: mocks.getWorkItems,
  getTeacherPblWorkItem: mocks.getWorkItem,
  sendTeacherPblFeedback: mocks.sendFeedback,
  getTeacherPblFollowUps: mocks.getFollowUps,
  getTeacherPblFollowUp: mocks.getFollowUp,
  sendTeacherPblFollowUpFeedback: mocks.sendFollowUpFeedback,
  getTeacherPblSessionPage: mocks.getSessionPage,
  getTeacherPblDashboard: mocks.getDashboard,
  createPblSession: mocks.createSession,
  closePblSession: mocks.closeSession,
}))
vi.mock('@/features/classroom/public', () => ({ getClassStudents: mocks.getClassStudents }))
vi.mock('@/features/content/public', () => ({ getGuidedCasesAsync: mocks.getCases }))
vi.mock('@/features/learning/public', () => ({ getKnowledgeCatalog: mocks.getKnowledgeCatalog }))

const workItem = {
  snapshotId: '7',
  sessionId: '4',
  source: 'student_submission' as const,
  status: 'pending' as const,
  student: { id: '3', name: '来源学生' },
  class: { id: '1', name: '病理班' },
  topic: '肾病理',
  knowledgeGapCount: 1,
  reasoningIssueCount: 1,
  nextAction: '审阅并反馈',
}
const diagnostic = {
  diagnosticStatus: 'ready',
  assistantReply: '请继续核对。',
  studentName: '来源学生',
  className: '病理班',
  phaseEvidenceSummary: '学生以血流与通透性变化解释红肿，但没有连接到渗出机制。',
  knowledgeGaps: [
    {
      id: 'gap-1',
      point_code: 'inflammation',
      summary: '渗出机制解释不完整',
      evidence_message_ids: ['message-1'],
      evidence_summary: '固定证据摘要',
      confidence: 'medium' as const,
    },
  ],
  reasoningIssues: [
    {
      id: 'issue-1',
      dimension_id: 'evidence',
      issue_type: 'missing_link',
      summary: '证据与结论缺少连接',
      evidence_message_ids: ['message-1'],
      evidence_summary: '固定证据摘要',
      improvement: '逐项说明证据如何支持结论',
    },
  ],
  recommendedQuestions: [
    {
      id: 'question-1',
      title: '解释局部红肿的病理基础',
      prompt: '分别说明血流与血管通透性改变造成的表现。',
      linkedFindings: ['gap-1'],
      status: 'proposed',
      version: 1,
    },
  ],
}

function workPage(name = '来源学生') {
  return {
    items: [{ ...workItem, student: { ...workItem.student, name } }],
    total: 1,
    summary: { pending: 1, responded: 0, task_published: 0, closed: 0 },
  }
}

function followUpPlan(overrides: Record<string, unknown> = {}) {
  return {
    id: 11,
    student_id: 3,
    source_type: 'pbl_suggestion',
    source_id: 9,
    source_context: {
      teacher_id: 2,
      class_id: 1,
      class_name: '病理班',
      session_id: 4,
      snapshot_id: 7,
      suggestion_id: 8,
      point_codes: ['inflammation'],
      dimension_ids: ['evidence'],
      topic_code: '炎症证据推理',
    },
    status: 'completed',
    verification_status: 'needs_reinforcement',
    verification_note: '第二轮仍有证据缺失。',
    verified_at: '2026-09-11T00:00:00Z',
    version: 2,
    due_at: '2026-09-20T00:00:00Z',
    current_cycle: 2,
    max_cycles: 2,
    automation_exhausted: true,
    decision_policy_version: 'v1',
    decision_basis: {
      result: 'needs_reinforcement',
      failed_targets: [{ target_type: 'knowledge', target_code: 'inflammation', label: '炎症机制' }],
    },
    evaluated_at: '2026-09-11T00:00:00Z',
    tasks: [
      {
        id: 15,
        position: 1,
        task_type: 'retest',
        status: 'completed',
        problem_id: 2,
        public_definition: { prompt: '说明炎症渗出的机制。', target_label: '炎症机制' },
        result: { score: 80, feedback: '', evidence: ['e1'], answer: {}, submitted_at: '2026-09-11' },
        cycle_number: 2,
        target_type: 'knowledge',
        target_code: 'inflammation',
        variant_code: 'b',
      },
    ],
    evaluations: [
      {
        cycle_number: 2,
        policy_version: 'v1',
        result: 'needs_reinforcement',
        checks: [
          {
            target_type: 'knowledge',
            target_code: 'inflammation',
            label: '炎症机制',
            threshold: 100,
            score: 80,
            evidence_present: true,
            passed: false,
          },
        ],
        failed_targets: [{ target_type: 'knowledge', target_code: 'inflammation', label: '炎症机制' }],
        automation_exhausted: true,
        record_source: 'system',
        evaluated_at: '2026-09-11',
      },
    ],
    ...overrides,
  }
}

beforeEach(() => {
  for (const mock of Object.values(mocks)) mock.mockReset()
  mocks.getWorkItems.mockResolvedValue(workPage())
  mocks.getWorkItem.mockResolvedValue({ workItem, diagnostic, feedbacks: [] })
  mocks.sendFeedback.mockResolvedValue({})
  mocks.getClassStudents.mockResolvedValue([
    { id: 3, nickname: '来源学生' },
    { id: 4, nickname: '同班学生' },
  ])
  mocks.getFollowUps.mockResolvedValue({
    items: [
      {
        planId: 11,
        studentId: 3,
        studentName: '来源学生',
        classId: 1,
        className: '病理班',
        sessionId: 4,
        sessionTopic: '炎症证据推理',
        status: 'support_needed',
        currentCycle: 2,
        verificationStatus: 'needs_reinforcement',
        automationExhausted: true,
        failedTargets: [],
      },
    ],
    total: 1,
  })
  mocks.getFollowUp.mockResolvedValue({ plan: followUpPlan(), feedbacks: [] })
  mocks.sendFollowUpFeedback.mockResolvedValue({})
  mocks.getSessionPage.mockResolvedValue({
    items: [{ id: '4', classId: '1', className: '病理班', topicCode: '炎症证据推理', status: 'active' }],
    total: 1,
  })
  mocks.getDashboard.mockResolvedValue({
    session: { id: '4', classId: '1', status: 'active' },
    summary: { participants: 3, pending_verification: 1 },
    students: [
      {
        studentId: '3',
        studentName: '只有诊断',
        currentPhase: 'completed',
        phaseStatus: 'completed',
        snapshotId: '7',
        taskProgress: { completed: 0, total: 0 },
      },
      {
        studentId: '4',
        studentName: '只有正式任务',
        currentPhase: 'completed',
        phaseStatus: 'completed',
        taskProgress: { completed: 1, total: 2 },
      },
      {
        studentId: '5',
        studentName: '尚无结果',
        currentPhase: 'evidence',
        phaseStatus: 'active',
        taskProgress: { completed: 0, total: 0 },
      },
    ],
  })
  mocks.getCases.mockResolvedValue([])
  mocks.getKnowledgeCatalog.mockResolvedValue([])
})

describe('teacher PBL diagnostics controller', () => {
  it('ignores invalid deep-link and typed IDs without issuing invalid requests', async () => {
    const wrapper = mount(TeacherPblWorkItems, { global: uniComponents })
    await flushPromises()
    await (wrapper.vm as unknown as { openSnapshot: (id: string) => Promise<void> }).openSnapshot('../7')
    expect(mocks.getWorkItem).not.toHaveBeenCalled()

    const inputs = wrapper.findAll('input')
    await inputs[0].setValue('0')
    await inputs[1].setValue('-3')
    await wrapper.get('.filter-submit').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('必须为正整数')
    expect(mocks.getWorkItems).toHaveBeenCalledTimes(1)
  })

  it('keeps the newest list result when an older request finishes last', async () => {
    let resolveFirst: (value: ReturnType<typeof workPage>) => void = () => {}
    mocks.getWorkItems
      .mockImplementationOnce(
        () =>
          new Promise((resolve) => {
            resolveFirst = resolve
          }),
      )
      .mockResolvedValueOnce(workPage('最新筛选学生'))
    const wrapper = mount(TeacherPblWorkItems, { global: uniComponents })
    await flushPromises()
    wrapper.getComponent({ name: 'TeacherPblWorkItemList' }).vm.$emit('statusChange', 'responded')
    await flushPromises()
    resolveFirst(workPage('过期学生'))
    await flushPromises()
    expect(wrapper.text()).toContain('最新筛选学生')
    expect(wrapper.text()).not.toContain('过期学生')
  })

  it('shows complete fixed evidence and removes terminal publish actions after refresh', async () => {
    mocks.getWorkItem.mockResolvedValueOnce({
      workItem: { ...workItem, status: 'task_published', nextAction: '到学情查看正式任务' },
      diagnostic,
      feedbacks: [{ id: 'f1', snapshotId: '7', actionType: 'task_published', body: '继续巩固。' }],
    })
    const wrapper = mount(TeacherPblWorkItems, { global: uniComponents })
    await flushPromises()
    await wrapper.get('.row').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('诊断证据')
    expect(wrapper.text()).toContain('渗出机制解释不完整')
    expect(wrapper.text()).toContain('证据与结论缺少连接')
    expect(wrapper.text()).toContain('分别说明血流与血管通透性改变')
    expect(wrapper.text()).toContain('该诊断已完成终态处置')
    expect(wrapper.find('.feedback-form').exists()).toBe(false)
  })

  it('preserves feedback text after a recoverable action failure', async () => {
    mocks.sendFeedback.mockRejectedValueOnce(new Error('网络暂不可用'))
    const wrapper = mount(TeacherPblWorkItems, { global: uniComponents })
    await flushPromises()
    await wrapper.get('.row').trigger('click')
    await flushPromises()
    await wrapper.get('textarea').setValue('请逐项连接证据与结论。')
    const feedbackButton = wrapper.findAll('button').find((button) => button.text() === '仅发送反馈')
    await feedbackButton?.trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('网络暂不可用')
    expect((wrapper.get('textarea').element as HTMLTextAreaElement).value).toBe('请逐项连接证据与结论。')
  })

  it('submits the teacher-edited title and prompt in the same publish action', async () => {
    const wrapper = mount(TeacherPblWorkItems, { global: uniComponents })
    await flushPromises()
    await wrapper.get('.row').trigger('click')
    await flushPromises()
    const textareas = wrapper.findAll('textarea')
    await textareas[0].setValue('请完成这项针对性巩固。')
    await wrapper.get('.suggestion-editor input').setValue('教师确认后的任务标题')
    await textareas[1].setValue('教师调整后的正式任务题干。')
    const publishButton = wrapper.findAll('button').find((button) => button.text() === '反馈并发布任务')
    await publishButton?.trigger('click')
    await flushPromises()
    expect(mocks.sendFeedback).toHaveBeenCalledWith(
      expect.objectContaining({
        actionType: 'task_published',
        suggestion: expect.objectContaining({
          id: 'question-1',
          title: '教师确认后的任务标题',
          prompt: '教师调整后的正式任务题干。',
        }),
      }),
    )
  })
})

describe('teacher PBL follow-up controller', () => {
  it('ignores invalid filter and plan context and only loads an unfiltered list', async () => {
    const wrapper = mount(TeacherPblFollowUps, { global: uniComponents })
    await flushPromises()
    await (
      wrapper.vm as unknown as {
        selectContext: (context: { sessionId?: string; studentId?: string; planId?: number }) => Promise<void>
      }
    ).selectContext({ sessionId: '0', studentId: 'student-3', planId: -1 })
    await flushPromises()
    expect(mocks.getFollowUp).not.toHaveBeenCalled()
    expect(mocks.getFollowUps).toHaveBeenLastCalledWith(
      expect.objectContaining({ sessionId: undefined, studentId: undefined }),
    )
  })

  it('shows formal tasks, current cycle, system decision and only exhausted support actions', async () => {
    const wrapper = mount(TeacherPblFollowUps, { global: uniComponents })
    await flushPromises()
    await wrapper.get('.follow-up-row').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('当前轮次：第 2 / 2 轮')
    expect(wrapper.text()).toContain('系统判定：两轮后仍需支持')
    expect(wrapper.text()).toContain('说明炎症渗出的机制')
    expect(wrapper.text()).toContain('得分 80 / 阈值 100')
    expect(wrapper.find('.support-form').exists()).toBe(true)

    mocks.getFollowUp.mockResolvedValueOnce({
      plan: followUpPlan({ automation_exhausted: false }),
      feedbacks: [],
    })
    await (wrapper.vm as unknown as { selectContext: (context: { planId: number }) => Promise<void> }).selectContext({
      planId: 11,
    })
    await flushPromises()
    expect(wrapper.find('.support-form').exists()).toBe(false)
    expect(wrapper.text()).toContain('自动巩固尚未耗尽')
  })

  it('does not let an older plan detail overwrite the newest deep-link selection', async () => {
    let resolveOld: (value: { plan: ReturnType<typeof followUpPlan>; feedbacks: never[] }) => void = () => {}
    const newestPlan = followUpPlan({
      id: 12,
      source_context: {
        ...followUpPlan().source_context,
        topic_code: '最新计划主题',
      },
    })
    mocks.getFollowUp
      .mockImplementationOnce(
        () =>
          new Promise((resolve) => {
            resolveOld = resolve
          }),
      )
      .mockResolvedValueOnce({ plan: newestPlan, feedbacks: [] })
    const wrapper = mount(TeacherPblFollowUps, { global: uniComponents })
    await flushPromises()
    const controller = wrapper.vm as unknown as {
      selectContext: (context: { planId: number }) => Promise<void>
    }
    const oldRequest = controller.selectContext({ planId: 11 })
    await flushPromises()
    await controller.selectContext({ planId: 12 })
    await flushPromises()
    resolveOld({ plan: followUpPlan(), feedbacks: [] })
    await oldRequest
    await flushPromises()
    expect(wrapper.text()).toContain('最新计划主题')
    expect(wrapper.text()).not.toContain('炎症证据推理 · 正式任务跟进')
  })
})

describe('teacher PBL classroom routing actions', () => {
  it('uses a teacher-facing topic label and local time instead of raw session codes', async () => {
    mocks.getSessionPage.mockResolvedValue({
      items: [
        {
          id: '4',
          classId: '1',
          className: '病理班',
          topicCode: 'pathology.inflammation',
          status: 'active',
          createdAt: '2026-09-12T03:10:56.041Z',
        },
      ],
      total: 1,
    })
    const wrapper = mount(TeacherPblClassrooms, {
      props: { classId: '1', classes: [{ id: 1, name: '病理班' }] },
      global: uniComponents,
    })
    await flushPromises()

    expect(wrapper.text()).toContain('病理班 · 炎症')
    expect(wrapper.text()).toContain('2026年9月12日')
    expect(wrapper.text()).not.toContain('pathology.inflammation')
    expect(wrapper.text()).not.toContain('2026-09-12T03:10:56.041Z')
  })

  it('offers diagnosis and follow-up routes only when each student has matching data', async () => {
    const wrapper = mount(TeacherPblClassrooms, {
      props: { classId: '1', classes: [{ id: 1, name: '病理班' }] },
      global: uniComponents,
    })
    await flushPromises()
    await wrapper.get('.session-row').trigger('click')
    await flushPromises()
    const students = wrapper.findAll('.student-row')
    expect(students[0].findAll('button').map((button) => button.text())).toEqual(['查看诊断'])
    expect(students[1].findAll('button').map((button) => button.text())).toEqual(['查看跟进'])
    expect(students[2].text()).toContain('等待学生形成诊断或正式任务')
    await students[0].get('button').trigger('click')
    await students[1].get('button').trigger('click')
    expect(wrapper.emitted('openDiagnostic')).toEqual([['7']])
    expect(wrapper.emitted('openFollowUp')).toEqual([[{ classId: '1', sessionId: '4', studentId: '4' }]])
  })
})
