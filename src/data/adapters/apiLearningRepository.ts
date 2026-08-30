import {
  apiLearningPlanSchema,
  apiLearningProfileSchema,
  apiLearningTaskAttemptSchema,
  apiLearningTaskStartSchema,
  apiNotificationPageSchema,
} from '@/data/contracts/learning'
import { apiRequest, encodePathSegment } from '@/services/apiClient'
import type {
  LearningNotification,
  LearningPlan,
  LearningProfile,
  LearningTask,
  LearningTaskAttempt,
} from '@/types/learning'
import { AppError } from '@/types/errors'

const ANALYTICS_TTL = 60_000
const STATE_TTL = 15_000

function toTask(value: ReturnType<typeof apiLearningTaskStartSchema.parse>['task']): LearningTask {
  const definition = value.public_definition
  return {
    id: value.id,
    position: value.position,
    taskType: value.task_type,
    dimensionId: value.dimension_id,
    stageId: value.stage_id || undefined,
    problemId: value.problem_id ?? undefined,
    status: value.status,
    publicDefinition: {
      title: definition.title,
      context: definition.context,
      instruction: definition.instruction,
      answerSchema: definition.answer_schema,
      displayHints: definition.display_hints,
      reason: definition.reason,
    },
    startedAt: value.started_at || undefined,
    completedAt: value.completed_at || undefined,
  }
}

function toPlan(value: ReturnType<typeof apiLearningPlanSchema.parse>): LearningPlan {
  return {
    id: value.id,
    status: value.status,
    sourceAssessmentId: value.source_assessment_id,
    targetDimensionIds: value.target_dimension_ids,
    dueAt: value.due_at,
    generationMode: value.generation_mode,
    modelName: value.model_name,
    promptVersion: value.prompt_version,
    fallbackUsed: value.fallback_used,
    failureReason: value.failure_reason || undefined,
    createdAt: value.created_at,
    completedAt: value.completed_at || undefined,
    supersededAt: value.superseded_at || undefined,
    tasks: value.tasks.map(toTask),
  }
}

function toAttempt(value: ReturnType<typeof apiLearningTaskAttemptSchema.parse>): LearningTaskAttempt {
  const definition = value.public_definition
  return {
    id: value.id,
    taskId: value.task_id,
    status: value.status,
    answer: value.answer,
    publicDefinition: {
      title: definition.title,
      context: definition.context,
      instruction: definition.instruction,
      answerSchema: definition.answer_schema,
      displayHints: definition.display_hints,
      reason: definition.reason,
    },
    score: value.score ?? undefined,
    evidence: value.evidence,
    feedback: value.feedback,
    nextStep: value.next_step,
    createdAt: value.created_at,
    assessedAt: value.assessed_at || undefined,
  }
}

export async function getLearningProfile(): Promise<LearningProfile> {
  const profile = await apiRequest({
    path: '/learning/profile',
    cacheTtlMs: ANALYTICS_TTL,
    schema: apiLearningProfileSchema,
  })
  return {
    formalDimensions: profile.formal_dimensions,
    recentAssessments: profile.recent_assessments,
    practiceMastery: Object.fromEntries(
      Object.entries(profile.practice_mastery).map(([key, value]) => [
        key,
        { averageScore: value.average_score, attemptCount: value.attempt_count },
      ]),
    ),
    activePlan: profile.active_plan ? toPlan(profile.active_plan) : undefined,
    unreadCount: profile.unread_count,
  }
}

export async function createLearningPlan(attemptId: string): Promise<LearningPlan> {
  const value = await apiRequest({
    path: `/attempts/${encodePathSegment(attemptId)}/learning-plan`,
    method: 'POST',
    schema: apiLearningPlanSchema,
    invalidateCache: ['/learning', '/notifications'],
  })
  return toPlan(value)
}

export async function getCurrentLearningPlan(): Promise<LearningPlan | undefined> {
  try {
    return toPlan(
      await apiRequest({
        path: '/learning-plans/current',
        cacheTtlMs: STATE_TTL,
        schema: apiLearningPlanSchema,
      }),
    )
  } catch (error) {
    if (error instanceof AppError && error.code === 'RESOURCE_NOT_FOUND') return undefined
    throw error
  }
}

export async function getLearningPlan(id: number): Promise<LearningPlan> {
  return toPlan(
    await apiRequest({
      path: `/learning-plans/${encodePathSegment(id)}`,
      cacheTtlMs: STATE_TTL,
      schema: apiLearningPlanSchema,
    }),
  )
}

export async function startLearningTask(id: number): Promise<{
  mode: 'case_attempt' | 'micro_drill'
  task: LearningPlan['tasks'][number]
  attempt: Record<string, unknown>
}> {
  const value = await apiRequest({
    path: `/learning-tasks/${encodePathSegment(id)}/start`,
    method: 'POST',
    schema: apiLearningTaskStartSchema,
    invalidateCache: ['/learning'],
  })
  return { mode: value.mode, task: toTask(value.task), attempt: value.attempt }
}

export async function getLearningTaskAttempt(id: number): Promise<LearningTaskAttempt> {
  return toAttempt(
    await apiRequest({
      path: `/learning-task-attempts/${encodePathSegment(id)}`,
      cacheTtlMs: STATE_TTL,
      schema: apiLearningTaskAttemptSchema,
    }),
  )
}

export async function submitLearningTaskAttempt(
  id: number,
  answer: Record<string, unknown>,
): Promise<LearningTaskAttempt> {
  return toAttempt(
    await apiRequest({
      path: `/learning-task-attempts/${encodePathSegment(id)}/submit`,
      method: 'POST',
      body: { answer },
      schema: apiLearningTaskAttemptSchema,
      invalidateCache: ['/learning', '/notifications'],
    }),
  )
}

export async function completeLearningPlan(id: number): Promise<LearningPlan> {
  return toPlan(
    await apiRequest({
      path: `/learning-plans/${encodePathSegment(id)}/complete`,
      method: 'POST',
      schema: apiLearningPlanSchema,
      invalidateCache: ['/learning', '/notifications'],
    }),
  )
}

export async function getLearningNotifications(
  unreadOnly = false,
): Promise<{ items: LearningNotification[]; unreadCount: number }> {
  const value = await apiRequest({
    path: '/notifications',
    query: { unread_only: unreadOnly, limit: 50 },
    cacheTtlMs: STATE_TTL,
    schema: apiNotificationPageSchema,
  })
  return {
    items: value.items.map((item) => ({
      id: item.id,
      type: item.type,
      entityType: item.entity_type,
      entityId: item.entity_id,
      title: item.title,
      body: item.body,
      readAt: item.read_at || undefined,
      createdAt: item.created_at,
    })),
    unreadCount: value.unread_count,
  }
}

export async function markLearningNotificationsRead(): Promise<void> {
  await apiRequest({
    path: '/notifications/read-all',
    method: 'POST',
    invalidateCache: ['/notifications', '/learning/profile'],
  })
}

import type { LearningRepository } from '@/data/repositories/learning'
export const apiLearningRepository: LearningRepository = {
  getLearningProfile,
  createLearningPlan,
  getCurrentLearningPlan,
  getLearningPlan,
  startLearningTask,
  getLearningTaskAttempt,
  submitLearningTaskAttempt,
  completeLearningPlan,
  getLearningNotifications,
  markLearningNotificationsRead,
}
