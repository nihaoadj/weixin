import { beforeEach, vi } from 'vitest'

const storage = new Map<string, unknown>()

beforeEach(() => {
  storage.clear()
  vi.stubGlobal(
    'getCurrentPages',
    vi.fn(() => []),
  )
  vi.stubGlobal('uni', {
    getStorageSync: vi.fn((key: string) => storage.get(key)),
    getStorageInfoSync: vi.fn(() => ({ keys: [...storage.keys()] })),
    setStorageSync: vi.fn((key: string, value: unknown) => storage.set(key, value)),
    removeStorageSync: vi.fn((key: string) => storage.delete(key)),
    reLaunch: vi.fn(),
    redirectTo: vi.fn(),
    navigateTo: vi.fn(),
    navigateBack: vi.fn(),
    showModal: vi.fn(),
    showToast: vi.fn(),
    request: vi.fn(),
  })
})
