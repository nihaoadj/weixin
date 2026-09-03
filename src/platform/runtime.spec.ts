import { afterEach, describe, expect, it, vi } from 'vitest'
import { getApiBaseUrl, getRuntimeMode, isApiMode, isDemoMode } from './runtime'

describe('runtime configuration', () => {
  afterEach(() => vi.unstubAllEnvs())

  it('defaults to explicit demo behavior', () => {
    expect(getRuntimeMode()).toBe('demo')
    expect(isDemoMode()).toBe(true)
    expect(isApiMode()).toBe(false)
  })

  it('requires a base URL in api mode', () => {
    vi.stubEnv('VITE_APP_MODE', 'api')
    expect(() => getApiBaseUrl()).toThrow('VITE_API_BASE_URL')
  })

  it('normalizes the api base URL', () => {
    vi.stubEnv('VITE_APP_MODE', 'api')
    vi.stubEnv('VITE_API_BASE_URL', 'https://api.example.com/')
    expect(getApiBaseUrl()).toBe('https://api.example.com')
  })

  it('rejects unknown modes', () => {
    vi.stubEnv('VITE_APP_MODE', 'offline')
    expect(() => getRuntimeMode()).toThrow('不支持')
  })
})
