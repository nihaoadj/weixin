import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { clearTeacherSwipeEntry, prepareTeacherSwipeEntry, takeTeacherSwipeEntry } from './teacherSwipeMotion'

describe('teacher swipe entry handoff', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-10-03T00:00:00Z'))
    clearTeacherSwipeEntry()
  })

  afterEach(() => {
    clearTeacherSwipeEntry()
    vi.useRealTimers()
  })

  it('returns a matching entry direction once and consumes it', () => {
    prepareTeacherSwipeEntry('insights', 'left')

    expect(takeTeacherSwipeEntry('insights')).toBe('left')
    expect(takeTeacherSwipeEntry('insights')).toBeUndefined()
  })

  it('consumes entries that target a different workspace', () => {
    prepareTeacherSwipeEntry('content', 'right')

    expect(takeTeacherSwipeEntry('pbl')).toBeUndefined()
    expect(takeTeacherSwipeEntry('content')).toBeUndefined()
  })

  it('accepts entries through the 1200ms lifetime and rejects expired entries', () => {
    prepareTeacherSwipeEntry('pbl', 'right')
    vi.advanceTimersByTime(1200)
    expect(takeTeacherSwipeEntry('pbl')).toBe('right')

    prepareTeacherSwipeEntry('content', 'left')
    vi.advanceTimersByTime(1201)
    expect(takeTeacherSwipeEntry('content')).toBeUndefined()
  })

  it('clears an entry explicitly', () => {
    prepareTeacherSwipeEntry('insights', 'left')
    clearTeacherSwipeEntry()

    expect(takeTeacherSwipeEntry('insights')).toBeUndefined()
  })
})
