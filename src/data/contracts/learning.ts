import { z } from 'zod'
import type { components } from './openapi.generated'
import { apiCaseAttemptSchema } from './case'

export type ApiLearningPlan = components['schemas']['LearningPlanRead']
export type ApiLearningProfile = components['schemas']['LearningProfileRead']
export type ApiLearningTaskAttempt = components['schemas']['LearningTaskAttemptRead']

const timestamp = z.string().min(1)
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
  source_assessment_id: z.number().int(),
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
  type: z.enum(['learning_plan_ready', 'learning_plan_due', 'learning_plan_completed']),
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
