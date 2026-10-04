import { describe, expect, it } from 'vitest'
import { studentRecordRowHeight } from './studentRecordLayout'

describe('complete student rows', () => {
  it.each([
    [580, 548],
    [420, 375],
    [300, 375],
  ])('fits an integer number of readable rows in %spx at width %s', (height, width) => {
    const row = studentRecordRowHeight(height, width)
    const count = (height - 1) / row
    expect(count).toBeCloseTo(Math.round(count))
    expect(row).toBeGreaterThanOrEqual((114 * width) / 750)
    expect(row * count).toBeLessThan(height)
  })
  it('ignores unavailable measurements and keeps one row for a short viewport', () => {
    expect(studentRecordRowHeight(0, 375)).toBe(0)
    expect(studentRecordRowHeight(NaN, 375)).toBe(0)
    expect(studentRecordRowHeight(580, 0)).toBe(0)
    expect(studentRecordRowHeight(40, 375)).toBe(39)
  })
})
