import { z } from 'zod'

const positive = z.number().int().positive()
const nonnegative = z.number().int().nonnegative()
const percentage = z.number().min(0).max(100)
const date = z.string().regex(/^\d{4}-\d{2}-\d{2}$/)
const timestamp = z.string().datetime({ offset: true })
const sessionId = positive.nullable()

const metricBasis = z
  .object({
    progress: z.literal('published_route_cohort'),
    results: z.literal('completed_test_window'),
    diagnoses: z.literal('completed_diagnosis_window'),
  })
  .strict()

const scope = z
  .object({
    class_id: positive.nullable(),
    class_name: z.string().nullable(),
    class_ids: z.array(positive),
    session_id: sessionId,
    date_from: date,
    date_to: date,
    timezone: z.literal('Asia/Shanghai'),
    as_of: timestamp,
    metric_basis: metricBasis,
  })
  .strict()

const cohort = z
  .object({
    published_routes: nonnegative,
    completed_tests: nonnegative,
    completion_rate: percentage.nullable(),
    grading_tests: nonnegative,
  })
  .strict()

const periodResults = z
  .object({
    completed_tests: nonnegative,
    average_score: percentage.nullable(),
    format_counts: z.record(z.string(), nonnegative),
  })
  .strict()

const discussionProgress = z.object({ participated: nonnegative, active: nonnegative, completed: nonnegative }).strict()
const discussion = z
  .object({
    participation_id: positive,
    session_id: positive,
    class_id: positive,
    student_id: positive,
    phase: z.string(),
    status: z.string(),
    started_at: timestamp,
    completed_at: timestamp.nullable(),
  })
  .strict()

const student = z
  .object({
    student_id: positive,
    student_name: z.string(),
    class_ids: z.array(positive),
    cohort,
    period_results: periodResults,
    diagnosis_count: nonnegative,
    last_completed_at: timestamp.nullable(),
    discussion_progress: discussionProgress,
  })
  .strict()

const knowledge = z
  .object({
    point_code: z.string().min(1),
    correct_count: nonnegative,
    objective_count: nonnegative,
    invalid_objective_count: nonnegative,
    accuracy_rate: percentage.nullable(),
    short_answer_count: nonnegative,
    invalid_short_answer_count: nonnegative,
    points_awarded: z.number().nonnegative(),
    points_possible: z.number().nonnegative(),
    short_answer_score_rate: percentage.nullable(),
  })
  .strict()

const finding = z.object({ code: z.string().min(1), summary: z.string().max(160) }).strict()

const diagnosis = z
  .object({
    participation_id: positive,
    session_id: positive,
    class_id: positive,
    class_name: z.string(),
    student_id: positive,
    student_name: z.string(),
    completed_at: timestamp,
    knowledge_gap_codes: z.array(z.string().min(1)),
    reasoning_issue_codes: z.array(z.string().min(1)),
    knowledge_gaps: z.array(finding),
    reasoning_issues: z.array(finding),
  })
  .strict()

const findingGroup = z
  .object({
    code: z.string().min(1),
    student_count: nonnegative,
    diagnosis_count: nonnegative,
    last_completed_at: timestamp,
  })
  .strict()

const resultSummary = z
  .object({
    result_id: z.string().uuid(),
    route_id: z.string().uuid(),
    class_id: positive,
    session_id: positive,
    student_id: positive,
    score: percentage,
    completed_at: timestamp,
    format_version: z.enum(['single_choice_v1', 'mixed_v2']),
  })
  .strict()

const routeProgress = z
  .object({
    route_id: z.string().uuid(),
    student_id: positive,
    class_id: positive,
    session_id: positive,
    published_at: timestamp,
    result_id: z.string().uuid().nullable(),
    test_generation_state: z.string().nullable(),
    test_review_state: z.string().nullable(),
    attempt_status: z.string().nullable(),
    completed_steps: nonnegative.nullable(),
    total_steps: nonnegative.nullable(),
    reading_seconds: nonnegative.nullable(),
  })
  .strict()

export const apiTeacherInsightsOverviewSchema = z
  .object({
    scope,
    cohort,
    period_results: periodResults,
    diagnosis_count: nonnegative,
    student_count: nonnegative,
  })
  .strict()

export const apiTeacherInsightsStudentsSchema = z
  .object({
    scope,
    items: z.array(student),
    total: nonnegative,
    limit: positive,
    offset: nonnegative,
  })
  .strict()

export const apiTeacherInsightsStudentSchema = z
  .object({
    scope,
    summary: student,
    discussions: z.array(discussion),
    routes: z.array(routeProgress),
    results: z.array(resultSummary),
    diagnoses: z.array(diagnosis),
    knowledge: z.array(knowledge),
  })
  .strict()

export const apiTeacherInsightsKnowledgeSchema = z
  .object({
    scope,
    items: z.array(knowledge),
    result_count: nonnegative,
  })
  .strict()

export const apiTeacherInsightsDiagnosticsSchema = z
  .object({
    scope,
    items: z.array(diagnosis),
    total: nonnegative,
    limit: positive,
    offset: nonnegative,
    knowledge_gaps: z.array(findingGroup),
    reasoning_issues: z.array(findingGroup),
  })
  .strict()
