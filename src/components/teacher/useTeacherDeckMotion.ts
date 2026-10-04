import { computed, onUnmounted, ref } from 'vue'
import { useHorizontalSwipe, type SwipeDirection } from './useHorizontalSwipe'

/** The real target is already next to the current pane; commit only changes its index. */
export function useTeacherDeckMotion(options: {
  current: () => number
  width: () => number
  allowed: (index: number) => boolean
  commit: (index: number) => void
}) {
  const offset = ref(0)
  const phase = ref<'idle' | 'dragging' | 'settling'>('idle')
  const instant = ref(false)
  let timer: ReturnType<typeof setTimeout> | undefined
  let disposed = false
  function clear() {
    if (timer) clearTimeout(timer)
    timer = undefined
  }
  function settle(target: number) {
    if (phase.value === 'settling') return
    clear()
    instant.value = false
    const next = options.allowed(target) ? target : options.current()
    phase.value = 'settling'
    offset.value = (options.current() - next) * options.width()
    timer = setTimeout(() => {
      if (disposed) return
      instant.value = true
      if (next !== options.current()) options.commit(next)
      offset.value = 0
      phase.value = 'idle'
      timer = setTimeout(() => {
        instant.value = false
      }, 32)
    }, 240)
  }
  function drag(delta: number) {
    if (phase.value === 'settling') return
    clear()
    instant.value = false
    phase.value = 'dragging'
    const next = options.current() + (delta < 0 ? 1 : -1)
    // Keep the current content still if its real neighbour is not ready.
    offset.value = options.allowed(next) ? Math.max(-options.width(), Math.min(options.width(), delta)) : 0
  }
  function release(direction: SwipeDirection) {
    settle(options.current() + (direction === 'left' ? 1 : -1))
  }
  const swipe = useHorizontalSwipe(release, {
    onDrag: drag,
    onCancel: () => settle(options.current()),
    viewportWidth: options.width,
  })
  function reset() {
    clear()
    swipe.cancel()
    clear()
    instant.value = true
    offset.value = 0
    phase.value = 'idle'
  }
  function paneStyle(index: number) {
    const position = (index - options.current()) * options.width() + offset.value
    return {
      transform: phase.value === 'idle' && index === options.current() ? 'none' : `translate3d(${position}px,0,0)`,
      transition:
        instant.value || phase.value === 'idle'
          ? 'none'
          : `transform ${phase.value === 'dragging' ? 36 : 240}ms ${phase.value === 'dragging' ? 'linear' : 'cubic-bezier(.22,1,.36,1)'}`,
    }
  }
  const position = computed(() => options.current() - offset.value / options.width())
  onUnmounted(() => {
    disposed = true
    clear()
  })
  return {
    offset,
    phase,
    position,
    paneStyle,
    drag,
    release,
    cancel: () => settle(options.current()),
    settle,
    reset,
    swipe,
  }
}
