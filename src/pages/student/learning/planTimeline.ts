import type { LearningRouteDetail, LearningRouteStep } from '@/features/learning/public'

export type PlanTimelineItem =
  | { kind: 'resource'; number: number; state: 'completed' | 'active' | 'locked'; step: LearningRouteStep }
  | { kind: 'test'; number: number; state: 'completed' | 'active' | 'locked' }

export function planTimeline(detail: LearningRouteDetail): PlanTimelineItem[] {
  if (!detail.steps.length) return []
  const resources: PlanTimelineItem[] = [...detail.steps]
    .sort((a, b) => a.position - b.position)
    .map((step, index) => ({
      kind: 'resource' as const,
      number: index + 1,
      state:
        step.status === 'completed'
          ? ('completed' as const)
          : step.status === 'locked'
            ? ('locked' as const)
            : ('active' as const),
      step,
    }))
  const testCompleted = Boolean(detail.summary.resultId) || detail.summary.status === 'completed'
  return [
    ...resources,
    {
      kind: 'test',
      number: resources.length + 1,
      state: testCompleted ? 'completed' : detail.canStartTest ? 'active' : 'locked',
    },
  ]
}

export function planProgress(items: PlanTimelineItem[]): { completed: number; total: number } | undefined {
  if (items.length <= 1) return undefined
  return { completed: items.filter((item) => item.state === 'completed').length, total: items.length }
}
