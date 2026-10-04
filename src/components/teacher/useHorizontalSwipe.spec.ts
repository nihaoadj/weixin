import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useHorizontalSwipe } from './useHorizontalSwipe'

const point = (clientX: number, clientY = 100) => ({ clientX, clientY })

describe('useHorizontalSwipe', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-10-03T00:00:00Z'))
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it.each([
    { direction: 'left', endX: 40 },
    { direction: 'right', endX: 160 },
  ] as const)('recognizes a $direction swipe at the 60px threshold', ({ direction, endX }) => {
    const onSwipe = vi.fn()
    const swipe = useHorizontalSwipe(onSwipe)
    swipe.touchstart({ touches: [point(100)] })
    swipe.touchend({ touches: [], changedTouches: [point(endX)] })

    expect(onSwipe).toHaveBeenCalledExactlyOnceWith(direction)
  })

  it('ignores a movement below the threshold and a diagonal without horizontal dominance', () => {
    const onSwipe = vi.fn()
    const swipe = useHorizontalSwipe(onSwipe)

    swipe.touchstart({ touches: [point(100)] })
    swipe.touchend({ touches: [], changedTouches: [point(41)] })
    swipe.touchstart({ touches: [point(100)] })
    swipe.touchend({ touches: [], changedTouches: [point(161, 141)] })

    expect(onSwipe).not.toHaveBeenCalled()
  })

  it('uses 22 percent of the viewport for slow swipes and accepts a fast 32px swipe', () => {
    const onSwipe = vi.fn()
    const swipe = useHorizontalSwipe(onSwipe, { viewportWidth: () => 400 })

    swipe.touchstart({ touches: [point(120)] })
    vi.advanceTimersByTime(200)
    swipe.touchmove({ touches: [point(30)] })
    swipe.touchend({ touches: [], changedTouches: [point(30)] })

    swipe.touchstart({ touches: [point(120)] })
    vi.advanceTimersByTime(40)
    swipe.touchmove({ touches: [point(160)] })
    vi.advanceTimersByTime(10)
    swipe.touchend({ touches: [], changedTouches: [point(160)] })

    expect(onSwipe.mock.calls).toEqual([['left'], ['right']])
  })

  it('reports drag offsets and cancels a slow short drag', () => {
    const onSwipe = vi.fn()
    const onDrag = vi.fn()
    const onCancel = vi.fn()
    const swipe = useHorizontalSwipe(onSwipe, { onDrag, onCancel, viewportWidth: () => 400 })

    swipe.touchstart({ touches: [point(100)] })
    vi.advanceTimersByTime(50)
    swipe.touchmove({ touches: [point(130)] })
    vi.advanceTimersByTime(50)
    swipe.touchmove({ touches: [point(140)] })
    swipe.touchend({ touches: [], changedTouches: [point(140)] })

    expect(onDrag.mock.calls).toEqual([[30], [40]])
    expect(onCancel).toHaveBeenCalledExactlyOnceWith()
    expect(onSwipe).not.toHaveBeenCalled()
  })

  it('locks a vertical scroll even when the finger later moves horizontally', () => {
    const onSwipe = vi.fn()
    const swipe = useHorizontalSwipe(onSwipe)
    swipe.touchstart({ touches: [point(100)] })
    swipe.touchmove({ touches: [point(116, 117)] })
    swipe.touchend({ touches: [], changedTouches: [point(30, 118)] })

    expect(onSwipe).not.toHaveBeenCalled()
  })

  it('cancels a horizontal drag when it turns vertical', () => {
    const onSwipe = vi.fn()
    const onDrag = vi.fn()
    const onCancel = vi.fn()
    const swipe = useHorizontalSwipe(onSwipe, { onDrag, onCancel })
    swipe.touchstart({ touches: [point(100, 100)] })
    swipe.touchmove({ touches: [point(125, 110)] })
    swipe.touchmove({ touches: [point(126, 150)] })
    swipe.touchend({ touches: [], changedTouches: [point(220, 150)] })

    expect(onDrag).toHaveBeenCalledExactlyOnceWith(25)
    expect(onCancel).toHaveBeenCalledExactlyOnceWith()
    expect(onSwipe).not.toHaveBeenCalled()
  })

  it('ignores non-finite touch coordinates', () => {
    const onSwipe = vi.fn()
    const onDrag = vi.fn()
    const onCancel = vi.fn()
    const swipe = useHorizontalSwipe(onSwipe, { onDrag, onCancel })

    swipe.touchstart({ touches: [point(Number.NaN)] })
    swipe.touchend({ touches: [], changedTouches: [point(0)] })
    swipe.touchstart({ touches: [point(100)] })
    swipe.touchmove({ touches: [point(Number.POSITIVE_INFINITY)] })
    swipe.touchend({ touches: [], changedTouches: [point(Number.POSITIVE_INFINITY)] })

    expect(onSwipe).not.toHaveBeenCalled()
    expect(onDrag).not.toHaveBeenCalled()
    expect(onCancel).not.toHaveBeenCalled()
  })

  it('cancels multi-touch gestures and explicit touch cancellation', () => {
    const onSwipe = vi.fn()
    const swipe = useHorizontalSwipe(onSwipe)

    swipe.touchstart({ touches: [point(100)] })
    swipe.touchmove({ touches: [point(90), point(200)] })
    swipe.touchend({ touches: [], changedTouches: [point(20)] })
    swipe.touchstart({ touches: [point(100)] })
    swipe.cancel()
    swipe.touchend({ touches: [], changedTouches: [point(20)] })
    swipe.touchstart({ touches: [point(100), point(200)] })
    swipe.touchend({ touches: [], changedTouches: [point(20)] })

    expect(onSwipe).not.toHaveBeenCalled()
  })

  it('ignores a long press and leaves the left-edge gesture to the platform', () => {
    const onSwipe = vi.fn()
    const swipe = useHorizontalSwipe(onSwipe)

    swipe.touchstart({ touches: [point(100)] })
    vi.advanceTimersByTime(801)
    swipe.touchend({ touches: [], changedTouches: [point(20)] })
    swipe.touchstart({ touches: [point(20)] })
    swipe.touchend({ touches: [], changedTouches: [point(100)] })

    expect(onSwipe).not.toHaveBeenCalled()
  })
})
