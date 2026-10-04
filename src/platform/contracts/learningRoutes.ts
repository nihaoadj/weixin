import { z } from 'zod'

const uuid = z.string().uuid()
const sourceKind = z.enum(['classroom', 'autonomous'])
const reviewKind = z.enum(['teacher', 'ai_direct']).nullable()
const finalTestFormat = z.enum(['single_choice_v1', 'mixed_v2'])
const questionType = z.enum(['single_choice', 'multiple_choice', 'short_answer'])
const optionAnswer = z.number().int().min(0).max(3)
const rubricCriterionSchema = z
  .object({
    criterion_id: z.string().min(1).max(80),
    description: z.string().min(1).max(300),
    max_points: z.literal(10),
  })
  .strict()
const testSummarySchema = z
  .object({
    id: uuid,
    title: z.string(),
    question_count: z.number().int().nonnegative(),
    generation_state: z.string(),
    review_state: z.string(),
    review_kind: reviewKind,
    can_start: z.boolean(),
    lock_reason: z.string().nullable(),
    claim_expires_at: z.string().nullable(),
    retry_allowed: z.boolean(),
  })
  .strict()
const routeSummarySchema = z
  .object({
    id: uuid,
    title: z.string(),
    source_kind: sourceKind,
    scope_status: z.enum(['active', 'inactive']).default('active'),
    session_locator: z.string(),
    goal_point_codes: z.array(z.string()),
    status: z.string(),
    next_action: z.string(),
    progress: z
      .object({ completed_steps: z.number().int().nonnegative(), total_steps: z.number().int().nonnegative() })
      .strict(),
    updated_at: z.string(),
    test_summary: testSummarySchema,
    result_id: uuid.nullable(),
    generation_state: z.string(),
    claim_expires_at: z.string().nullable(),
    retry_allowed: z.boolean(),
  })
  .strict()
const stepSchema = z
  .object({
    id: uuid,
    position: z.number().int().positive(),
    kind: z.enum(['reading', 'case']),
    title: z.string(),
    goal_point_codes: z.array(z.string()),
    status: z.string(),
    case_id: uuid.nullable(),
    completed_at: z.string().nullable(),
  })
  .strict()
const diagnosisSchema = z
  .object({
    gaps: z.array(z.record(z.string(), z.unknown())).default([]),
    reasoning_issues: z.array(z.record(z.string(), z.unknown())).default([]),
    diagnosis_outcome: z.string().default(''),
  })
  .passthrough()
const readingProgressSchema = z
  .object({
    lease_token: z.string().nullable(),
    accumulated_seconds: z.number().int().nonnegative(),
    last_seen_at: z.string().nullable(),
  })
  .strict()
const testQuestionSchema = z
  .object({
    id: uuid,
    position: z.number().int().positive(),
    point_code: z.string(),
    prompt: z.string(),
    question_type: questionType.default('single_choice'),
    options: z.array(z.string()).max(4),
  })
  .strict()
export const attemptReadSchema = z
  .object({
    id: uuid,
    status: z.string(),
    version: z.number().int().positive(),
    answers: z.record(z.string(), z.union([optionAnswer, z.array(optionAnswer).max(4), z.string()])),
    saved_at: z.string().nullable(),
    submitted_at: z.string().nullable(),
  })
  .strict()
const resultQuestionSchema = testQuestionSchema
  .extend({
    selected_option: optionAnswer.nullable().optional(),
    selected_options: z.array(optionAnswer).nullable().optional(),
    selected_text: z.string().nullable().optional(),
    correct_option: optionAnswer.nullable().optional(),
    correct_options: z.array(optionAnswer).nullable().optional(),
    reference_answer: z.string().nullable().optional(),
    points_awarded: z.number().int().nonnegative().nullable().optional(),
    points_possible: z.number().int().nonnegative().nullable().optional(),
    grading_feedback: z.string().nullable().optional(),
    rubric_results: z
      .array(
        z
          .object({
            criterion_id: z.string(),
            earned_points: z.number().int().min(0).max(10),
            evidence: z.string(),
          })
          .strict(),
      )
      .nullable()
      .optional(),
    explanation: z.string(),
  })
  .strict()
