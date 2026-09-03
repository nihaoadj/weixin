import './validationRuntime'
import { describe, expect, it, vi } from 'vitest'
import { z } from 'zod'
import { apiLoginResponseSchema } from './auth'
import { sessionSchema } from '@/platform/storage/storage'

describe('sandbox-safe validation runtime', () => {
  it('validates nested contracts without dynamic Function construction', () => {
    const dynamicFunction = vi.spyOn(globalThis, 'Function').mockImplementation(() => {
      throw new Error('Dynamic code generation is unavailable in this sandbox')
    })
    let calls: number
    let valid: boolean
    let invalid: boolean
    try {
      const schema = z.object({ entries: z.array(z.object({ title: z.string().min(1), score: z.number().int() })) })
      valid = schema.safeParse({ entries: [{ title: '病例反馈', score: 80 }] }).success
      invalid = schema.safeParse({ entries: [{ title: '', score: '80' }] }).success
      calls = dynamicFunction.mock.calls.length
    } finally {
      dynamicFunction.mockRestore()
    }
    expect(calls).toBe(0)
    expect(valid).toBe(true)
    expect(invalid).toBe(false)
  })

  it('preserves session and API validation constraints', () => {
    expect(z.config().jitless).toBe(true)
    expect(sessionSchema.safeParse({ openid: 'demo', role: 'admin' }).success).toBe(false)
    expect(
      apiLoginResponseSchema.safeParse({
        access_token: '',
        user: { id: 1, role: 'student', nickname: '测试学生', created_at: '2026-08-31' },
      }).success,
    ).toBe(false)
    expect(
      apiLoginResponseSchema.safeParse({
        access_token: 'test-only-token',
        user: { id: 1, role: 'student', nickname: '测试学生', created_at: '2026-08-31' },
      }).success,
    ).toBe(true)
  })
})
