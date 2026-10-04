import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import TeacherPblClassrooms from './TeacherPblClassrooms.vue'

const uniComponents = {
  stubs: {
    picker: { template: '<div><slot /></div>' },
    checkbox: true,
    'radio-group': {
      name: 'RadioGroupStub',
      emits: ['change'],
      template: '<div><slot /></div>',
    },
    radio: {
      name: 'RadioStub',
      props: ['checked', 'value'],
      template: '<span />',
    },
  },
}

const mocks = vi.hoisted(() => ({
  getSessionPage: vi.fn(),
  getDashboard: vi.fn(),
  createSession: vi.fn(),
  closeSession: vi.fn(),
  getCases: vi.fn(),
  getKnowledgeCatalog: vi.fn(),
  goDetail: vi.fn(),
}))

vi.mock('@/platform/navigation', () => ({
  ROUTES: {
    teacherPblDiagnosticDetail: '/teacher/pbl-diagnostic-detail',
  },
  goDetail: mocks.goDetail,
}))

vi.mock('@/features/pbl/public', () => ({
  getTeacherPblSessionPage: mocks.getSessionPage,
  getTeacherPblDashboard: mocks.getDashboard,
  createPblSession: mocks.createSession,
  closePblSession: mocks.closeSession,
}))
vi.mock('@/features/content/public', () => ({ getGuidedCasesAsync: mocks.getCases }))
vi.mock('@/features/learning/public', () => ({ getKnowledgeCatalog: mocks.getKnowledgeCatalog }))