const teacherQuestionSchema = z
  .object({
    id: uuid.nullable(),
    position: z.number().int().positive(),
    primary_point_code: z.string(),
    prompt: z.string(),
    question_type: questionType.default('single_choice'),
    options: z.array(z.string()).max(4),
    correct_option: optionAnswer.nullable().optional(),
    correct_options: z.array(optionAnswer).nullable().optional(),
    reference_answer: z.string().nullable().optional(),
    rubric: z.array(rubricCriterionSchema).nullable().optional(),
    explanation: z.string(),
  })
  .strict()
const studentTestSchema = z
  .object({
    id: uuid,
    title: z.string(),
    review_kind: reviewKind,
    format_version: finalTestFormat.default('single_choice_v1'),
    released_version: z.number().int().positive(),
    released_digest: z.string(),
    questions: z.array(testQuestionSchema),
    attempt: attemptReadSchema.nullable(),
  })
  .strict()
  .superRefine((test, context) => {
    for (const [index, question] of test.questions.entries()) {
      const expectedOptions = question.question_type === 'short_answer' ? 0 : 4
      if (question.options.length !== expectedOptions)
        context.addIssue({
          code: 'custom',
          path: ['questions', index, 'options'],
          message: 'Options do not match question type',
        })
    }
    if (
      test.format_version === 'single_choice_v1' &&
      test.questions.some((question) => question.question_type !== 'single_choice')
    )
      context.addIssue({
        code: 'custom',
        path: ['questions'],
        message: 'Legacy tests must contain single-choice questions',
      })
    if (test.format_version === 'mixed_v2') {
      const expected = ['single_choice', 'single_choice', 'single_choice', 'multiple_choice', 'short_answer']
      if (
        test.questions.length !== expected.length ||
        test.questions.some((question, index) => question.question_type !== expected[index])
      )
        context.addIssue({
          code: 'custom',
          path: ['questions'],
          message: 'Mixed tests must contain the fixed question sequence',
        })
    }
  })
const teacherTestSchema = z
  .object({
    id: uuid,
    route_id: uuid,
    title: z.string(),
    source_kind: z.literal('classroom'),
    class_id: z.number().int().positive(),
    session_id: z.number().int().positive(),
    student_id: z.number().int().positive(),
    diagnosis_summary: z.record(z.string(), z.unknown()),
    goal_point_codes: z.array(z.string()),
    generation_state: z.string(),
    review_state: z.string(),
    review_kind: reviewKind,
    current_scope_active: z.boolean(),
    format_version: finalTestFormat.default('single_choice_v1'),
    version: z.number().int().positive(),
    draft_digest: z.string(),
    questions: z.array(teacherQuestionSchema.extend({ id: uuid, source_digest: z.string().regex(/^[0-9a-f]{64}$/i) })),
    released_at: z.string().nullable(),
    feedback_draft: z.string(),
  })
  .strict()
  .superRefine((test, context) => {
    for (const [index, question] of test.questions.entries()) {
      const optionCount = question.question_type === 'short_answer' ? 0 : 4
      if (question.options.length !== optionCount)
        context.addIssue({
          code: 'custom',
          path: ['questions', index, 'options'],
          message: 'Options do not match question type',
        })
      if (question.question_type === 'single_choice' && question.correct_option == null)
        context.addIssue({
          code: 'custom',
          path: ['questions', index, 'correct_option'],
          message: 'Single-choice answer required',
        })
      if (
        question.question_type === 'multiple_choice' &&
        (!question.correct_options || question.correct_options.length === 0)
      )
        context.addIssue({
          code: 'custom',
          path: ['questions', index, 'correct_options'],
          message: 'Multiple-choice answers required',
        })
      if (question.question_type === 'short_answer' && (!question.reference_answer || !question.rubric?.length))
        context.addIssue({
          code: 'custom',
          path: ['questions', index],
          message: 'Short-answer grading criteria required',
        })
    }
    if (
      test.format_version === 'single_choice_v1' &&
      test.questions.some((question) => question.question_type !== 'single_choice')
    )
      context.addIssue({
        code: 'custom',
        path: ['questions'],
        message: 'Legacy tests must contain single-choice questions',
      })
    if (test.format_version === 'mixed_v2') {
      const expected = ['single_choice', 'single_choice', 'single_choice', 'multiple_choice', 'short_answer']
      if (
        test.questions.length !== expected.length ||
        test.questions.some((question, index) => question.question_type !== expected[index])
      )
        context.addIssue({
          code: 'custom',
          path: ['questions'],
          message: 'Mixed tests must contain the fixed question sequence',
        })
    }
  })
