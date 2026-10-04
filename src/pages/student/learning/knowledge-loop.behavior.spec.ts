import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import KnowledgeLoop from './knowledge-loop.vue'

const api = vi.hoisted(() => ({
  load: undefined as undefined | ((options?: Record<string, string>) => void),
  allowed: true,
  session: { role: 'student', openid: 'student-a' },
  getKnowledgeCatalog: vi.fn(),
  getReviewDashboard: vi.fn(),
  getKnowledgeCardContributions: vi.fn(),
  createExitQuiz: vi.fn(),
  getDueReviewQueue: vi.fn(),
  gradeObjectiveCard: vi.fn(),
  revealRecallCard: vi.fn(),
  rateRecallCard: vi.fn(),
  goPrimary: vi.fn(),
  goReplace: vi.fn(),
}))

vi.mock('@dcloudio/uni-app', () => ({
  onLoad: (hook: (options?: Record<string, string>) => void) => {
    api.load = hook
  },
}))
vi.mock('@/features/identity/public', () => ({
  requireRole: () => api.allowed,
  getSession: () => api.session,
}))
vi.mock('@/features/learning/public', () => ({
  getKnowledgeCatalog: api.getKnowledgeCatalog,
  createExitQuiz: api.createExitQuiz,
  getDueReviewQueue: api.getDueReviewQueue,
  getReviewDashboard: api.getReviewDashboard,
  gradeObjectiveCard: api.gradeObjectiveCard,
  rateRecallCard: api.rateRecallCard,
  revealRecallCard: api.revealRecallCard,
}))
vi.mock('@/features/content/public', () => ({ getKnowledgeCardContributions: api.getKnowledgeCardContributions }))
vi.mock('@/platform/navigation', () => ({
  goPrimary: api.goPrimary,
  goReplace: api.goReplace,
  ROUTES: { studentKnowledgeNode: '/knowledge-node', studentLearning: '/learning' },
}))

const loadPage = async (options: Record<string, string> = {}) => {
  const wrapper = mount(KnowledgeLoop)
  api.load?.(options)
  await flushPromises()
  return wrapper
}
const expectNoRetiredReadsOrWrites = () => {
  for (const operation of [
    api.getReviewDashboard,
    api.getKnowledgeCardContributions,
    api.createExitQuiz,
    api.getDueReviewQueue,
    api.gradeObjectiveCard,
    api.revealRecallCard,
    api.rateRecallCard,
  ]) {
    expect(operation).not.toHaveBeenCalled()
  }
}

describe('T63 retired knowledge loop compatibility', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.load = undefined
    api.allowed = true
    api.session = { role: 'student', openid: 'student-a' }
    api.getKnowledgeCatalog.mockResolvedValue([{ code: 'cell' }, { code: 'inflammation' }])
  })

  it.each<[Record<string, string>, string]>([
    [{ topicCode: 'cell' }, 'cell'],
    [{ topicCodes: 'unknown, inflammation,cell' }, 'inflammation'],
    [{ topicCode: 'cell', topicCodes: 'inflammation' }, 'cell'],
  ])('replaces a supported old topic URL with its current knowledge node: %j', async (options, code) => {
    const wrapper = await loadPage(options)
    expect(api.goReplace).toHaveBeenCalledWith('/knowledge-node', { topicCode: code })
    expect(api.goPrimary).not.toHaveBeenCalled()
    expectNoRetiredReadsOrWrites()
    expect(wrapper.findAll('button')).toHaveLength(0)
    wrapper.unmount()
  })

  it.each<Record<string, string>>([
    {},
    { topicCode: 'unknown' },
    { topicCodes: 'unknown,invalid' },
    { topicCode: ' ' },
  ])('returns absent or unsupported topic URLs to learning: %j', async (options) => {
    const wrapper = await loadPage(options)
    expect(api.goPrimary).toHaveBeenCalledWith('/learning')
    expect(api.goReplace).not.toHaveBeenCalled()
    expectNoRetiredReadsOrWrites()
    wrapper.unmount()
  })

  it('does not load a catalog when no topic was requested', async () => {
    const wrapper = await loadPage()
    expect(api.getKnowledgeCatalog).not.toHaveBeenCalled()
    wrapper.unmount()
  })

  it('checks student access before reading or navigating', async () => {
    api.allowed = false
    const wrapper = await loadPage({ topicCode: 'cell' })
    expect(api.getKnowledgeCatalog).not.toHaveBeenCalled()
    expect(api.goPrimary).not.toHaveBeenCalled()
    expect(api.goReplace).not.toHaveBeenCalled()
    expectNoRetiredReadsOrWrites()
    wrapper.unmount()
  })

  it('returns catalog failures to learning without starting an old quiz', async () => {
    api.getKnowledgeCatalog.mockRejectedValue(new Error('目录暂不可用'))
    const wrapper = await loadPage({ topicCode: 'cell' })
    expect(uni.showToast).toHaveBeenCalledWith({ title: '目录暂不可用', icon: 'none' })
    expect(api.goPrimary).toHaveBeenCalledWith('/learning')
    expectNoRetiredReadsOrWrites()
    wrapper.unmount()
  })

  it('discards a pending navigation when the student identity changes', async () => {
    let resolveCatalog!: (value: { code: string }[]) => void
    api.getKnowledgeCatalog.mockReturnValue(
      new Promise((resolve) => {
        resolveCatalog = resolve
      }),
    )
    const wrapper = mount(KnowledgeLoop)
    api.load?.({ topicCode: 'cell' })
    api.session = { role: 'student', openid: 'student-b' }
    resolveCatalog([{ code: 'cell' }])
    await flushPromises()
    expect(api.goReplace).not.toHaveBeenCalled()
    expect(api.goPrimary).not.toHaveBeenCalled()
    wrapper.unmount()
  })
})
