import { mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'

import App from '@/App.vue'

const ensureDemoData = vi.hoisted(() => vi.fn())
const recordStartupLog = vi.hoisted(() => vi.fn())

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
})
