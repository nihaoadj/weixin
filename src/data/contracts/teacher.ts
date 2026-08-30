import { z } from 'zod'

const nullableNumber = z.number().nullable()

export const apiTeacherClassSchema = z.object({
  id: z.number().int(),
  name: z.string(),
  code: z.string(),
  status: z.string(),
  teacher_id: z.number().int(),
  created_at: z.string().min(1),
})
export const apiTeacherClassListSchema = z.array(apiTeacherClassSchema)

export const apiTeacherStudentListSchema = z.array(
  z.object({
    id: z.number().int(),
    nickname: z.string(),
    external_id: z.string(),
    joined_at: z.string(),
  }),
)

export const apiAnalyticsDimensionSchema = z.object({
  dimension_id: z.string(),
  label: z.string(),
  average_score: nullableNumber,
  baseline_score: nullableNumber.optional(),
  current_score: nullableNumber.optional(),
  delta: nullableNumber.optional(),
  student_count: z.number().int().optional(),
  rate: nullableNumber.optional(),
})

const analyticsScopeSchema = z.object({
  class_id: z.number().int().nullable(),
  class_name: z.string().nullable(),
  date_from: z.string(),
  date_to: z.string(),
})

export const apiAnalyticsOverviewSchema = z.object({
  scope: analyticsScopeSchema,
  student_count: z.number().int(),
  published_case_count: z.number().int(),
  eligible_pairs: z.number().int(),
  started_pairs: z.number().int(),
  completed_pairs: z.number().int(),
  completion_rate: nullableNumber,
  current_average_score: nullableNumber,
  average_improvement: nullableNumber,
  dimensions: z.array(apiAnalyticsDimensionSchema),
  weak_dimensions: z.array(apiAnalyticsDimensionSchema),
  cases: z.array(
    z.object({
      problem_id: z.number().int(),
      title: z.string(),
      completed: z.number().int(),
      assigned: z.number().int(),
      average_score: nullableNumber,
    }),
  ),
  students: z.array(
    z.object({
      student_id: z.number().int(),
      nickname: z.string(),
      completed: z.number().int(),
      assigned: z.number().int(),
      average_score: nullableNumber,
    }),
  ),
})

export const apiAnalyticsCaseSchema = z.object({
  problem: z.object({
    id: z.number().int(),
    title: z.string(),
    version: z.number().int(),
    slug: z.string().nullable().optional(),
  }),
  eligible_pairs: z.number().int(),
  started_pairs: z.number().int(),
  completed_pairs: z.number().int(),
  completion_rate: nullableNumber,
  current_average_score: nullableNumber,
  average_improvement: nullableNumber,
  average_duration_minutes: nullableNumber,
  dimensions: z.array(apiAnalyticsDimensionSchema),
  distribution: z.record(z.string(), z.number()),
  students: z.array(
    z.object({
      student_id: z.number().int(),
      nickname: z.string(),
      status: z.string(),
      baseline: nullableNumber,
      current: nullableNumber,
      delta: nullableNumber,
      focus_stage: z.string().nullable(),
      last_assessed_at: z.string().nullable(),
    }),
  ),
})

export const apiAnalyticsStudentSchema = z.object({
  student: z.object({ id: z.number().int(), nickname: z.string() }),
  assigned: z.number().int(),
  started: z.number().int(),
  completed: z.number().int(),
  completion_rate: nullableNumber,
  current_average_score: nullableNumber,
  average_improvement: nullableNumber,
  dimensions: z.array(apiAnalyticsDimensionSchema),
  cases: z.array(
    z.object({
      problem_id: z.number().int(),
      title: z.string(),
      version: z.number().int(),
      first_score: nullableNumber,
      latest_score: nullableNumber,
      delta: nullableNumber,
      attempt_count: z.number().int(),
      focus_stage: z.string().nullable(),
      last_assessed_at: z.string().nullable(),
    }),
  ),
  timeline: z.array(
    z.object({
      attempt_id: z.number().int(),
      problem_id: z.number().int(),
      score: z.number(),
      assessed_at: z.string().nullable(),
    }),
  ),
  learning_plan: z
    .object({
      id: z.number().int(),
      status: z.string(),
      target_dimension_ids: z.array(z.string()),
      due_at: z.string(),
    })
    .nullable()
    .optional(),
  practice_mastery: z
    .record(z.string(), z.object({ average_score: z.number(), attempt_count: z.number().int() }))
    .optional()
    .default({}),
})
