import { defineComponent, h, ref } from 'vue'
import { mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useTeacherDeckMotion } from './useTeacherDeckMotion'
import type { SwipeDirection } from './useHorizontalSwipe'

const wrappers: Array<ReturnType<typeof mount>> = []

function mountMotion(start: number, ready: number[] = [0, 1, 2, 3, 4]) {
  const current = ref(start)
  const commits: number[] = []
  let motion!: ReturnType<typeof useTeacherDeckMotion>
  const wrapper = mount(
    defineComponent({
      setup() {
        motion = useTeacherDeckMotion({
          current: () => current.value,
          width: () => 400,
          allowed: (index) => ready.includes(index),
          commit: (index) => {
            commits.push(index)
            current.value = index
          },
        })
        return () => h('div')
      },
    }),
  )
  wrappers.push(wrapper)
  return { current, commits, motion, wrapper }
}

beforeEach(() => vi.useFakeTimers())
afterEach(() => {
  for (const wrapper of wrappers.splice(0)) wrapper.unmount()
  vi.clearAllTimers()
  vi.useRealTimers()
})

describe('teacher deck motion', () => {
  it('moves adjacent real panes together and commits the index after the settle animation', async () => {
    const { current, commits, motion } = mountMotion(1)

    motion.drag(-150)
    expect(motion.paneStyle(1).transform).toBe('translate3d(-150px,0,0)')
    expect(motion.paneStyle(2).transform).toBe('translate3d(250px,0,0)')
    expect(motion.phase.value).toBe('dragging')

    motion.release('left')
    expect(motion.phase.value).toBe('settling')
    expect(motion.paneStyle(1).transform).toBe('translate3d(-400px,0,0)')
    expect(motion.paneStyle(2).transform).toBe('translate3d(0px,0,0)')
    expect(current.value).toBe(1)
    expect(commits).toEqual([])

    await vi.advanceTimersByTimeAsync(239)
    expect(commits).toEqual([])
    await vi.advanceTimersByTimeAsync(1)
    expect(commits).toEqual([2])
    expect(current.value).toBe(2)
    expect(motion.paneStyle(2).transform).toBe('none')
  })

  it('keeps an unready neighbor in place and returns to the current pane on a cancelled drag', async () => {
    const { current, commits, motion } = mountMotion(1, [1])

    motion.drag(-180)
    expect(motion.offset.value).toBe(0)
    expect(motion.paneStyle(1).transform).toBe('translate3d(0px,0,0)')
    expect(motion.paneStyle(2).transform).toBe('translate3d(400px,0,0)')

    motion.cancel()
    expect(motion.phase.value).toBe('settling')
    await vi.advanceTimersByTimeAsync(240)
    expect(current.value).toBe(1)
    expect(commits).toEqual([])
    expect(motion.phase.value).toBe('idle')
  })

  it.each([
    [0, 'right', -1],
    [4, 'left', 5],
  ] as Array<[number, SwipeDirection, number]>)(
    'does not cross the %s workspace boundary',
    async (start, direction, target) => {
      const { current, commits, motion } = mountMotion(start)
      motion.release(direction)
      expect(motion.phase.value).toBe('settling')
      expect(motion.offset.value).toBe(0)
      await vi.advanceTimersByTimeAsync(240)
      expect(current.value).toBe(start)
      expect(commits).toEqual([])
      expect(commits).not.toContain(target)
    },
  )

  it('ignores new gestures while settling and cancels a pending commit on reset or unmount', async () => {
    const first = mountMotion(1)
    first.motion.release('left')
    first.motion.drag(120)
    first.motion.release('right')
    expect(first.motion.phase.value).toBe('settling')
    expect(first.current.value).toBe(1)
    expect(first.commits).toEqual([])
    first.motion.reset()
    await vi.advanceTimersByTimeAsync(240)
    expect(first.commits).toEqual([])

    const second = mountMotion(2)
    second.motion.release('left')
    second.wrapper.unmount()
    await vi.advanceTimersByTimeAsync(240)
    expect(second.commits).toEqual([])
  })
})
