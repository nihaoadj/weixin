import { describe, expect, it } from 'vitest'
import { formatClock, formatDateTime } from './date'

describe('date utils', () => {
  it('formats clock values with leading zeroes', () => {
    expect(formatClock(new Date('2026-08-14T03:05:00'))).toBe('03:05')
  })

  it('formats ISO date time values', () => {
    expect(formatDateTime('2026-08-14T09:30:00')).toBe('2026-08-14 09:30')
  })

  it('returns invalid input unchanged', () => {
    expect(formatDateTime('not-a-date')).toBe('not-a-date')
  })
})
