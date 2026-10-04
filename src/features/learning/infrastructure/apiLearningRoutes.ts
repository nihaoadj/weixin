import { apiRequest, encodePathSegment } from '@/platform/http/apiClient'
import type { z } from 'zod'
import {
  attemptReadSchema,
  finalTestGradingStatusSchema,
  finalTestReleaseSchema,
  finalTestSubmissionSchema,
  learningResultSchema,
  learningResultTutorSchema,
  learningRouteGenerationSchema,
  readingStepSchema,
  routeCaseMessageResultSchema,
  routeCaseSchema,
  routeDetailSchema,
  routePageSchema,
  routeReadingProgressSchema,
  studentFinalTestSchema,
  teacherLearningResultReadSchema,
  teacherFinalTestReviewQueueSchema,
  teacherFinalTestSchema,
} from '@/platform/contracts/learningRoutes'
import type { LearningRoutesPort } from '../domain/learningRoutesPort'
import type {
  LearningRouteSummary,
  LearningRouteDetail,
  LearningRouteReading,
  LearningRouteGenerationReceipt,
  LearningRouteStep,
  LearningRouteTestSummary,
} from '../domain/learningRoutes'
import type { RouteCaseMessage, RouteCaseMessageResult, RouteCaseRead } from '../domain/routeCases'
import type {
  FinalTestGradingStatus,
  FinalTestReleaseReceipt,
  LearningResult,
  LearningResultQuestion,
  LearningResultTutorThread,
  StudentFinalTest,
  StudentFinalTestQuestion,
  TeacherFinalTest,
  TeacherFinalTestReviewQueueFilters,
  TeacherFinalTestReviewQueuePage,
  TeacherFinalTestQuestion,
  TeacherLearningResult,
} from '../domain/finalTests'

