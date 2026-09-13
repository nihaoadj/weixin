import { z } from 'zod'
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
import type { PrivatePracticeFeedback, PrivatePracticeGroup, StudyPathState } from '@/types/study'

const ANALYTICS_TTL = 60_000
const STATE_TTL = 15_000
const studySectionSchema = z.object({ title: z.string(), text: z.string() })
const studyPathSchema = z.object({
  id: z.number(),
  point_code: z.string(),
  session_id: z.number(),
  material_version: z.string(),
})
const studySchema = z.object({
  material: z.object({
    version: z.string(),
    point_code: z.string(),
    title: z.string(),
    objective: z.string(),
    scenario: z.string(),
    background: z.array(studySectionSchema),
    example: studySectionSchema,
    remediation: z.array(studySectionSchema),
    reference: z.string(),
    review_status: z.literal('unreviewed'),
  }),
  path: studyPathSchema.nullable(),
  phase: z.string(),
  practice_unlocked: z.boolean(),
  review_unlocked: z.boolean(),
  legacy_access: z.boolean(),
  summary: z.string(),
  lock_reason: z.string(),
  history: z.array(studyPathSchema),
})
const privatePracticeSchema = z.object({
  id: z.number(),
  path_id: z.number(),
  cycle: z.union([z.literal(1), z.literal(2)]),
  status: z.enum(['generating', 'ready', 'failed']),
  failure: z.string().nullable(),
  questions: z.array(
    z.object({ index: z.number(), point_code: z.string(), prompt: z.string(), options: z.array(z.string()) }),
  ),
  attempts: z.array(
    z.object({
      id: z.number(),
      question_index: z.number(),
      selected_option: z.number(),
      correct: z.boolean(),
      due_at: z.string(),
      created_at: z.string(),
    }),
  ),
  due_indexes: z.array(z.number()),
  can_retest: z.boolean(),
  exhausted: z.boolean(),
})
const privateFeedbackSchema = z.object({
  id: z.number(),
  question_index: z.number(),
  selected_option: z.number(),
  correct: z.boolean(),
  explanation: z.string(),
  reference_option: z.number(),
  due_at: z.string(),
  created_at: z.string(),
})

const mapPath = (value: z.infer<typeof studyPathSchema>) => ({
  id: value.id,
  pointCode: value.point_code,
  sessionId: String(value.session_id),
  materialVersion: value.material_version,
})
const mapStudy = (value: z.infer<typeof studySchema>): StudyPathState => ({
  material: {
    version: value.material.version,
    pointCode: value.material.point_code,
    title: value.material.title,
    objective: value.material.objective,
    scenario: value.material.scenario,
    background: value.material.background,
    example: value.material.example,
    remediation: value.material.remediation,
    reference: value.material.reference,
    reviewStatus: value.material.review_status,
  },
  path: value.path ? mapPath(value.path) : undefined,
  phase: value.phase,
  practiceUnlocked: value.practice_unlocked,
  reviewUnlocked: value.review_unlocked,
  legacyAccess: value.legacy_access,
  summary: value.summary,
  lockReason: value.lock_reason,
  history: value.history.map(mapPath),
})
const mapPrivatePractice = (value: z.infer<typeof privatePracticeSchema>): PrivatePracticeGroup => ({
  id: value.id,
  pathId: value.path_id,
  cycle: value.cycle,
  status: value.status,
  failure: value.failure || undefined,
  questions: value.questions.map((question) => ({
    index: question.index,
    pointCode: question.point_code,
    prompt: question.prompt,
    options: question.options,
  })),
  attempts: value.attempts.map((attempt) => ({
    id: attempt.id,
    questionIndex: attempt.question_index,
    selectedOption: attempt.selected_option,
    correct: attempt.correct,
    dueAt: attempt.due_at,
    createdAt: attempt.created_at,
  })),
  dueIndexes: value.due_indexes,
  canRetest: value.can_retest,
  exhausted: value.exhausted,
})

export async function getStudyPath(pointCode: string): Promise<StudyPathState> {
  return mapStudy(
    await apiRequest({
      path: `/learning/knowledge-points/${encodePathSegment(pointCode)}/study`,
      cacheTtlMs: STATE_TTL,
      schema: studySchema,
    }),
  )
}

