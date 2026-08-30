import { apiRequest, isRemoteApiEnabled } from '@/services/apiClient'
import type { LearningNotification, LearningPlan, LearningProfile, LearningTaskAttempt } from '@/types/learning'

const camel = <T>(value: unknown): T => {
  if (Array.isArray(value)) return value.map((item) => camel(item)) as T
  if (!value || typeof value !== 'object') return value as T
  return Object.fromEntries(
    Object.entries(value as Record<string, unknown>).map(([key, item]) => [
      key.replace(/_([a-z])/g, (_, letter: string) => letter.toUpperCase()),
      camel(item),
    ]),
  ) as T
}

const emptyProfile: LearningProfile = {
  formalDimensions: [],
  recentAssessments: [],
  practiceMastery: {},
  unreadCount: 0,
}

export async function getLearningProfile(): Promise<LearningProfile> {
  if (!isRemoteApiEnabled()) return emptyProfile
  return camel(await apiRequest({ path: '/learning/profile' }))
}

export async function createLearningPlan(attemptId: string): Promise<LearningPlan> {
  return camel(await apiRequest({ path: `/attempts/${attemptId}/learning-plan`, method: 'POST' }))
}

export async function getCurrentLearningPlan(): Promise<LearningPlan | undefined> {
  if (!isRemoteApiEnabled()) return undefined
  try {
    return camel(await apiRequest({ path: '/learning-plans/current' }))
  } catch (error) {
    if (error instanceof Error && error.message.includes('RESOURCE_NOT_FOUND')) return undefined
    throw error
  }
}

export async function getLearningPlan(id: number): Promise<LearningPlan> {
  return camel(await apiRequest({ path: `/learning-plans/${id}` }))
}

export async function startLearningTask(id: number): Promise<{
  mode: 'case_attempt' | 'micro_drill'
  task: LearningPlan['tasks'][number]
  attempt: Record<string, unknown>
}> {
  return camel(await apiRequest({ path: `/learning-tasks/${id}/start`, method: 'POST' }))
}

export async function getLearningTaskAttempt(id: number): Promise<LearningTaskAttempt> {
  return camel(await apiRequest({ path: `/learning-task-attempts/${id}` }))
}

export async function submitLearningTaskAttempt(
  id: number,
  answer: Record<string, unknown>,
): Promise<LearningTaskAttempt> {
  return camel(await apiRequest({ path: `/learning-task-attempts/${id}/submit`, method: 'POST', body: { answer } }))
}

export async function completeLearningPlan(id: number): Promise<LearningPlan> {
  return camel(await apiRequest({ path: `/learning-plans/${id}/complete`, method: 'POST' }))
}

export async function getLearningNotifications(
  unreadOnly = false,
): Promise<{ items: LearningNotification[]; unreadCount: number }> {
  if (!isRemoteApiEnabled()) return { items: [], unreadCount: 0 }
  return camel(await apiRequest({ path: `/notifications?unread_only=${unreadOnly ? 'true' : 'false'}&limit=50` }))
}

export async function markLearningNotificationsRead(): Promise<void> {
  if (isRemoteApiEnabled()) await apiRequest({ path: '/notifications/read-all', method: 'POST' })
}