const API_TTL = 10_000
type RouteDetailResponse = z.infer<typeof routeDetailSchema>
type ReadingResponse = z.infer<typeof readingStepSchema>
type CaseResponse = z.infer<typeof routeCaseSchema>
type StudentTestResponse = z.infer<typeof studentFinalTestSchema>
type TeacherTestResponse = z.infer<typeof teacherFinalTestSchema>
type ResultResponse = z.infer<typeof learningResultSchema>
const mapTestSummary = (v: RouteDetailResponse['test_summary']): LearningRouteTestSummary => ({
  id: v.id,
  title: v.title,
  questionCount: v.question_count,
  generationState: v.generation_state,
  reviewState: v.review_state,
  reviewKind: v.review_kind,
  canStart: v.can_start,
  lockReason: v.lock_reason || undefined,
  claimExpiresAt: v.claim_expires_at || undefined,
  retryAllowed: v.retry_allowed,
})
const mapRouteSummary = (v: RouteDetailResponse['summary']): LearningRouteSummary => ({
  id: v.id,
  title: v.title,
  sourceKind: v.source_kind,
  scopeStatus: v.scope_status,
  sessionLocator: v.session_locator,
  goalPointCodes: v.goal_point_codes,
  status: v.status,
  nextAction: v.next_action,
  progress: { completedSteps: v.progress.completed_steps, totalSteps: v.progress.total_steps },
  updatedAt: v.updated_at,
  testSummary: mapTestSummary(v.test_summary),
  resultId: v.result_id || undefined,
  generationState: v.generation_state,
  claimExpiresAt: v.claim_expires_at || undefined,
  retryAllowed: v.retry_allowed,
})
const mapStep = (v: RouteDetailResponse['steps'][number]): LearningRouteStep => ({
  id: v.id,
  position: v.position,
  kind: v.kind,
  title: v.title,
  goalPointCodes: v.goal_point_codes,
  status: v.status,
  caseId: v.case_id || undefined,
  completedAt: v.completed_at || undefined,
})
const mapRouteDetail = (v: RouteDetailResponse): LearningRouteDetail => ({
  summary: mapRouteSummary(v.summary),
  diagnosisSummary: v.diagnosis_summary,
  steps: v.steps.map(mapStep),
  testSummary: mapTestSummary(v.test_summary),
  canStartTest: v.can_start_test,
  lockReasons: v.lock_reasons,
  routeVersion: v.route_version,
})
const mapReading = (v: ReadingResponse): LearningRouteReading => ({
  routeId: v.route_id,
  step: mapStep(v),
  sources: v.sources.map((s) => ({
    id: String(s.source_id || ''),
    title: String(s.title || ''),
    institution: String(s.institution || s.publisher || ''),
    url: typeof s.url === 'string' ? s.url : undefined,
    version: typeof s.version === 'string' ? s.version : undefined,
    sourceType: typeof s.source_type === 'string' ? s.source_type : undefined,
  })),
  aiGuide: v.ai_guide,
  sections: v.sections.map((section) => ({ title: String(section.title || ''), text: String(section.text || '') })),
  learningPoints: v.learning_points,
  readingProgress: {
    leaseToken: v.reading_progress.lease_token || undefined,
    accumulatedSeconds: v.reading_progress.accumulated_seconds,
    lastSeenAt: v.reading_progress.last_seen_at || undefined,
  },
})
const mapGeneration = (v: z.infer<typeof learningRouteGenerationSchema>): LearningRouteGenerationReceipt => ({
  routeId: v.route_id,
  component: v.component,
  generationState: v.generation_state,
  claimExpiresAt: v.claim_expires_at || undefined,
})
const mapCaseMessage = (v: CaseResponse['messages'][number]): RouteCaseMessage => ({
  id: v.id,
  role: v.role,
  content: v.content,
  revision: v.revision,
  phase: v.phase,
})
const mapRouteCase = (v: CaseResponse): RouteCaseRead => ({
  id: v.id,
  routeId: v.route_id,
  stepId: v.step_id,
  syntheticCase: {
    title: v.synthetic_case.title,
    publicScenario: v.synthetic_case.public_scenario,
    caseFacts: v.synthetic_case.case_facts,
    targetPointCodes: v.synthetic_case.target_point_codes,
  },
  phase: v.phase,
  revision: v.revision,
  status: v.status,
  goals: v.goals.map((g) => ({ goalId: g.goal_id, objective: g.objective })),
  stages: v.stages.map((stage) => ({
    phase: stage.phase,
    goals: stage.goals.map((goal) => ({ goalId: goal.goal_id, objective: goal.objective })),
    prompt: stage.prompt,
  })),
  messages: v.messages.map(mapCaseMessage),
  nextPrompt: v.next_prompt,
  safetyNotice: v.safety_notice,
  pendingMessage: v.pending_message
    ? {
        clientMessageId: v.pending_message.client_message_id,
        requestRevision: v.pending_message.request_revision,
        processingState: v.pending_message.processing_state,
        retryAllowed: v.pending_message.retry_allowed,
        claimExpiresAt: v.pending_message.claim_expires_at || undefined,
      }
    : undefined,
})
const mapCaseResult = (v: z.infer<typeof routeCaseMessageResultSchema>): RouteCaseMessageResult => ({
  clientMessageId: v.client_message_id,
  requestRevision: v.request_revision,
  processingState: v.processing_state,
  retryAllowed: v.retry_allowed,
  reply: v.reply || undefined,
  phase: v.phase,
  revision: v.revision,
  decision: v.decision || undefined,
  missingElements: v.missing_elements,
  status: v.status,
})
const mapStudentQuestion = (v: StudentTestResponse['questions'][number]): StudentFinalTestQuestion => ({
  id: v.id,
  position: v.position,
  pointCode: v.point_code,
  prompt: v.prompt,
  questionType: v.question_type,
  options: v.options,
})
const mapAttempt = (v: z.infer<typeof attemptReadSchema> | null) =>
  v
    ? {
        id: v.id,
        status: v.status,
        version: v.version,
        answers: v.answers,
        savedAt: v.saved_at || undefined,
        submittedAt: v.submitted_at || undefined,
      }
    : null
