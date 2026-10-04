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

// T29: minimal student-facing class membership fact for report submission.
export const apiStudentActiveClassSchema = z.object({
  id: z.number().int(),
  name: z.string(),
  code: z.string(),
})
export const apiStudentActiveClassListSchema = z.array(apiStudentActiveClassSchema)
export type ApiStudentActiveClass = z.infer<typeof apiStudentActiveClassSchema>

export const apiAnalyticsDimensionSchema = z.object({
  dimension_id: z.string(),
  label: z.string(),
  average_score: nullableNumber,
  baseline_score: nullableNumber.optional(),
  current_score: nullableNumber.optional(),
  delta: nullableNumber.optional(),
  student_count: z.number().int().optional(),
  rate: nullableNumber.optional(),
  sample_count: z.number().int().nonnegative().optional(),
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
  published_case_count: z.number().int().nullable(),
  eligible_pairs: z.number().int().nullable(),
  started_pairs: z.number().int().nullable(),
  completed_pairs: z.number().int().nullable(),
  completion_rate: nullableNumber,
  current_average_score: nullableNumber,
  average_improvement: nullableNumber,
  dimensions: z.array(apiAnalyticsDimensionSchema),
  weak_dimensions: z.array(apiAnalyticsDimensionSchema),
  coverage: z
    .object({
      student_count: z.number().int().nonnegative(),
      participant_count: z.number().int().nonnegative(),
      evidence_count: z.number().int().nonnegative(),
      updated_at: z.string().nullable(),
    })
    .nullable()
    .optional(),
  completion: z
    .object({
      formal_task_rate: nullableNumber,
      formal_task_completed: z.number().int().nonnegative(),
      formal_task_attempted: z.number().int().nonnegative(),
      classroom_pbl_rate: nullableNumber,
      classroom_pbl_completed: z.number().int().nonnegative(),
      classroom_pbl_started: z.number().int().nonnegative(),
      case_rate: nullableNumber,
      case_completed: z.number().int().nonnegative(),
    })
    .nullable()
    .optional(),
  attention: z
    .object({
      support_needed: z.number().int().nonnegative(),
      formal_repeated_failure: z.number().int().nonnegative(),
      inactive: z.number().int().nonnegative(),
      items: z.array(z.object({ kind: z.string(), student_count: z.number().int().nonnegative(), route: z.string() })),
    })
    .nullable()
    .optional(),
  knowledge: z
    .array(
      z.object({
        point_code: z.string(),
        label: z.string().optional(),
        participant_count: z.number().int().nonnegative(),
        evidence_count: z.number().int().nonnegative(),
        correct_count: z.number().int().nonnegative().optional(),
        rate: nullableNumber,
        trend: nullableNumber.optional(),
      }),
    )
    .optional()
    .default([]),
  knowledge_notice: z.string().nullable().optional(),
  activity_sources: z
    .array(
      z.object({
        source_type: z.string(),
        event_count: z.number().int().nonnegative(),
        participant_count: z.number().int().nonnegative(),
      }),
    )
    .optional()
    .default([]),
  source_summary: z
    .array(
      z.object({
        source_type: z.string(),
        event_count: z.number().int().nonnegative(),
        participant_count: z.number().int().nonnegative(),
      }),
    )
    .optional()
    .default([]),
  privacy: z
    .object({ minimum_cohort_size: z.number().int().positive(), rankings_suppressed: z.boolean() })
    .nullable()
    .optional(),
  updated_at: z.string().nullable().optional(),
  cases: z.array(
    z.object({
      problem_id: z.number().int(),
      title: z.string(),
      completed: z.number().int(),
      assigned: z.number().int().nullable(),
      average_score: nullableNumber,
    }),
  ),
  students: z.array(
    z.object({
      student_id: z.number().int(),
      nickname: z.string(),
      completed: z.number().int(),
      assigned: z.number().int().nullable(),
      average_score: nullableNumber,
      formal_activity_completed: z.number().int().nonnegative().optional(),
      formal_activity_expected: z.number().int().nullable().optional(),
      formal_activity_rate: nullableNumber.optional(),
      recent_result: z.string().nullable().optional(),
      attention_codes: z.array(z.string()).optional().default([]),
      pbl_status: z.string().nullable().optional(),
      last_evidence_at: z.string().nullable().optional(),
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
  assigned: z.number().int().nullable(),
  started: z.number().int().nullable(),
  completed: z.number().int().nullable(),
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
  formal_evidence: z
    .object({ event_count: z.number().int().nonnegative(), last_evidence_at: z.string().nullable() })
    .nullable()
    .optional(),
  attention_codes: z.array(z.string()).optional().default([]),
  pbl_status: z.string().nullable().optional(),
})

export const apiAnalyticsKnowledgeSchema = z.object({
  class_id: z.number().int(),
  class_name: z.string(),
  participant_count: z.number().int().nonnegative(),
  due_backlog: z.number().int().nonnegative(),
  objective_correct_rate: nullableNumber,
  weak_points: z.array(z.object({ point_code: z.string(), student_count: z.number().int().nonnegative() })),
  rankings_suppressed: z.boolean(),
})