const resultSchema = z
  .object({
    id: uuid,
    route_id: uuid,
    source_kind: sourceKind,
    goal_point_codes: z.array(z.string()),
    route_summary: z.record(z.string(), z.unknown()),
    correct_count: z.number().int().nonnegative(),
    question_count: z.number().int().positive(),
    score: z.number().min(0).max(100),
    submitted_at: z.string(),
    questions: z.array(resultQuestionSchema),
    review_kind: reviewKind,
    format_version: finalTestFormat.default('single_choice_v1'),
  })
  .strict()
  .superRefine((result, context) => {
    for (const [index, question] of result.questions.entries()) {
      const optionCount = question.question_type === 'short_answer' ? 0 : 4
      if (question.options.length !== optionCount)
        context.addIssue({
          code: 'custom',
          path: ['questions', index, 'options'],
          message: 'Options do not match question type',
        })
    }
    if (
      result.format_version === 'single_choice_v1' &&
      result.questions.some((question) => question.question_type !== 'single_choice')
    )
      context.addIssue({
        code: 'custom',
        path: ['questions'],
        message: 'Legacy results must contain single-choice questions',
      })
    if (result.format_version === 'mixed_v2') {
      const expected = ['single_choice', 'single_choice', 'single_choice', 'multiple_choice', 'short_answer']
      if (
        result.questions.length !== expected.length ||
        result.questions.some((question, index) => question.question_type !== expected[index])
      )
        context.addIssue({
          code: 'custom',
          path: ['questions'],
          message: 'Mixed results must contain the fixed question sequence',
        })
    }
  })
const teacherLearningResultSchema = resultSchema
  .extend({
    student_id: z.number().int().positive(),
    class_id: z.number().int().positive(),
    session_id: z.number().int().positive(),
  })
  .strict()

export const routePageSchema = z
  .object({
    items: z.array(routeSummarySchema),
    total: z.number().int().nonnegative(),
    limit: z.number().int().positive(),
    offset: z.number().int().nonnegative(),
  })
  .strict()
export const routeDetailSchema = z
  .object({
    summary: routeSummarySchema,
    diagnosis_summary: diagnosisSchema,
    steps: z.array(stepSchema),
    test_summary: testSummarySchema,
    can_start_test: z.boolean(),
    lock_reasons: z.array(z.string()),
    route_version: z.number().int().positive(),
  })
  .strict()
export const readingStepSchema = stepSchema
  .extend({
    route_id: uuid,
    sources: z.array(z.record(z.string(), z.unknown())),
    ai_guide: z.string(),
    sections: z.array(z.record(z.string(), z.unknown())),
    learning_points: z.array(z.string()),
    reading_progress: readingProgressSchema,
  })
  .strict()
