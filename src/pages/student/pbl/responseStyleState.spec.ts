import { describe, expect, it, vi } from 'vitest'
import { invalidatePendingPblMessage, resolvePendingPblMessage } from './responseStyleState'

describe('PBL response style pending message state', () => {
  it('reuses an id only while content, session, and style are unchanged', () => {
    const createId = vi.fn(() => 'next-id')
    const pending = {
      id: 'stable-id',
      content: '为什么会水肿？',
      sessionId: 'session-1',
      interactionStyle: 'guided' as const,
    }

    expect(
      resolvePendingPblMessage(
        pending,
        { content: pending.content, sessionId: pending.sessionId, interactionStyle: pending.interactionStyle },
        createId,
      ),
    ).toBe(pending)
    expect(createId).not.toHaveBeenCalled()

    expect(
      resolvePendingPblMessage(
        pending,
        { content: pending.content, sessionId: pending.sessionId, interactionStyle: 'direct' },
        createId,
      ),
    ).toEqual({ ...pending, id: 'next-id', interactionStyle: 'direct' })
    expect(createId).toHaveBeenCalledOnce()
  })

  it('drops a failed message id after switching style without changing the draft', () => {
    const pending = {
      id: 'failed-id',
      content: '保留这段草稿',
      sessionId: 'session-1',
      interactionStyle: 'guided' as const,
    }
    expect(invalidatePendingPblMessage(pending, 'guided')).toBe(pending)
    expect(invalidatePendingPblMessage(pending, 'direct')).toBeUndefined()
    expect(pending.content).toBe('保留这段草稿')
  })
})
