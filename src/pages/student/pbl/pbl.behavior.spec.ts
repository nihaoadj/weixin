import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import Page from './pbl.vue'

const hooks = vi.hoisted(() => ({
  show: undefined as undefined | (() => void),
  load: undefined as undefined | ((query?: Record<string, unknown>) => void),
}))
const api = vi.hoisted(() => ({
  list: vi.fn(),
  catalog: vi.fn(),
  create: vi.fn(),
  send: vi.fn(),
  get: vi.fn(),
  submission: vi.fn(),
  messageId: vi.fn(() => 'stable-client-id'),
  primary: vi.fn(),
  detail: vi.fn(),
}))

vi.mock('@dcloudio/uni-app', () => ({
  onShow: (hook: () => void) => {
    hooks.show = hook
  },
  onLoad: (hook: (query?: Record<string, unknown>) => void) => {
    hooks.load = hook
  },
  onBackPress: vi.fn(),
}))
vi.mock('@/features/pbl/public', () => ({
  createLearningDialogue: api.create,
  createPblMessageId: api.messageId,
  getLearningDialogue: api.get,
  getLearningDialogueSubmission: api.submission,
  getLearningDialogues: api.list,
  sendPblMessage: api.send,
}))
vi.mock('@/features/learning/public', () => ({ getKnowledgeCatalog: api.catalog }))
vi.mock('@/platform/navigation', () => ({
  goDetail: api.detail,
  goPrimary: api.primary,
  handleBackPress: vi.fn(),
  ROUTES: {
    studentPbl: '/pbl',
    studentLearning: '/learning',
    studentLearningPlans: '/learning/plans',
    studentLearningPlanDetail: '/learning/plan-detail',
  },
}))

const points = [
  {
    code: 'pathology.inflammation.vascular',
    title: '血管反应',
    systemCode: 'pathology.inflammation',
    systemLabel: '炎症',
  },
]
const created = {
  session: {
    id: 'session-1',
    topicCode: 'pathology.inflammation',
    status: 'active',
    createdAt: '2026-09-26T00:00:00Z',
    sessionKind: 'student_initiated',
    phase: 'problem_framing',
  },
  participation: {
    messages: [],
    currentPhase: 'problem_framing',
    phaseStatus: 'active',
    interactionStyle: 'guided',
    evidenceLocked: false,
    conversationMode: 'evidence',
  },
}
const mountPage = () =>
  mount(Page, {
    global: {
      stubs: {
        'scroll-view': { template: '<div><slot /></div>' },
        selection: { template: '<span><slot /></span>' },
        MedState: {
          props: ['title', 'description', 'actionLabel'],
          emits: ['action'],
          template:
            '<view class="med-state"><text>{{ title }}</text><text>{{ description }}</text><button class="med-state-action" @click="$emit(\'action\')">{{ actionLabel }}</button></view>',
        },
        picker: {
          props: ['range', 'value'],
          emits: ['change'],
          template: '<view class="picker-stub" @click="$emit(\'change\', { detail: { value: 1 } })"><slot /></view>',
        },
        StudentPrimaryNav: true,
        PblConversationBoundary: true,
        ChatComposer: {
          props: ['modelValue', 'sendLabel', 'sendAriaLabel', 'error'],
          emits: ['update:modelValue', 'send'],
          template:
            '<view class="composer-stub"><slot name="quote"/><textarea class="composer-draft" :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)"/><text class="send-error">{{ error }}</text><slot name="context"/><button class="composer-send" @click="$emit(\'send\')">{{ sendLabel }}</button></view>',
        },
        PblResponseStylePicker: {
          props: ['modelValue'],
          emits: ['update:modelValue', 'change'],
          template:
            "<button class=\"style-stub\" @click=\"$emit('update:modelValue', 'direct'); $emit('change', 'direct')\">切换直接讲解</button>",
        },
      },
    },
  })

beforeEach(() => {
  vi.clearAllMocks()
  hooks.show = undefined
  hooks.load = undefined
  api.list.mockResolvedValue({ items: [] })
  api.catalog.mockResolvedValue(points)
  api.create.mockReset()
  api.send.mockReset()
  api.get.mockReset()
  api.submission.mockReset()
  api.messageId.mockReturnValue('stable-client-id')
})

