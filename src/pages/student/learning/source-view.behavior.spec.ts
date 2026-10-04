import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import SourceView from './source-view.vue'

const hooks = vi.hoisted(() => ({
  load: undefined as undefined | ((options?: Record<string, string>) => void),
  show: undefined as undefined | (() => void),
}))
const getKnowledgeMap = vi.hoisted(() => vi.fn())

vi.mock('@dcloudio/uni-app', () => ({
  onLoad: (hook: (options?: Record<string, string>) => void) => {
    hooks.load = hook
  },
  onShow: (hook: () => void) => {
    hooks.show = hook
  },
  onBackPress: vi.fn(),
}))
vi.mock('@/features/learning/public', () => ({ getKnowledgeMap }))
vi.mock('@/features/identity/public', () => ({ requireRole: () => true }))
vi.mock('@/platform/navigation', () => ({
  backOrRoute: vi.fn(),
  handleBackPress: vi.fn(),
  ROUTES: { studentKnowledgeNode: '/pages/student/learning/knowledge-node' },
}))

describe('source view page', () => {
  const mountPage = () => mount(SourceView, { global: { stubs: { 'web-view': true } } })

  beforeEach(() => {
    vi.clearAllMocks()
    vi.unstubAllGlobals()
    hooks.load = undefined
    hooks.show = undefined
  })

  it('resolves the source from the catalog identity and opens its HTTPS URL', async () => {
    getKnowledgeMap.mockResolvedValue([
      {
        code: 'pathology.cell-injury.adaptation',
        sources: [
          {
            sourceKey: 'S01',
            title: 'Cellular Injury and Adaptation',
            url: 'https://pmc.ncbi.nlm.nih.gov/articles/PMC7171462/',
          },
        ],
      },
    ])
    const wrapper = mountPage()

    hooks.load?.({ pointCode: 'pathology.cell-injury.adaptation', sourceKey: 'S01' })
    hooks.show?.()
    await flushPromises()

    expect(wrapper.get('web-view-stub').attributes('src')).toBe('https://pmc.ncbi.nlm.nih.gov/articles/PMC7171462/')
  })

  it('rejects a catalog source that is not HTTPS', async () => {
    getKnowledgeMap.mockResolvedValue([
      {
        code: 'pathology.cell-injury.adaptation',
        sources: [{ sourceKey: 'S01', title: 'Unsafe', url: 'javascript:alert(1)' }],
      },
    ])
    const wrapper = mountPage()

    hooks.load?.({ pointCode: 'pathology.cell-injury.adaptation', sourceKey: 'S01' })
    hooks.show?.()
    await flushPromises()

    expect(wrapper.find('web-view-stub').exists()).toBe(false)
    expect(wrapper.text()).toContain('链接暂时无法安全打开')
  })

  it('copies the persisted URL only when WeChat rejects the web-view domain', async () => {
    getKnowledgeMap.mockResolvedValue([
      {
        code: 'pathology.cell-injury.adaptation',
        sources: [
          {
            sourceKey: 'S01',
            title: 'Cellular Injury and Adaptation',
            url: 'https://pmc.ncbi.nlm.nih.gov/articles/PMC7171462/',
          },
        ],
      },
    ])
    const setClipboardData = vi.fn(({ success }) => success())
    vi.stubGlobal('uni', { setClipboardData })
    const wrapper = mountPage()

    hooks.load?.({ pointCode: 'pathology.cell-injury.adaptation', sourceKey: 'S01' })
    hooks.show?.()
    await flushPromises()
    await wrapper.get('web-view-stub').trigger('error')
    await flushPromises()

    expect(setClipboardData).toHaveBeenCalledWith(
      expect.objectContaining({ data: 'https://pmc.ncbi.nlm.nih.gov/articles/PMC7171462/' }),
    )
    expect(wrapper.find('web-view-stub').exists()).toBe(false)
    expect(wrapper.text()).toContain('链接已复制')
  })
})
