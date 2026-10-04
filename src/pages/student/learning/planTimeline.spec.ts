import { describe, expect, it } from 'vitest'
import type { LearningRouteDetail, LearningRouteStep } from '@/features/learning/public'
import { planProgress, planTimeline } from './planTimeline'

function detail(steps: LearningRouteStep[], options: { canStartTest?: boolean; resultId?: string } = {}) {
  return {
    steps,
    canStartTest: options.canStartTest ?? false,
    summary: { resultId: options.resultId, status: options.resultId ? 'completed' : 'learning' },
  } as LearningRouteDetail
}

describe('learning plan timeline', () => {
  it('keeps any number of resources in route order and appends the test once', () => {
    const steps = [
      { id: 'case', position: 4, kind: 'case', title: '病例', status: 'locked' },
      { id: 'reading-2', position: 3, kind: 'reading', title: '资料二', status: 'available' },
      { id: 'reading-1', position: 1, kind: 'reading', title: '资料一', status: 'completed' },
      { id: 'reading-3', position: 2, kind: 'reading', title: '资料三', status: 'completed' },
    ] as LearningRouteStep[]
    const items = planTimeline(detail(steps))
    expect(items.map((item) => (item.kind === 'test' ? 'test' : item.step.id))).toEqual([
      'reading-1',
      'reading-3',
      'reading-2',
      'case',
      'test',
    ])
    expect(items.map((item) => item.number)).toEqual([1, 2, 3, 4, 5])
    expect(planProgress(items)).toEqual({ completed: 2, total: 5 })
  })

  it('counts a submitted test and does not invent progress before route generation', () => {
    const steps = [
      { id: 'reading', position: 1, kind: 'reading', title: '资料', status: 'completed' },
    ] as LearningRouteStep[]
    expect(planProgress(planTimeline(detail(steps, { resultId: 'result' })))).toEqual({ completed: 2, total: 2 })
    expect(planTimeline(detail(steps, { canStartTest: true }))[1]).toMatchObject({ kind: 'test', state: 'active' })
    expect(planTimeline(detail([]))).toEqual([])
    expect(planProgress(planTimeline(detail([])))).toBeUndefined()
  })
})
