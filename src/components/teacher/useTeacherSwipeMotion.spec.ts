import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h, nextTick } from 'vue'
import { mount } from '@vue/test-utils'
import { useTeacherSwipeMotion, type TeacherSwipeProgress } from './useTeacherSwipeMotion'
import type { SwipeDirection } from './useHorizontalSwipe'

const wrappers: Array<ReturnType<typeof mount>> = []

const MotionHarness = defineComponent({
  props: {
    width: { type: Number, default: 375 },
    allowed: { type: Boolean, default: true },
    reducedMotion: { type: Boolean, default: false },
    onCommit: { type: Function, required: true },
    onProgress: { type: Function, required: false },
  },
  setup(props, { expose }) {
    const motion = useTeacherSwipeMotion({
      width: () => props.width,
      canSwipe: () => props.allowed,
      commit: (direction) => (props.onCommit as (value: SwipeDirection) => void)(direction),
      progress: props.onProgress as ((value: TeacherSwipeProgress) => void) | undefined,
      reducedMotion: props.reducedMotion,
    })
    expose({ motion })
    return () => h('div', { class: 'motion-body', 'data-phase': motion.phase.value, style: motion.style.value })
  },
})

function mountMotion(options: { width?: number; allowed?: boolean; reducedMotion?: boolean } = {}) {
  const commit = vi.fn<(direction: SwipeDirection) => void>()
  const progress = vi.fn<(value: TeacherSwipeProgress) => void>()
  const wrapper = mount(MotionHarness, { props: { ...options, onCommit: commit, onProgress: progress } })
  wrappers.push(wrapper)
  const motion = (wrapper.vm as unknown as { motion: ReturnType<typeof useTeacherSwipeMotion> }).motion
  return { wrapper, motion, commit, progress }
}

beforeEach(() => {
  vi.useFakeTimers()
  vi.setSystemTime(new Date('2026-10-03T00:00:00Z'))
})

afterEach(() => {
  for (const wrapper of wrappers.splice(0)) wrapper.unmount()
  vi.clearAllTimers()
  vi.useRealTimers()
})

describe('useTeacherSwipeMotion', () => {
  it('tracks drag with a short transition and returns to idle after cancel', async () => {
    const { wrapper, motion, commit } = mountMotion()
    motion.drag(-90)
    await nextTick()
    expect(motion.phase.value).toBe('dragging')
    expect((wrapper.get('.motion-body').element as HTMLElement).style.transform).toBe('translate3d(-90px, 0, 0)')
    expect((wrapper.get('.motion-body').element as HTMLElement).style.transition).toContain('36ms linear')

    motion.cancel()
    await nextTick()
    expect(motion.phase.value).toBe('returning')
    expect(motion.busy.value).toBe(true)
    expect((wrapper.get('.motion-body').element as HTMLElement).style.transition).toContain('240ms')
    motion.drag(120)
    expect(motion.offset.value).toBe(0)
    await vi.advanceTimersByTimeAsync(239)
    expect(motion.phase.value).toBe('returning')
    await vi.advanceTimersByTimeAsync(1)
    expect(motion.phase.value).toBe('idle')
    expect(motion.busy.value).toBe(false)
    expect(commit).not.toHaveBeenCalled()
  })

  it('waits 180ms before committing once and recovers if navigation does not finish', async () => {
    const { motion, commit } = mountMotion()
    motion.release('left')
    expect(motion.phase.value).toBe('leaving')
    expect(motion.busy.value).toBe(true)
    await vi.advanceTimersByTimeAsync(179)
    expect(commit).not.toHaveBeenCalled()
    await vi.advanceTimersByTimeAsync(1)
    expect(motion.phase.value).toBe('waiting')
    expect(commit).toHaveBeenCalledExactlyOnceWith('left')

    await vi.advanceTimersByTimeAsync(700)
    expect(motion.phase.value).toBe('returning')
    expect(motion.busy.value).toBe(true)
    await vi.advanceTimersByTimeAsync(240)
    expect(motion.phase.value).toBe('idle')
    expect(commit).toHaveBeenCalledTimes(1)
  })

  it('places an incoming body offscreen, waits for render, then enters over 240ms', async () => {
    const { wrapper, motion } = mountMotion()
    const afterRender = motion.enter('left')
    await nextTick()

    const body = wrapper.get('.motion-body').element as HTMLElement
    expect(motion.phase.value).toBe('entering')
    expect(body.style.transform).toBe('translate3d(375px, 0, 0)')
    expect(body.style.transition).toBe('none')

    afterRender()
    await vi.advanceTimersByTimeAsync(31)
    expect((wrapper.get('.motion-body').element as HTMLElement).style.transform).toBe('translate3d(375px, 0, 0)')
    await vi.advanceTimersByTimeAsync(1)
    expect(motion.offset.value).toBe(0)
    expect((wrapper.get('.motion-body').element as HTMLElement).style.transition).toContain('240ms')
    await vi.advanceTimersByTimeAsync(240)
    expect(motion.phase.value).toBe('idle')
    expect((wrapper.get('.motion-body').element as HTMLElement).style.transform).toBe('none')
  })

  it('ignores an entry render callback made stale by reset and a later drag', async () => {
    const { motion, progress } = mountMotion()
    const afterRender = motion.enter('left')
    motion.reset()
    motion.drag(-40)
    const progressCalls = progress.mock.calls.length
    afterRender()

    await vi.advanceTimersByTimeAsync(32)
    expect(motion.phase.value).toBe('dragging')
    expect(motion.offset.value).toBe(-40)
    expect(progress).toHaveBeenCalledTimes(progressCalls)
  })

  it('clears a pending release timer when the component unmounts', async () => {
    const { wrapper, motion, commit } = mountMotion()
    motion.release('right')
    wrapper.unmount()
    await vi.advanceTimersByTimeAsync(1000)

    expect(commit).not.toHaveBeenCalled()
    expect(vi.getTimerCount()).toBe(0)
  })
})