export const routeReadingProgressSchema = readingProgressSchema
export const routeCaseSchema = z
  .object({
    id: uuid,
    route_id: uuid,
    step_id: uuid,
    synthetic_case: z
      .object({
        title: z.string(),
        public_scenario: z.string(),
        case_facts: z.array(z.string()),
        target_point_codes: z.array(z.string()),
      })
      .strict(),
    phase: z.string(),
    revision: z.number().int().nonnegative(),
    status: z.string(),
    goals: z.array(z.object({ goal_id: z.string(), objective: z.string() }).strict()),
    stages: z
      .array(
        z
          .object({
            phase: z.enum([
              'pathology_recognition',
              'mechanism_explanation',
              'evidence_judgment',
              'summary_reflection',
            ]),
            goals: z
              .array(z.object({ goal_id: z.string(), objective: z.string() }).strict())
              .min(1)
              .max(3),
            prompt: z.string().min(1),
          })
          .strict(),
      )
      .length(4),
    messages: z.array(
      z
        .object({
          id: z.string(),
          role: z.enum(['student', 'assistant']),
          content: z.string(),
          revision: z.number().int().nonnegative(),
          phase: z.enum(['pathology_recognition', 'mechanism_explanation', 'evidence_judgment', 'summary_reflection']),
        })
        .strict(),
    ),
    next_prompt: z.string(),
    safety_notice: z.string(),
    pending_message: z
      .object({
        client_message_id: z.string(),
        request_revision: z.number().int().nonnegative(),
        processing_state: z.string(),
        retry_allowed: z.boolean(),
        claim_expires_at: z.string().nullable(),
      })
      .strict()
      .nullable(),
  })
  .strict()
export const routeCaseMessageResultSchema = z
  .object({
    client_message_id: z.string(),
    request_revision: z.number().int().nonnegative(),
    processing_state: z.string(),
    retry_allowed: z.boolean(),
    reply: z.string().nullable(),
    phase: z.string(),
    revision: z.number().int().nonnegative(),
    decision: z.string().nullable(),
    missing_elements: z.array(z.string()),
    status: z.string(),
  })
  .strict()
export const studentFinalTestSchema = studentTestSchema
export const teacherFinalTestSchema = teacherTestSchema
export const teacherFinalTestReviewQueueItemSchema = z
  .object({
    id: uuid,
    route_id: uuid,
    title: z.string(),
    class_id: z.number().int().positive(),
    class_name: z.string(),
    session_id: z.number().int().positive(),
    student_id: z.number().int().positive(),
    student_name: z.string(),
    generation_state: z.enum(['ready', 'generation_failed']),
    review_state: z.enum(['pending_review', 'needs_changes']),
    updated_at: z.string().datetime({ offset: true }),
    can_review: z.boolean(),
    can_retry: z.boolean(),
    action_reason: z.enum(['REVIEW_READY', 'GENERATION_FAILED']),
  })
  .strict()
export const teacherFinalTestReviewQueueSchema = z
  .object({
    items: z.array(teacherFinalTestReviewQueueItemSchema),
    counts: z
      .object({
        pending_review: z.number().int().nonnegative(),
        needs_changes: z.number().int().nonnegative(),
        generation_failed: z.number().int().nonnegative(),
      })
      .strict(),
    total: z.number().int().nonnegative(),
    limit: z.number().int().positive().max(100),
    offset: z.number().int().nonnegative(),
    as_of: z.string().datetime({ offset: true }),
  })
  .strict()
export const learningResultSchema = resultSchema
export const finalTestGradingStatusSchema = z
  .object({
    status: z.enum(['grading', 'completed']),
    test_id: uuid,
    route_id: uuid,
    result_id: uuid.nullable(),
    retry_allowed: z.boolean(),
    error_code: z.string().nullable(),
  })
  .strict()
export const finalTestSubmissionSchema = z.union([learningResultSchema, finalTestGradingStatusSchema])
export const learningResultTutorSchema = z
  .object({
    result_id: uuid,
    revision: z.number().int().nonnegative(),
    processing_state: z.enum(['idle', 'processing', 'retry_allowed']),
    pending_message_id: z.string().nullable(),
    messages: z.array(
      z
        .object({
          id: z.string(),
          role: z.enum(['student', 'assistant']),
          question_id: uuid,
          content: z.string(),
          sequence: z.number().int().positive(),
          created_at: z.string(),
        })
        .strict(),
    ),
  })
  .strict()
export const teacherLearningResultReadSchema = teacherLearningResultSchema
export const learningRouteGenerationSchema = z
  .object({
    route_id: uuid,
    component: z.enum(['route', 'test']),
    generation_state: z.string(),
    claim_expires_at: z.string().nullable(),
  })
  .strict()
export const finalTestReleaseSchema = z
  .object({
    test_id: uuid,
    released_version: z.number().int().positive(),
    released_digest: z.string(),
    released_at: z.string(),
  })
  .strict()
