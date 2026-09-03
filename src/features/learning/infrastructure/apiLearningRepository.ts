import {
  apiLearningPlanSchema,
  apiLearningProfileSchema,
  apiLearningTaskAttemptSchema,
  apiLearningTaskStartSchema,
  apiKnowledgeCatalogSchema,
  apiKnowledgeMapSchema,
  apiNotificationPageSchema,
  apiExitQuizSchema,
  apiReviewDashboardSchema,
  apiReviewGradeSchema,
  apiRecallRevealSchema,
  apiReviewItemSchema,
  apiReviewQueueSchema,
} from '@/platform/contracts/learning'
import { apiRequest, encodePathSegment } from '@/platform/http/apiClient'
import type {
  LearningNotification,
  LearningPlan,
  LearningProfile,
  LearningTask,
  LearningTaskAttempt,
} from '@/types/learning'
import { AppError } from '@/types/errors'
import type {
  KnowledgePoint,
  KnowledgeMapPoint,
  RecallReveal,
  ReviewCard,
  ReviewDashboard,
  ReviewGrade,
  ReviewItem,
} from '@/types/knowledge'

const ANALYTICS_TTL = 60_000
const STATE_TTL = 15_000

export async function getKnowledgeCatalog(): Promise<KnowledgePoint[]> {
  const catalog = await apiRequest({
    path: '/knowledge/tree',
    cacheTtlMs: ANALYTICS_TTL,
    schema: apiKnowledgeCatalogSchema,
  })
  return catalog.items.map((item) => ({
    code: item.code,
    systemCode: item.system_code,
    systemLabel: item.system_label,
    topic: item.topic,
    title: item.title,
    objective: item.objective,
    reference: item.reference,
    cardCount: item.card_count,
    catalogVersion: item.catalog_version,
  }))
}

export async function getKnowledgeMap(): Promise<KnowledgeMapPoint[]> {
  const [catalog, map] = await Promise.all([
    getKnowledgeCatalog(),
    apiRequest({ path: '/learning/knowledge-map', cacheTtlMs: STATE_TTL, schema: apiKnowledgeMapSchema }),
  ])
  const statusByCode = new Map(map.items.map((item) => [item.code, item.status]))
  return catalog.map((point) => ({ ...point, status: statusByCode.get(point.code) || 'not_started' }))
}

function toReviewCard(value: {
  card_code: string
  point_code: string
  prompt: string
  options: string[]
  due_at?: string | null
}): ReviewCard {
  return {
    cardCode: value.card_code,
    pointCode: value.point_code,
    prompt: value.prompt,
    options: value.options,
    dueAt: value.due_at || undefined,
  }
}

function toReviewItem(value: ReturnType<typeof apiReviewItemSchema.parse>): ReviewItem {
  return {
    id: value.id,
    pointCode: value.point_code,
    cardCode: value.card_code || undefined,
    sourceType: value.source_type,
    sourceId: value.source_id,
    note: value.note,
    active: value.active,
    createdAt: value.created_at,
    updatedAt: value.updated_at,
  }
}

function toReviewDashboard(value: ReturnType<typeof apiReviewDashboardSchema.parse>): ReviewDashboard {
  return {
    dueCount: value.due_count,
    weakPointCodes: value.weak_point_codes,
    items: value.items.map(toReviewItem),
  }
}

export async function createExitQuiz(topicCodes: string[]): Promise<ReviewCard[]> {
  const value = await apiRequest({
    path: '/learning/exit-quiz',
    method: 'POST',
    body: { topic_codes: topicCodes },
    schema: apiExitQuizSchema,
  })
  return value.cards.map(toReviewCard)
}

export async function getReviewDashboard(): Promise<ReviewDashboard> {
  return toReviewDashboard(
    await apiRequest({ path: '/learning/review-dashboard', cacheTtlMs: STATE_TTL, schema: apiReviewDashboardSchema }),
  )
}

export async function getDueReviewQueue(): Promise<ReviewCard[]> {
  const value = await apiRequest({ path: '/learning/reviews/due', cacheTtlMs: STATE_TTL, schema: apiReviewQueueSchema })
  return value.map(toReviewCard)
}

export async function gradeObjectiveCard(
  cardCode: string,
  selectedOption: number,
  confidence: 'low' | 'medium' | 'high',
): Promise<ReviewGrade> {
  const value = await apiRequest({
    path: `/learning/reviews/${encodePathSegment(cardCode)}/grade`,
    method: 'POST',
    body: { selected_option: selectedOption, confidence },
    schema: apiReviewGradeSchema,
    invalidateCache: ['/learning/review-dashboard', '/learning/reviews/due', '/learning/review-items'],
  })
  return {
    cardCode: value.card_code,
    correct: value.correct,
    rating: value.rating,
    explanation: value.explanation,
    dueAt: value.due_at,
  }
}

export async function revealRecallCard(cardId: number): Promise<RecallReveal> {
  const value = await apiRequest({
    path: `/learning/recall-cards/${encodePathSegment(cardId)}/reveal`,
    method: 'POST',
    schema: apiRecallRevealSchema,
  })
  return {
    cardCode: value.card_code,
    pointCode: value.point_code,
    prompt: value.prompt,
    explanation: value.explanation,
  }
}

export async function rateRecallCard(cardId: number, rating: 'again' | 'hard' | 'good' | 'easy'): Promise<ReviewGrade> {
  const value = await apiRequest({
    path: `/learning/recall-cards/${encodePathSegment(cardId)}/rate`,
    method: 'POST',
    body: { rating },
    schema: apiReviewGradeSchema,
    invalidateCache: ['/learning/review-dashboard', '/learning/reviews/due', '/learning/review-items'],
  })
  return {
    cardCode: value.card_code,
    correct: value.correct,
    rating: value.rating,
    explanation: value.explanation,
    dueAt: value.due_at,
  }
}

export async function captureManualReviewItem(input: {
  pointCode: string
  sourceType: string
  sourceId: string
  note?: string
}): Promise<ReviewItem> {
  return toReviewItem(
    await apiRequest({
      path: '/learning/review-items',
      method: 'POST',
      body: {
        point_code: input.pointCode,
        source_type: input.sourceType,
        source_id: input.sourceId,
        note: input.note || '',
      },
      schema: apiReviewItemSchema,
      invalidateCache: ['/learning/review-dashboard', '/learning/review-items'],
    }),
  )
}

export async function dismissReviewItem(id: number): Promise<void> {
  await apiRequest({
    path: `/learning/review-items/${encodePathSegment(id)}/dismiss`,
    method: 'POST',
    invalidateCache: ['/learning/review-dashboard', '/learning/review-items'],
  })
}

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

import type { LearningRepository } from '@/features/learning/domain/ports'
export const apiLearningRepository: LearningRepository = {
  getKnowledgeCatalog,
  getKnowledgeMap,
  createExitQuiz,
  getReviewDashboard,
  getDueReviewQueue,
  gradeObjectiveCard,
  revealRecallCard,
  rateRecallCard,
  captureManualReviewItem,
  dismissReviewItem,
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