const mapStudentTest = (v: StudentTestResponse): StudentFinalTest => ({
  id: v.id,
  title: v.title,
  reviewKind: v.review_kind,
  formatVersion: v.format_version,
  releasedVersion: v.released_version,
  releasedDigest: v.released_digest,
  questions: v.questions.map(mapStudentQuestion),
  attempt: mapAttempt(v.attempt),
})
const mapTeacherQuestion = (v: TeacherTestResponse['questions'][number]): TeacherFinalTestQuestion => {
  const fields = {
    id: v.id || null,
    position: v.position,
    prompt: v.prompt,
    primaryPointCode: v.primary_point_code,
    explanation: v.explanation,
    sourceDigest: v.source_digest,
  }
  if (v.question_type === 'short_answer')
    return {
      ...fields,
      questionType: 'short_answer',
      referenceAnswer: v.reference_answer || '',
      rubric: (v.rubric || []).map((item) => ({
        criterionId: item.criterion_id,
        description: item.description,
        maxPoints: item.max_points,
      })),
    }
  if (v.question_type === 'multiple_choice')
    return {
      ...fields,
      questionType: 'multiple_choice',
      options: v.options as [string, string, string, string],
      correctOptions: v.correct_options || [],
    }
  return {
    ...fields,
    questionType: 'single_choice',
    options: v.options as [string, string, string, string],
    correctOption: v.correct_option ?? 0,
  }
}
const mapTeacherTest = (v: TeacherTestResponse): TeacherFinalTest => ({
  id: v.id,
  routeId: v.route_id,
  title: v.title,
  sourceKind: v.source_kind,
  classId: v.class_id,
  sessionId: v.session_id,
  studentId: v.student_id,
  diagnosisSummary: v.diagnosis_summary,
  goalPointCodes: v.goal_point_codes,
  generationState: v.generation_state,
  reviewState: v.review_state,
  reviewKind: v.review_kind,
  currentScopeActive: v.current_scope_active,
  formatVersion: v.format_version,
  version: v.version,
  draftDigest: v.draft_digest,
  questions: v.questions.map(mapTeacherQuestion),
  releasedAt: v.released_at || undefined,
  feedbackDraft: v.feedback_draft,
})
const mapResultQuestion = (
  v: ResultResponse['questions'][number],
  pointsPossibleFallback: number,
): LearningResultQuestion => {
  const selectedOption = v.selected_option ?? undefined
  const correctOption = v.correct_option ?? undefined
  const pointsPossible = v.points_possible ?? (pointsPossibleFallback > 0 ? pointsPossibleFallback : undefined)
  return {
    ...mapStudentQuestion(v),
    selectedOption,
    correctOption,
    selectedOptions: v.selected_options ?? undefined,
    correctOptions: v.correct_options ?? undefined,
    selectedText: v.selected_text ?? undefined,
    referenceAnswer: v.reference_answer ?? undefined,
    rubricResults: v.rubric_results?.map((item) => ({
      criterionId: item.criterion_id,
      earnedPoints: item.earned_points,
      evidence: item.evidence,
    })),
    gradingFeedback: v.grading_feedback ?? undefined,
    pointsAwarded:
      v.points_awarded ??
      (pointsPossibleFallback > 0 && selectedOption !== undefined && correctOption !== undefined
        ? selectedOption === correctOption
          ? pointsPossible
          : 0
        : undefined),
    pointsPossible,
    explanation: v.explanation,
  }
}
const mapResult = (v: ResultResponse): LearningResult => ({
  id: v.id,
  routeId: v.route_id,
  sourceKind: v.source_kind,
  goalPointCodes: v.goal_point_codes,
  routeSummary: v.route_summary,
  correctCount: v.correct_count,
  questionCount: v.question_count,
  score: v.score,
  submittedAt: v.submitted_at,
  questions: v.questions.map((question) =>
    mapResultQuestion(question, v.format_version === 'single_choice_v1' ? 100 / v.question_count : 0),
  ),
  reviewKind: v.review_kind,
  formatVersion: v.format_version,
})
const mapTeacherResult = (v: z.infer<typeof teacherLearningResultReadSchema>): TeacherLearningResult => ({
  ...mapResult(v),
  studentId: v.student_id,
  classId: v.class_id,
  sessionId: v.session_id,
})
const mapTeacherReviewQueuePage = (
  v: z.infer<typeof teacherFinalTestReviewQueueSchema>,
): TeacherFinalTestReviewQueuePage => ({
  items: v.items.map((item) => ({
    id: item.id,
    routeId: item.route_id,
    title: item.title,
    classId: item.class_id,
    className: item.class_name,
    sessionId: item.session_id,
    studentId: item.student_id,
    studentName: item.student_name,
    generationState: item.generation_state,
    reviewState: item.review_state,
    updatedAt: item.updated_at,
    canReview: item.can_review,
    canRetry: item.can_retry,
    actionReason: item.action_reason,
  })),
  counts: {
    pendingReview: v.counts.pending_review,
    needsChanges: v.counts.needs_changes,
    generationFailed: v.counts.generation_failed,
  },
  total: v.total,
  limit: v.limit,
  offset: v.offset,
  asOf: v.as_of,
})
const mapGradingStatus = (v: z.infer<typeof finalTestGradingStatusSchema>): FinalTestGradingStatus => ({
  status: v.status,
  testId: v.test_id,
  routeId: v.route_id,
  resultId: v.result_id || undefined,
  retryAllowed: v.retry_allowed,
  errorCode: v.error_code || undefined,
})
const mapTutorThread = (v: z.infer<typeof learningResultTutorSchema>): LearningResultTutorThread => ({
  resultId: v.result_id,
  revision: v.revision,
  processingState: v.processing_state,
  pendingMessageId: v.pending_message_id || undefined,
  messages: v.messages.map((message) => ({
    id: message.id,
    role: message.role,
    questionId: message.question_id,
    content: message.content,
    sequence: message.sequence,
    createdAt: message.created_at,
  })),
})

