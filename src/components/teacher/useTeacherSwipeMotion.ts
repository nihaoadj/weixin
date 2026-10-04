import { computed, onUnmounted, ref } from 'vue'
import type { SwipeDirection } from './useHorizontalSwipe'

export type TeacherSwipeProgress = { direction: SwipeDirection; progress: number } | undefined

export function useTeacherSwipeMotion(options: {
  width: () => number
  canSwipe: (direction: SwipeDirection) => boolean
  commit: (direction: SwipeDirection) => void
  progress?: (value: TeacherSwipeProgress) => void
  reducedMotion?: boolean
}) {
  const offset = ref(0)
  const phase = ref<'idle' | 'dragging' | 'returning' | 'leaving' | 'waiting' | 'entering'>('idle')
  const direction = ref<SwipeDirection>()
  const progress = computed(() => Math.min(1, Math.abs(offset.value) / options.width()))
  const busy = computed(() => ['returning', 'leaving', 'waiting', 'entering'].includes(phase.value))
  const duration = computed(() =>
    options.reducedMotion ? 0 : phase.value === 'dragging' ? 36 : phase.value === 'leaving' ? 180 : 240,
  )
  const style = computed(() => ({
    transform: phase.value === 'idle' ? 'none' : `translate3d(${offset.value}px, 0, 0)`,
    transition: `transform ${duration.value}ms ${phase.value === 'dragging' ? 'linear' : 'cubic-bezier(0.22, 1, 0.36, 1)'}`,
  }))
  const timers = new Set<ReturnType<typeof setTimeout>>()
  let disposed = false
  let revision = 0
  function later(callback: () => void, delay: number) {
    const scheduledRevision = revision
    const timer = setTimeout(() => {
      timers.delete(timer)
      if (!disposed && scheduledRevision === revision) callback()
    }, delay)
    timers.add(timer)
  }
  function clearTimers() {
    revision += 1
    for (const timer of timers) clearTimeout(timer)
    timers.clear()
  }
  function idle() {
    phase.value = 'idle'
    direction.value = undefined
    options.progress?.(undefined)
  }
  function cancel() {
    clearTimers()
    phase.value = 'returning'
    offset.value = 0
    options.progress?.(undefined)
    later(idle, options.reducedMotion ? 0 : 240)
  }
  function reset() {
    clearTimers()
    offset.value = 0
    idle()
  }
  function drag(delta: number) {
    if (busy.value) return
    clearTimers()
    phase.value = 'dragging'
    direction.value = delta < 0 ? 'left' : 'right'
    const allowed = options.canSwipe(direction.value)
    offset.value = allowed
      ? Math.max(-options.width(), Math.min(options.width(), delta))
      : Math.sign(delta) * Math.min(48, Math.abs(delta) * 0.2)
    options.progress?.(allowed ? { direction: direction.value, progress: progress.value } : undefined)
  }
  function release(next: SwipeDirection) {
    if (busy.value) return
    if (!options.canSwipe(next)) return cancel()
    clearTimers()
    direction.value = next
    phase.value = 'leaving'
    offset.value = (next === 'left' ? -1 : 1) * options.width()
    options.progress?.({ direction: next, progress: 1 })
    later(
      () => {
        phase.value = 'waiting'
        // The same-frame panel handoff may call enter and replace this recovery timer.
        later(cancel, 700)
        try {
          options.commit(next)
        } catch {
          cancel()
        }
      },
      options.reducedMotion ? 0 : 180,
    )
  }
  function enter(next: SwipeDirection) {
    clearTimers()
    const entryRevision = revision
    direction.value = next
    phase.value = 'entering'
    offset.value = options.reducedMotion ? 0 : (next === 'left' ? 1 : -1) * options.width()
    // Disable transitions for the offscreen placement, then animate after it renders.
    return () => {
      if (disposed || entryRevision !== revision) return
      later(
        () => {
          offset.value = 0
          options.progress?.(undefined)
          later(idle, options.reducedMotion ? 0 : 240)
        },
        options.reducedMotion ? 0 : 32,
      )
    }
  }
  const renderedStyle = computed(() =>
    phase.value === 'entering' && offset.value !== 0 ? { ...style.value, transition: 'none' } : style.value,
  )
  onUnmounted(() => {
    disposed = true
    clearTimers()
  })
  return { offset, phase, direction, progress, busy, style: renderedStyle, drag, release, cancel, reset, enter }
}