beforeEach(() => {
  for (const mock of Object.values(mocks)) mock.mockReset()
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

describe('teacher PBL classroom routing actions', () => {
  it('marks all four stages completed while keeping active discussion stages distinct', async () => {
    const wrapper = mount(TeacherPblClassrooms, {
      props: { classId: '1', classes: [{ id: 1, name: '病理班' }] },
      global: uniComponents,
    })
    await flushPromises()
    await wrapper.get('.session-row').trigger('click')
    await flushPromises()
    const students = wrapper.findAll('.student-row')
    expect(students[0].findAll('.phase-step--done')).toHaveLength(4)
    expect(students[0].findAll('.phase-step--current')).toHaveLength(0)
    expect(students[2].findAll('.phase-step--done')).toHaveLength(2)
    expect(students[2].get('.phase-step--current').text()).toContain('搜集证据')
    expect(wrapper.text()).not.toContain('0/0 项任务')
  })
  it('allows saved cases regardless of historical review state', async () => {
    mocks.getCases.mockResolvedValue([
      {
        id: 'draft',
        title: '审核通过但未发布',
        status: '待审核',
        medicalReviewStatus: 'approved',
        knowledgePointCodes: ['goal-a'],
      },
      {
        id: 'unapproved',
        title: '尚未医学审核',
        status: '已发布',
        medicalReviewStatus: 'pending',
        knowledgePointCodes: ['goal-a'],
      },
    ])
    mocks.getKnowledgeCatalog.mockResolvedValue([{ code: 'goal-a', title: '目标一' }])
    const wrapper = mount(TeacherPblClassrooms, {
      props: { classId: '1', classes: [{ id: 1, name: '病理班' }], createOnly: true },
      global: uniComponents,
    })
    await flushPromises()
    await wrapper.get('.topic-input').setValue('课堂主题')
    expect(wrapper.findAllComponents({ name: 'RadioStub' })).toHaveLength(1)
    expect(wrapper.get('.create-submit').attributes('disabled')).toBeDefined()
    expect(mocks.createSession).not.toHaveBeenCalled()
  })

  it('keeps an archived selected class visible while preventing classroom creation', async () => {
    mocks.getCases.mockResolvedValue([
      {
        id: 'case-1',
        title: '正式病例',
        status: '已发布',
        medicalReviewStatus: 'approved',
        knowledgePointCodes: ['goal-a'],
      },
    ])
    mocks.getKnowledgeCatalog.mockResolvedValue([{ code: 'goal-a', title: '目标一' }])
    const wrapper = mount(TeacherPblClassrooms, {
      props: {
        classId: '2',
        classes: [
          { id: 1, name: '活动班', status: 'active' },
          { id: 2, name: '归档班', status: 'archived' },
        ],
        createOnly: true,
      },
      global: uniComponents,
    })
    await flushPromises()
    await wrapper.get('.topic-input').setValue('课堂主题')
    wrapper.findComponent({ name: 'RadioGroupStub' }).vm.$emit('change', { detail: { value: 'goal-a' } })
    await flushPromises()
    expect(wrapper.get('.form-picker__value').text()).toBe('归档班')
    expect(wrapper.text()).toContain('不能创建新课堂')
    expect(wrapper.get('.create-submit').attributes('disabled')).toBeDefined()
    expect(mocks.createSession).not.toHaveBeenCalled()
    await wrapper.setProps({ createOnly: false })
    await wrapper.get('.session-row').trigger('click')
    await flushPromises()
    expect(wrapper.find('.dashboard').exists()).toBe(true)
    expect(wrapper.find('.close-session').exists()).toBe(false)
    expect(mocks.closeSession).not.toHaveBeenCalled()
  })

  it('does not restore an old classroom dashboard after the class filter changes', async () => {
    let resolveOld!: (value: unknown) => void
    mocks.getDashboard.mockReturnValueOnce(
      new Promise((resolve) => {
        resolveOld = resolve
      }),
    )
    const wrapper = mount(TeacherPblClassrooms, {
      props: {
        classId: '1',
        classes: [
          { id: 1, name: '病理班' },
          { id: 2, name: '新班' },
        ],
      },
      global: uniComponents,
    })
    await flushPromises()
    await wrapper.get('.session-row').trigger('click')
    await wrapper.setProps({ classId: '2' })
    resolveOld({ session: { id: '4', classId: '1', status: 'active' }, summary: { participants: 0 }, students: [] })
    await flushPromises()
    expect(wrapper.find('.dashboard').exists()).toBe(false)
  })

  it('creates a classroom with exactly the one selected knowledge goal', async () => {
    mocks.getCases.mockResolvedValue([
      {
        id: 'case-1',
        title: '已审核病例',
        status: '已发布',
        medicalReviewStatus: 'approved',
        knowledgePointCodes: ['goal-a', 'goal-b'],
      },
    ])
    mocks.getKnowledgeCatalog.mockResolvedValue([
      { code: 'goal-a', title: '目标一' },
      { code: 'goal-b', title: '目标二' },
    ])
    mocks.createSession.mockResolvedValue({ id: 'session-1', topicCode: '肾病变证据推理', status: 'active' })
    mocks.getDashboard.mockResolvedValue({
      session: { id: 'session-1', classId: '1', status: 'active' },
      summary: { participants: 0 },
      students: [],
    })

    const wrapper = mount(TeacherPblClassrooms, {
      props: { classId: '1', classes: [{ id: 1, name: '病理班' }], createOnly: true },
      global: uniComponents,
    })
    await flushPromises()
    await wrapper.get('.topic-input').setValue('肾病变证据推理')

    const group = wrapper.findComponent({ name: 'RadioGroupStub' })
    group.vm.$emit('change', { detail: { value: 'goal-a' } })
    group.vm.$emit('change', { detail: { value: 'goal-b' } })
    group.vm.$emit('change', { detail: { value: 'goal-b' } })
    await flushPromises()

    expect(wrapper.findAllComponents({ name: 'RadioStub' }).map((radio) => radio.props('checked'))).toEqual([
      false,
      true,
    ])
    await wrapper.get('.create-submit').trigger('click')
    await flushPromises()

    expect(mocks.createSession).toHaveBeenCalledWith('1', '肾病变证据推理', 'case-1', ['goal-b'])
    expect(wrapper.emitted('created')).toEqual([['session-1']])
  })

  it('opens an explicitly linked session even when it is not on the first list page', async () => {
    mocks.getSessionPage.mockResolvedValue({ items: [], total: 0 })
    const wrapper = mount(TeacherPblClassrooms, {
      props: { classId: '1', sessionId: '4', classes: [{ id: 1, name: '病理班' }] },
      global: uniComponents,
    })
    await flushPromises()
    expect(mocks.getDashboard).toHaveBeenCalledWith('1', '4')
    expect(wrapper.find('.dashboard').exists()).toBe(true)
    expect(wrapper.emitted('sessionChange')).toEqual([['4']])
  })

  it('does not reopen a classroom after closing completes under a different class filter', async () => {
    let resolveClose!: () => void
    mocks.closeSession.mockReturnValueOnce(
      new Promise<void>((resolve) => {
        resolveClose = resolve
      }),
    )
    const wrapper = mount(TeacherPblClassrooms, {
      props: {
        classId: '1',
        classes: [
          { id: 1, name: '旧班' },
          { id: 2, name: '新班' },
        ],
      },
      global: uniComponents,
    })
    await flushPromises()
    await wrapper.get('.session-row').trigger('click')
    await flushPromises()
    await wrapper.get('.close-session').trigger('click')
    await wrapper.setProps({ classId: '2' })
    resolveClose()
    await flushPromises()
    expect(mocks.closeSession).toHaveBeenCalledWith('1', '4')
    expect(mocks.getDashboard).toHaveBeenCalledTimes(1)
    expect(wrapper.find('.dashboard').exists()).toBe(false)
  })

  it('does not replace the new class draft with a late classroom creation response', async () => {
    mocks.getCases.mockResolvedValue([
      {
        id: 'case-1',
        title: '已发布病例',
        status: '已发布',
        medicalReviewStatus: 'approved',
        knowledgePointCodes: ['goal-a'],
      },
    ])
    mocks.getKnowledgeCatalog.mockResolvedValue([{ code: 'goal-a', title: '目标一' }])
    let resolveCreate!: (value: unknown) => void
    mocks.createSession.mockReturnValueOnce(
      new Promise((resolve) => {
        resolveCreate = resolve
      }),
    )
    const wrapper = mount(TeacherPblClassrooms, {
      props: {
        classId: '1',
        classes: [
          { id: 1, name: '旧班' },
          { id: 2, name: '新班' },
        ],
        createOnly: true,
      },
      global: uniComponents,
    })
    await flushPromises()
    await wrapper.get('.topic-input').setValue('旧班主题')
    wrapper.findComponent({ name: 'RadioGroupStub' }).vm.$emit('change', { detail: { value: 'goal-a' } })
    await flushPromises()
    await wrapper.get('.create-submit').trigger('click')
    await wrapper.setProps({ classId: '2' })
    await wrapper.get('.topic-input').setValue('新班主题')
    resolveCreate({ id: 'late-session', topicCode: '旧班主题', status: 'active' })
    await flushPromises()
    expect(wrapper.get('.topic-input').element).toHaveProperty('value', '新班主题')
    expect(mocks.getDashboard).not.toHaveBeenCalled()
    expect(wrapper.emitted('created')).toBeUndefined()
    expect(wrapper.find('.create-form').exists()).toBe(true)
  })

  it('renders only the inline creation form when opened from the reference homepage', async () => {
    const wrapper = mount(TeacherPblClassrooms, {
      props: { classId: '1', classes: [{ id: 1, name: '病理班' }], createOnly: true },
      global: uniComponents,
    })
    await flushPromises()

    expect(wrapper.find('.create-form').exists()).toBe(true)
    expect(wrapper.find('.toolbar').exists()).toBe(false)
    expect(wrapper.find('.session-list').exists()).toBe(false)
    expect(wrapper.find('.dashboard').exists()).toBe(false)
  })

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

  it('offers diagnosis, test review and submitted result actions only when matching data exists', async () => {
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
          studentName: '只有课堂测试',
          currentPhase: 'completed',
          phaseStatus: 'completed',
          learningRouteId: '11111111-1111-4111-8111-111111111111',
          finalTestId: '22222222-2222-4222-8222-222222222222',
          taskProgress: { completed: 1, total: 2 },
        },
        {
          studentId: '5',
          studentName: '已有结果',
          currentPhase: 'completed',
          phaseStatus: 'completed',
          learningRouteId: '33333333-3333-4333-8333-333333333333',
          finalTestId: '44444444-4444-4444-8444-444444444444',
          resultId: '55555555-5555-4555-8555-555555555555',
          taskProgress: { completed: 2, total: 2 },
          score: 66.7,
        },
      ],
    })
    const wrapper = mount(TeacherPblClassrooms, {
      props: { classId: '1', classes: [{ id: 1, name: '病理班' }] },
      global: uniComponents,
    })
    await flushPromises()
    await wrapper.get('.session-row').trigger('click')
    await flushPromises()
    const students = wrapper.findAll('.student-row')
    expect(students[0].findAll('button').map((button) => button.text())).toEqual(['查看固定诊断'])
    expect(students[1].findAll('button').map((button) => button.text())).toEqual(['查看最终测试'])
    expect(students[2].findAll('button').map((button) => button.text())).toEqual(['查看最终测试'])
    await students[0].get('button').trigger('click')
    await students[1].get('button').trigger('click')
    await wrapper.get('.classroom-insights').trigger('click')
    expect(wrapper.emitted('openDiagnostic')).toEqual([['7']])
    expect(wrapper.emitted('openFinalTest')).toEqual([['22222222-2222-4222-8222-222222222222']])
    expect(wrapper.emitted('openInsights')).toEqual([[{ classId: '1', sessionId: '4' }]])
  })
})