describe('student PBL page classroom and private-learning boundaries', () => {
  it('restores an entry link starter and point as a private dialogue draft', async () => {
    api.create.mockResolvedValue(created)
    const wrapper = mountPage()
    hooks.load?.({ starter: '我想继续理解炎症。', topicCode: points[0].code })
    hooks.show?.()
    await flushPromises()

    expect(wrapper.text()).toContain('从旧答疑带来的起始问题')
    expect(wrapper.get('.choice-chip').attributes('aria-pressed')).toBe('true')
    await wrapper.get('.primary-action').trigger('click')
    await flushPromises()

    expect(api.create).toHaveBeenCalledWith(expect.objectContaining({ goalPointCodes: [points[0].code] }))
    expect((wrapper.find('textarea.composer-draft').element as HTMLTextAreaElement).value).toBe('我想继续理解炎症。')
  })

  it('shows a recoverable load error and retries the dialogue list', async () => {
    api.list.mockRejectedValueOnce(new Error('temporary')).mockResolvedValueOnce({ items: [] })
    const wrapper = mountPage()
    hooks.show?.()
    await flushPromises()

    expect(wrapper.text()).toContain('研讨加载失败，请检查网络后重新加载。')
    await wrapper.get('.med-state-action').trigger('click')
    await flushPromises()

    expect(api.list).toHaveBeenCalledTimes(2)
    expect(wrapper.text()).toContain('开始一次病理研讨')
  })

  it('keeps an unavailable requested dialogue explicit instead of opening another session', async () => {
    const wrapper = mountPage()
    hooks.load?.({ dialogueId: 'missing-session' })
    hooks.show?.()
    await flushPromises()

    expect(wrapper.text()).toContain('指定研讨记录暂不可用，请返回学习页后重试。')
    expect(api.get).not.toHaveBeenCalled()
    expect(api.create).not.toHaveBeenCalled()
  })

  it('starts with private self-study, requires a selected point, and preserves the create key on retry', async () => {
    const wrapper = mountPage()
    hooks.show?.()
    await flushPromises()

    expect(wrapper.text()).toContain('自主研讨默认私有')
    expect(wrapper.get('.primary-action').attributes('disabled')).toBeDefined()
    await wrapper.get('.choice-chip').trigger('click')
    expect(wrapper.get('.primary-action').attributes('disabled')).toBeUndefined()

    api.create.mockRejectedValueOnce(new Error('首次创建未确认')).mockResolvedValueOnce(created)
    await wrapper.get('.primary-action').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('创建未确认，设置已保留')
    await wrapper.get('.primary-action').trigger('click')
    await flushPromises()

    expect(api.create).toHaveBeenCalledTimes(2)
    expect(api.create.mock.calls[0][0]).toEqual(api.create.mock.calls[1][0])
    expect(api.create.mock.calls[1][0]).toMatchObject({
      clientSessionId: 'stable-client-id',
      interactionStyle: 'guided',
      goalPointCodes: ['pathology.inflammation.vascular'],
    })
    expect(api.create.mock.calls[1][0]).not.toHaveProperty('classId')
    expect(wrapper.text()).toContain('主动研讨')
  })

  it('preserves a student message and retries it with the same identity and selected response style', async () => {
    api.list.mockResolvedValue({ items: [created.session] })
    api.get.mockResolvedValue({ ...created, session: created.session })
    api.send.mockRejectedValueOnce(new Error('发送暂未确认')).mockResolvedValueOnce({
      ...created.participation,
      messages: [],
      currentPhase: 'problem_framing',
      interactionStyle: 'direct',
    })
    const wrapper = mountPage()
    hooks.show?.()
    await flushPromises()
    await wrapper.find('textarea.composer-draft').setValue('  我的疑问是血管通透性如何变化？  ')
    await wrapper.get('.style-stub').trigger('click')
    await wrapper.get('.composer-send').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('内容已保留')
    expect((wrapper.find('textarea.composer-draft').element as HTMLTextAreaElement).value).toBe(
      '  我的疑问是血管通透性如何变化？  ',
    )
    await wrapper.get('.composer-send').trigger('click')
    await flushPromises()

    expect(api.send).toHaveBeenCalledTimes(2)
    expect(api.send.mock.calls[0]).toEqual(api.send.mock.calls[1])
    expect(api.send.mock.calls[1]).toEqual([
      'session-1',
      '我的疑问是血管通透性如何变化？',
      'stable-client-id',
      'direct',
    ])
    expect((wrapper.find('textarea.composer-draft').element as HTMLTextAreaElement).value).toBe('')
  })

  it('keeps post-completion questions private and does not create another classroom diagnosis', async () => {
    const completedSession = { ...created.session, status: 'closed', sessionKind: 'classroom' }
    const completedParticipation = {
      ...created.participation,
      currentPhase: 'completed',
      phaseStatus: 'completed',
      evidenceLocked: true,
      conversationMode: 'private_follow_up',
      completionSnapshotId: 'snapshot-1',
      evidenceCompletedRevision: 2,
      messages: [{ id: 'evidence-1', sequence: 1, role: 'student', content: '课堂证据', turnScope: 'evidence' }],
    }
    api.list.mockResolvedValue({ items: [completedSession] })
    api.get.mockResolvedValue({ session: completedSession, participation: completedParticipation })
    api.send.mockResolvedValue({
      ...completedParticipation,
      messages: [
        ...completedParticipation.messages,
        { id: 'private-1', sequence: 2, role: 'student', content: '补充问题', turnScope: 'private_follow_up' },
      ],
      interactionStyle: 'guided',
    })
    const wrapper = mountPage()
    hooks.show?.()
    await flushPromises()

    expect(wrapper.text()).toContain('证据已完成 · 私人续问')
    expect(wrapper.text()).toContain('仅自己可见 · 不计入诊断')
    await wrapper.find('textarea.composer-draft').setValue('课后补充问题')
    await wrapper.get('.composer-send').trigger('click')
    await flushPromises()

    expect(api.send).toHaveBeenCalledWith('session-1', '课后补充问题', 'stable-client-id', 'guided')
    expect(api.create).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('仅自己可见 · 不计入诊断')
  })

  it('opens the generated T44 route from a completed classroom discussion', async () => {
    const completedSession = { ...created.session, status: 'closed', sessionKind: 'classroom' }
    const completedParticipation = {
      ...created.participation,
      currentPhase: 'completed',
      phaseStatus: 'completed',
      evidenceLocked: true,
      conversationMode: 'evidence',
      completionSnapshotId: 'snapshot-1',
      evidenceCompletedRevision: 2,
      learningRouteId: 'b06f66a2-8a15-4935-ae19-5821efeb84e3',
      messages: [{ id: 'evidence-1', sequence: 1, role: 'student', content: '课堂证据', turnScope: 'evidence' }],
    }
    api.list.mockResolvedValue({ items: [completedSession] })
    api.get.mockResolvedValue({ session: completedSession, participation: completedParticipation })
    const wrapper = mountPage()
    hooks.show?.()
    await flushPromises()

    expect(wrapper.text()).toContain('查看研讨学习计划')
    await wrapper.get('.completion-actions .text-action').trigger('click')

    expect(api.detail).toHaveBeenCalledWith('/learning/plan-detail', {
      routeId: 'b06f66a2-8a15-4935-ae19-5821efeb84e3',
    })
    expect(api.submission).not.toHaveBeenCalled()
  })

  it('returns from the new-dialogue form and switches between existing conversations', async () => {
    const firstSession = { ...created.session, sessionKind: 'classroom' }
    const secondSession = { ...created.session, id: 'session-2', topicCode: 'pathology.neoplasia' }
    api.list.mockResolvedValue({ items: [firstSession, secondSession] })
    api.get.mockImplementation(async (id: string) => ({
      session: id === 'session-2' ? secondSession : firstSession,
      participation: created.participation,
    }))
    const wrapper = mountPage()
    hooks.show?.()
    await flushPromises()

    await wrapper.get('.new-action').trigger('click')
    expect(wrapper.text()).toContain('开始一次病理研讨')
    await wrapper.get('.launch-heading .text-action').trigger('click')
    await flushPromises()
    expect(api.get).toHaveBeenLastCalledWith('session-1')
    expect(wrapper.text()).toContain('课堂研讨')

    await wrapper.get('.session-picker').trigger('click')
    await flushPromises()
    expect(api.get).toHaveBeenLastCalledWith('session-2')
    expect(wrapper.text()).toContain('主动研讨')

    await wrapper.get('.example-card').trigger('click')
    expect((wrapper.find('textarea.composer-draft').element as HTMLTextAreaElement).value).toBe(
      '我的疑问是：\n我目前的理解或判断依据是：',
    )
  })
})