export const apiLearningRoutes: LearningRoutesPort = {
  async getLearningRoutes(status = 'active', limit = 20, offset = 0) {
    const v = await apiRequest({
      path: '/learning/routes',
      query: { status, limit, offset },
      cacheTtlMs: API_TTL,
      schema: routePageSchema,
    })
    return { ...v, items: v.items.map(mapRouteSummary) }
  },
  async getLearningRoute(routeId) {
    return mapRouteDetail(
      await apiRequest({
        path: `/learning/routes/${encodePathSegment(routeId)}`,
        cacheTtlMs: API_TTL,
        schema: routeDetailSchema,
      }),
    )
  },
  async retryLearningRouteGeneration(routeId, component, clientRequestId) {
    return mapGeneration(
      await apiRequest({
        path: `/learning/routes/${encodePathSegment(routeId)}/retry-generation`,
        method: 'POST',
        body: { component, client_request_id: clientRequestId },
        schema: learningRouteGenerationSchema,
      }),
    )
  },
  async getLearningRouteStep(stepId) {
    return mapReading(
      await apiRequest({
        path: `/learning/route-steps/${encodePathSegment(stepId)}`,
        cacheTtlMs: API_TTL,
        schema: readingStepSchema,
      }),
    )
  },
  async saveRouteReadingProgress(stepId, action, clientRequestId, leaseToken) {
    const v = await apiRequest({
      path: `/learning/route-steps/${encodePathSegment(stepId)}/reading-progress`,
      method: 'POST',
      body: { action, lease_token: leaseToken, client_request_id: clientRequestId },
      schema: routeReadingProgressSchema,
      invalidateCache: [`/learning/route-steps/${stepId}`],
    })
    return {
      leaseToken: v.lease_token || undefined,
      accumulatedSeconds: v.accumulated_seconds,
      lastSeenAt: v.last_seen_at || undefined,
    }
  },
  async completeRouteReading(stepId, clientRequestId) {
    const v = await apiRequest({
      path: `/learning/route-steps/${encodePathSegment(stepId)}/complete-reading`,
      method: 'POST',
      body: { client_request_id: clientRequestId },
      schema: routeDetailSchema,
      invalidateCache: ['/learning/routes', `/learning/route-steps/${stepId}`],
    })
    return mapRouteDetail(v)
  },
  async getRouteCase(caseId) {
    return mapRouteCase(
      await apiRequest({
        path: `/learning/route-cases/${encodePathSegment(caseId)}`,
        cacheTtlMs: API_TTL,
        schema: routeCaseSchema,
      }),
    )
  },
  async sendRouteCaseMessage(caseId, content, clientMessageId, expectedRevision) {
    const v = await apiRequest({
      path: `/learning/route-cases/${encodePathSegment(caseId)}/messages`,
      method: 'POST',
      body: { content, client_message_id: clientMessageId, expected_revision: expectedRevision },
      schema: routeCaseMessageResultSchema,
      invalidateCache: [`/learning/route-cases/${caseId}`, '/learning/routes'],
    })
    return mapCaseResult(v)
  },
  async startFinalTest(testId, clientRequestId) {
    const v = await apiRequest({
      path: `/learning/final-tests/${encodePathSegment(testId)}/start`,
      method: 'POST',
      body: { client_request_id: clientRequestId },
      schema: studentFinalTestSchema,
      invalidateCache: [`/learning/final-tests/${testId}`],
    })
    return mapStudentTest(v)
  },
  async getFinalTest(routeId) {
    return mapStudentTest(
      await apiRequest({
        path: `/learning/routes/${encodePathSegment(routeId)}/final-test`,
        cacheTtlMs: API_TTL,
        schema: studentFinalTestSchema,
      }),
    )
  },
  async saveFinalTestDraft(testId, clientRequestId, expectedVersion, releasedDigest, answers) {
    const v = await apiRequest({
      path: `/learning/final-tests/${encodePathSegment(testId)}/draft`,
      method: 'PUT',
      body: {
        client_request_id: clientRequestId,
        expected_version: expectedVersion,
        released_digest: releasedDigest,
        answers,
      },
      schema: attemptReadSchema,
      invalidateCache: [`/learning/routes/`, `/learning/final-tests/${testId}`],
    })
    return mapAttempt(v)!
  },
  async submitFinalTest(testId, clientSubmissionId, expectedVersion, releasedDigest, answers) {
    const v = await apiRequest({
      path: `/learning/final-tests/${encodePathSegment(testId)}/submit`,
      method: 'POST',
      body: {
        client_submission_id: clientSubmissionId,
        expected_version: expectedVersion,
        released_digest: releasedDigest,
        answers,
      },
      schema: finalTestSubmissionSchema,
      invalidateCache: ['/learning/routes', `/learning/routes/`, `/learning/final-tests/${testId}`],
    })
    return 'status' in v ? mapGradingStatus(v) : mapResult(v)
  },
  async getFinalTestGrading(testId) {
    return mapGradingStatus(
      await apiRequest({
        path: `/learning/final-tests/${encodePathSegment(testId)}/grading`,
        cacheTtlMs: 0,
        schema: finalTestGradingStatusSchema,
      }),
    )
  },
  async retryFinalTestGrading(testId, clientRequestId) {
    return mapGradingStatus(
      await apiRequest({
        path: `/learning/final-tests/${encodePathSegment(testId)}/retry-grading`,
        method: 'POST',
        body: { client_request_id: clientRequestId },
        schema: finalTestGradingStatusSchema,
        invalidateCache: ['/learning/routes', `/learning/final-tests/${testId}`],
      }),
    )
  },
  async getLearningRouteResult(routeId) {
    return mapResult(
      await apiRequest({
        path: `/learning/routes/${encodePathSegment(routeId)}/result`,
        cacheTtlMs: API_TTL,
        schema: learningResultSchema,
      }),
    )
  },
  async getLearningResultTutor(resultId) {
    return mapTutorThread(
      await apiRequest({
        path: `/learning/results/${encodePathSegment(resultId)}/tutor`,
        cacheTtlMs: 0,
        schema: learningResultTutorSchema,
      }),
    )
  },
  async sendLearningResultTutorMessage(resultId, clientMessageId, questionId, expectedRevision, content) {
    return mapTutorThread(
      await apiRequest({
        path: `/learning/results/${encodePathSegment(resultId)}/tutor/messages`,
        method: 'POST',
        body: {
          client_message_id: clientMessageId,
          question_id: questionId,
          expected_revision: expectedRevision,
          content,
        },
        schema: learningResultTutorSchema,
        invalidateCache: [`/learning/results/${resultId}/tutor`],
      }),
    )
  },
  async getTeacherFinalTestReviewQueue(filters: TeacherFinalTestReviewQueueFilters = {}) {
    return mapTeacherReviewQueuePage(
      await apiRequest({
        path: '/learning/teacher/final-test-review-queue',
        query: {
          class_id: filters.classId,
          session_id: filters.sessionId,
          kind: filters.kind,
          limit: filters.limit ?? 20,
          offset: filters.offset ?? 0,
        },
        cacheTtlMs: 0,
        schema: teacherFinalTestReviewQueueSchema,
      }),
    )
  },
  async getTeacherFinalTest(testId) {
    return mapTeacherTest(
      await apiRequest({
        path: `/learning/teacher/final-tests/${encodePathSegment(testId)}`,
        cacheTtlMs: API_TTL,
        schema: teacherFinalTestSchema,
      }),
    )
  },
  async saveTeacherFinalTest(testId, clientRequestId, expectedVersion, questions, feedbackDraft) {
    const body = {
      client_request_id: clientRequestId,
      expected_version: expectedVersion,
      feedback_draft: feedbackDraft,
      questions: questions.map((q) => ({
        id: q.id,
        position: q.position,
        primary_point_code: q.primaryPointCode,
        prompt: q.prompt,
        question_type: q.questionType,
        options: q.questionType === 'short_answer' ? [] : q.options,
        correct_option: q.questionType === 'single_choice' ? q.correctOption : null,
        correct_options: q.questionType === 'multiple_choice' ? q.correctOptions : null,
        reference_answer: q.questionType === 'short_answer' ? q.referenceAnswer : null,
        rubric:
          q.questionType === 'short_answer'
            ? q.rubric.map((item) => ({
                criterion_id: item.criterionId,
                description: item.description,
                max_points: item.maxPoints,
              }))
            : null,
        explanation: q.explanation,
      })),
    }
    return mapTeacherTest(
      await apiRequest({
        path: `/learning/teacher/final-tests/${encodePathSegment(testId)}`,
        method: 'PUT',
        body,
        schema: teacherFinalTestSchema,
        invalidateCache: ['/learning/teacher/final-tests', '/learning/teacher/final-test-review-queue'],
      }),
    )
  },
  async requestTeacherTestChanges(testId, clientRequestId, expectedVersion, note) {
    return mapTeacherTest(
      await apiRequest({
        path: `/learning/teacher/final-tests/${encodePathSegment(testId)}/request-changes`,
        method: 'POST',
        body: { client_request_id: clientRequestId, expected_version: expectedVersion, note },
        schema: teacherFinalTestSchema,
        invalidateCache: ['/learning/teacher/final-tests', '/learning/teacher/final-test-review-queue'],
      }),
    )
  },
  async retryTeacherTestGeneration(testId, clientRequestId) {
    return mapGeneration(
      await apiRequest({
        path: `/learning/teacher/final-tests/${encodePathSegment(testId)}/retry-generation`,
        method: 'POST',
        body: { client_request_id: clientRequestId },
        schema: learningRouteGenerationSchema,
        invalidateCache: ['/learning/teacher/final-tests', '/learning/teacher/final-test-review-queue'],
      }),
    )
  },
  async releaseTeacherFinalTest(testId, clientRequestId, expectedVersion, draftDigest, feedback) {
    const v = await apiRequest({
      path: `/learning/teacher/final-tests/${encodePathSegment(testId)}/release`,
      method: 'POST',
      body: {
        client_request_id: clientRequestId,
        expected_version: expectedVersion,
        draft_digest: draftDigest,
        feedback,
      },
      schema: finalTestReleaseSchema,
      invalidateCache: [
        '/learning/teacher/final-tests',
        '/learning/teacher/final-test-review-queue',
        '/learning/teacher/route-results',
      ],
    })
    const receipt: FinalTestReleaseReceipt = {
      testId: v.test_id,
      releasedVersion: v.released_version,
      releasedDigest: v.released_digest,
      releasedAt: v.released_at,
    }
    return receipt
  },
  async getTeacherRouteResult(resultId) {
    return mapTeacherResult(
      await apiRequest({
        path: `/learning/teacher/route-results/${encodePathSegment(resultId)}`,
        cacheTtlMs: API_TTL,
        schema: teacherLearningResultReadSchema,
      }),
    )
  },
}