export async function startStudyPath(input: {
  pointCode: string
  clientId: string
  interactionStyle: 'guided' | 'direct'
  newRound?: boolean
}): Promise<StudyPathState> {
  return mapStudy(
    await apiRequest({
      path: `/learning/knowledge-points/${encodePathSegment(input.pointCode)}/study/start`,
      method: 'POST',
      body: {
        client_id: input.clientId,
        interaction_style: input.interactionStyle,
        new_round: Boolean(input.newRound),
      },
      schema: studySchema,
      invalidateCache: [`/learning/knowledge-points/${encodePathSegment(input.pointCode)}/study`],
    }),
  )
}

export async function getStudyPractices(pathId: number): Promise<PrivatePracticeGroup[]> {
  return (
    await apiRequest({
      path: `/learning/study-paths/${encodePathSegment(pathId)}/practices`,
      cacheTtlMs: STATE_TTL,
      schema: z.array(privatePracticeSchema),
    })
  ).map(mapPrivatePractice)
}

export async function generateStudyPractice(
  pathId: number,
  cycle: 1 | 2,
  clientId: string,
): Promise<PrivatePracticeGroup> {
  return mapPrivatePractice(
    await apiRequest({
      path: `/learning/study-paths/${encodePathSegment(pathId)}/practices`,
      method: 'POST',
      body: { cycle, client_id: clientId },
      schema: privatePracticeSchema,
      invalidateCache: ['/learning/self-practices/history'],
    }),
  )
}

export async function getPrivatePractice(id: number): Promise<PrivatePracticeGroup> {
  return mapPrivatePractice(
    await apiRequest({
      path: `/learning/self-practices/${encodePathSegment(id)}`,
      cacheTtlMs: STATE_TTL,
      schema: privatePracticeSchema,
    }),
  )
}

export async function getPrivatePracticeHistory(): Promise<PrivatePracticeGroup[]> {
  return (
    await apiRequest({
      path: '/learning/self-practices/history',
      cacheTtlMs: STATE_TTL,
      schema: z.array(privatePracticeSchema),
    })
  ).map(mapPrivatePractice)
}

export async function answerPrivatePractice(input: {
  groupId: number
  clientId: string
  questionIndex: number
  selectedOption: number
}): Promise<PrivatePracticeFeedback> {
  const value = await apiRequest({
    path: `/learning/self-practices/${encodePathSegment(input.groupId)}/answers`,
    method: 'POST',
    body: { client_id: input.clientId, question_index: input.questionIndex, selected_option: input.selectedOption },
    schema: privateFeedbackSchema,
    invalidateCache: [`/learning/self-practices/${input.groupId}`, '/learning/self-practices/history'],
  })
  return {
    id: value.id,
    questionIndex: value.question_index,
    selectedOption: value.selected_option,
    correct: value.correct,
    explanation: value.explanation,
    referenceOption: value.reference_option,
    dueAt: value.due_at,
    createdAt: value.created_at,
  }
}

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
    description: item.description,
    prerequisiteCodes: item.prerequisite_codes,
    relatedCodes: item.related_codes,
    caseSlug: item.case_slug,
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
    invalidateCache: [
      '/learning/knowledge-map',
      '/learning/review-dashboard',
      '/learning/reviews/due',
      '/learning/review-items',
    ],
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
    invalidateCache: [
      '/learning/knowledge-map',
      '/learning/review-dashboard',
      '/learning/reviews/due',
      '/learning/review-items',
    ],
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
      invalidateCache: ['/learning/knowledge-map', '/learning/review-dashboard', '/learning/review-items'],
    }),
  )
}

export async function dismissReviewItem(id: number): Promise<void> {
  await apiRequest({
    path: `/learning/review-items/${encodePathSegment(id)}/dismiss`,
    method: 'POST',
    invalidateCache: ['/learning/knowledge-map', '/learning/review-dashboard', '/learning/review-items'],
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
    sourceType: value.source_type,
    sourceId: value.source_id,
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
  getStudyPath,
  startStudyPath,
  getStudyPractices,
  generateStudyPractice,
  getPrivatePractice,
  getPrivatePracticeHistory,
  answerPrivatePractice,
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
