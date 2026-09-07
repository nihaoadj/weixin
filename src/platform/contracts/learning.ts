import { z } from 'zod'
import type { components } from '@/data/contracts/openapi.generated'
import { apiCaseAttemptSchema } from './case'

export type ApiLearningPlan = components['schemas']['LearningPlanRead']
export type ApiLearningProfile = components['schemas']['LearningProfileRead']
export type ApiLearningTaskAttempt = components['schemas']['LearningTaskAttemptRead']

const timestamp = z.string().min(1)
const knowledgePointSchema = z.object({
  code: z.string().min(1),
  system_code: z.string().min(1),
  system_label: z.string().min(1),
  topic: z.string().min(1),
  title: z.string().min(1),
  objective: z.string(),
  reference: z.string(),
  card_count: z.number().int().nonnegative(),
  description: z.string().optional(),
  prerequisite_codes: z.array(z.string()).optional(),
  related_codes: z.array(z.string()).optional(),
  case_slug: z.string().optional(),
  catalog_version: z.string().min(1),
})

export const apiKnowledgeCatalogSchema = z.object({
  catalog_version: z.string().min(1),
  items: z.array(knowledgePointSchema),
})
export const apiKnowledgeMapSchema = z.object({
  items: z.array(
    z.object({
      code: z.string().min(1),
      status: z.enum(['not_started', 'weak', 'learning', 'due', 'stable']),
    }),
  ),
})
const reviewCardSchema = z.object({
  card_code: z.string().min(1),
  point_code: z.string().min(1),
  prompt: z.string().min(1),
  options: z.array(z.string().min(1)).min(2),
  due_at: timestamp.nullable().optional(),
})
const reviewItemSchema = z.object({
  id: z.number().int(),
  point_code: z.string().min(1),
  card_code: z.string().nullable().optional(),
  source_type: z.string(),
  source_id: z.string(),
  note: z.string(),
  active: z.boolean(),
  created_at: timestamp,
  updated_at: timestamp,
})
export const apiExitQuizSchema = z.object({ cards: z.array(reviewCardSchema) })
export const apiReviewQueueSchema = z.array(reviewCardSchema)
export const apiReviewDashboardSchema = z.object({
  due_count: z.number().int().nonnegative(),
  weak_point_codes: z.array(z.string()),
  items: z.array(reviewItemSchema),
})
export const apiReviewItemSchema = reviewItemSchema
export const apiReviewGradeSchema = z.object({
  card_code: z.string(),
  correct: z.boolean(),
  rating: z.enum(['again', 'hard', 'good', 'easy']),
  explanation: z.string(),
  due_at: timestamp,
})

export const apiRecallRevealSchema = z.object({
  card_code: z.string().min(1),
  point_code: z.string().min(1),
  prompt: z.string(),
  explanation: z.string(),
})
const publicDefinitionSchema = z
  .object({
    title: z.string().optional(),
    context: z.string().optional(),
    instruction: z.string().optional(),
    answer_schema: z.enum(['short_text', 'evidence_grid', 'decision_cards']).optional(),
    display_hints: z.array(z.string()).optional(),
    reason: z.string().optional(),
  })
  .passthrough()

export const apiLearningTaskSchema = z.object({
  id: z.number().int(),
  position: z.number().int(),
  task_type: z.enum(['focused_retry', 'micro_drill', 'cross_case_transfer']),
  dimension_id: z.string(),
  stage_id: z.string().nullable().optional(),
  problem_id: z.number().int().nullable().optional(),
  status: z.enum(['pending', 'in_progress', 'completed']),
  public_definition: publicDefinitionSchema.optional().default({}),
  started_at: timestamp.nullable().optional(),
  completed_at: timestamp.nullable().optional(),
})

export const apiLearningPlanSchema = z.object({
  id: z.number().int(),
  status: z.enum(['active', 'completed', 'superseded']),
  source_assessment_id: z.number().int().nullable(),
  source_type: z.enum(['case_assessment', 'pbl_suggestion']),
  source_id: z.number().int().nullable(),
  target_dimension_ids: z.array(z.string()),
  due_at: timestamp,
  generation_mode: z.string(),
  model_name: z.string(),
  prompt_version: z.string(),
  fallback_used: z.boolean(),
  failure_reason: z.string().nullable().optional(),
  created_at: timestamp,
  completed_at: timestamp.nullable().optional(),
  superseded_at: timestamp.nullable().optional(),
  tasks: z.array(apiLearningTaskSchema).optional().default([]),
})

const masterySchema = z.object({ average_score: z.number(), attempt_count: z.number().int().nonnegative() })

export const apiLearningProfileSchema = z.object({
  formal_dimensions: z.array(z.record(z.string(), z.unknown())).optional().default([]),
  recent_assessments: z.array(z.record(z.string(), z.unknown())).optional().default([]),
  practice_mastery: z.record(z.string(), masterySchema).optional().default({}),
  active_plan: apiLearningPlanSchema.nullable().optional(),
  unread_count: z.number().int().nonnegative().optional().default(0),
})

export const apiLearningTaskAttemptSchema = z.object({
  id: z.number().int(),
  task_id: z.number().int(),
  status: z.enum(['in_progress', 'assessed']),
  answer: z.record(z.string(), z.unknown()).optional().default({}),
  public_definition: publicDefinitionSchema.optional().default({}),
  score: z.number().nullable().optional(),
  evidence: z.array(z.string()).optional().default([]),
  feedback: z.string().optional().default(''),
  next_step: z.string().optional().default(''),
  created_at: timestamp,
  assessed_at: timestamp.nullable().optional(),
})

export const apiLearningTaskStartSchema = z.discriminatedUnion('mode', [
  z.object({ mode: z.literal('case_attempt'), task: apiLearningTaskSchema, attempt: apiCaseAttemptSchema }),
  z.object({ mode: z.literal('micro_drill'), task: apiLearningTaskSchema, attempt: apiLearningTaskAttemptSchema }),
])

const notificationSchema = z.object({
  id: z.number().int(),
  type: z.enum([
    'learning_plan_ready',
    'learning_plan_due',
    'learning_plan_completed',
    'pbl_mastery_improved',
    'pbl_reinforcement_activated',
    'pbl_automation_exhausted',
  ]),
  entity_type: z.literal('learning_plan'),
  entity_id: z.number().int(),
  title: z.string(),
  body: z.string(),
  read_at: timestamp.nullable().optional(),
  created_at: timestamp,
})

export const apiNotificationPageSchema = z.object({
  items: z.array(notificationSchema),
  unread_count: z.number().int().nonnegative(),
})
