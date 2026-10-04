export type SwipeDirection = 'left' | 'right'
type TouchPoint = { clientX?: number; clientY?: number; pageX?: number; pageY?: number }
export type HorizontalTouchEvent = { touches?: ArrayLike<TouchPoint>; changedTouches?: ArrayLike<TouchPoint> }

/** A vertical gesture stays a scroll even if the finger later moves sideways. */
export function useHorizontalSwipe(
  onSwipe: (direction: SwipeDirection) => void,
  options: { onDrag?: (delta: number) => void; onCancel?: () => void; viewportWidth?: () => number } = {},
) {
  let start:
    { x: number; y: number; time: number; moved: boolean; lastX: number; lastTime: number; speed: number } | undefined
  const point = (touch?: TouchPoint) => {
    const x = touch?.clientX ?? touch?.pageX
    const y = touch?.clientY ?? touch?.pageY
    return typeof x === 'number' && Number.isFinite(x) && typeof y === 'number' && Number.isFinite(y)
      ? { x, y }
      : undefined
  }
  function cancel() {
    const moved = start?.moved
    start = undefined
    if (moved) options.onCancel?.()
  }
  function touchstart(event: HorizontalTouchEvent) {
    cancel()
    if (event.touches?.length !== 1) return
    const first = point(event.touches[0])
    // Leave the native left-edge back gesture to WeChat.
    if (first && first.x > 20) {
      const time = Date.now()
      start = { ...first, time, moved: false, lastX: first.x, lastTime: time, speed: 0 }
    }
  }
  function touchmove(event: HorizontalTouchEvent) {
    if (event.touches?.length !== 1) return cancel()
    const current = point(event.touches[0])
    if (!start || !current) return
    const dx = Math.abs(current.x - start.x)
    const dy = Math.abs(current.y - start.y)
    if (dy > 16 && dy > dx) return cancel()
    if (dx > 8 && dx > dy * 1.25) {
      const time = Date.now()
      start.speed = (current.x - start.lastX) / Math.max(1, time - start.lastTime)
      start.lastX = current.x
      start.lastTime = time
      start.moved = true
      options.onDrag?.(current.x - start.x)
    }
  }
  function touchend(event: HorizontalTouchEvent) {
    const previous = start
    start = undefined
    const last = point(event.changedTouches?.[0])
    if (!previous || !last || event.changedTouches?.length !== 1 || event.touches?.length) {
      if (previous?.moved) options.onCancel?.()
      return
    }
    const dx = last.x - previous.x
    const dy = Math.abs(last.y - previous.y)
    const elapsed = Date.now() - previous.time
    const threshold = options.viewportWidth ? Math.max(60, options.viewportWidth() * 0.22) : 60
    const speed = previous.moved && Date.now() - previous.lastTime < 120 ? previous.speed : dx / Math.max(1, elapsed)
    const fast = Boolean(options.viewportWidth && Math.abs(dx) >= 32 && Math.abs(speed) >= 0.5 && speed * dx > 0)
    if (elapsed <= 800 && (Math.abs(dx) >= threshold || fast) && Math.abs(dx) > dy * 1.5)
      onSwipe(dx < 0 ? 'left' : 'right')
    else if (previous.moved) options.onCancel?.()
  }
  return { touchstart, touchmove, touchend, cancel }
}
