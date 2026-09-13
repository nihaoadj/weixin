import { z } from 'zod'
import { apiRequest } from '@/platform/http/apiClient'
import type {
  PblDiagnostic,
  PblRepository,
  PblSession,
  PblSuggestion,
  PblSession as SessionType,
  PblTargets,
  PblFilters,
  InteractionStyle,
  LearningDialogueSubmission,
  PblTeacherFeedback,
  PblWorkItem,
  TeacherPblSession,
  TeacherPblDashboard,
  PblFollowUp,
  PblFollowUpStatus,
  PblPlan,
} from '../domain/ports'
import { mapLearningReport, mapReportPage, reportDetailSchema, reportPageSchema } from './reportContract'
const session = z.object({
  id: z.number(),
  class_id: z.number().nullable(),
  topic_code: z.string(),
  status: z.string(),
  created_at: z.string(),
  closed_at: z.string().nullable(),
  case_id: z.number().nullable(),
  case_version: z.number().nullable(),
  case_context: z
    .object({
      title: z.string(),
      opening: z.object({ setting: z.string(), patient_intro: z.string(), chief_complaint: z.string() }).optional(),
    })
    .nullable(),
  goal_point_codes: z.array(z.string()),
  phase: z.enum(['problem_framing', 'hypothesis', 'evidence', 'synthesis']),
  student_phase: z.enum(['problem_framing', 'hypothesis', 'evidence', 'synthesis', 'completed']).nullable().optional(),
  phase_status: z.enum(['active', 'completed']).nullable().optional(),
  phase_counts: z.record(z.string(), z.number()).nullable().optional(),
  version: z.number(),
  session_kind: z.enum(['classroom', 'student_initiated']).default('classroom'),
  interaction_style: z.enum(['guided', 'direct']).nullable().optional(),
  style_selected_at: z.string().nullable().optional(),
})
const suggestion = z.object({
  id: z.number(),
  title: z.string(),
  prompt: z.string(),
  linked_findings: z.array(z.string()),
  status: z.string(),
  version: z.number(),
  problem_id: z.number().nullable().optional(),
})
const finding = {
  id: z.string(),
  summary: z.string(),
  evidence_message_ids: z.array(z.string()),
  evidence_summary: z.string(),
}
const diagnostic = z.object({
  id: z.number(),
  diagnostic_status: z.string(),
  assistant_reply: z.string(),
  follow_up_question: z.string().nullable().optional(),
  knowledge_gaps: z.array(
    z.object({ ...finding, point_code: z.string(), confidence: z.enum(['low', 'medium', 'high']) }),
  ),
  reasoning_issues: z.array(
    z.object({ ...finding, dimension_id: z.string(), issue_type: z.string(), improvement: z.string() }),
  ),
  schema_version: z.number(),
  revision: z.number(),
  safety_notice: z.string(),
  created_at: z.string().nullable(),
  student_id: z.number().optional(),
  student_name: z.string().optional(),
  class_id: z.number().optional(),
  class_name: z.string().optional(),
  session_id: z.number().optional(),
  topic_code: z.string().optional(),
  recommended_questions: z.array(suggestion).optional(),
  phase: z.enum(['problem_framing', 'hypothesis', 'evidence', 'synthesis']).nullable().optional(),
  phase_decision: z.enum(['continue', 'advance', 'complete', 'unavailable']).nullable().optional(),
  phase_evidence_summary: z.string(),
  phase_missing_elements: z.array(z.string()),
  session_kind: z.enum(['classroom', 'student_initiated']).optional(),
  interaction_style: z.enum(['guided', 'direct']).optional(),
})
const toSession = (v: z.infer<typeof session>): PblSession => ({
  id: String(v.id),
  classId: v.class_id == null ? undefined : String(v.class_id),
  topicCode: v.topic_code,
  status: v.status,
  createdAt: v.created_at,
  closedAt: v.closed_at || undefined,
  caseId: v.case_id == null ? undefined : String(v.case_id),
  caseVersion: v.case_version ?? undefined,
  caseContext: v.case_context ?? undefined,
  goalPointCodes: v.goal_point_codes,
  phase: v.phase,
  studentPhase: v.student_phase ?? undefined,
  phaseStatus: v.phase_status ?? undefined,
  phaseCounts: v.phase_counts ?? undefined,
  version: v.version,
  sessionKind: v.session_kind,
  interactionStyle: v.interaction_style ?? undefined,
  styleSelectedAt: v.style_selected_at ?? undefined,
})
const toSuggestion = (v: z.infer<typeof suggestion>): PblSuggestion => ({
  id: String(v.id),
  title: v.title,
  prompt: v.prompt,
  linkedFindings: v.linked_findings,
  status: v.status,
  version: v.version,
  problemId: v.problem_id == null ? undefined : String(v.problem_id),
})
const teacherFeedback = z.object({
  id: z.number(),
  snapshot_id: z.number(),
  plan_id: z.number().nullable(),
  action_type: z.string(),
  body: z.string(),
  created_at: z.string().nullable(),
})
const workItem = z.object({
  snapshot_id: z.number(),
  session_id: z.number(),
  source: z.enum(['student_submission', 'classroom_diagnostic']),
  status: z.enum(['pending', 'responded', 'task_published', 'closed']),
  student: z.object({ id: z.number(), name: z.string() }),
  class: z.object({ id: z.number(), name: z.string() }),
  topic: z.string(),
  entered_at: z.string().nullable(),
  last_activity_at: z.string().nullable(),
  knowledge_gap_count: z.number(),
  reasoning_issue_count: z.number(),
  next_action: z.string(),
})
const toFeedback = (value: z.infer<typeof teacherFeedback>): PblTeacherFeedback => ({
  id: String(value.id),
  snapshotId: String(value.snapshot_id),
  planId: value.plan_id == null ? undefined : String(value.plan_id),
  actionType: value.action_type,
  body: value.body,
  createdAt: value.created_at ?? undefined,
})
const toWorkItem = (value: z.infer<typeof workItem>): PblWorkItem => ({
  snapshotId: String(value.snapshot_id),
  sessionId: String(value.session_id),
  source: value.source,
  status: value.status,
  student: { id: String(value.student.id), name: value.student.name },
  class: { id: String(value.class.id), name: value.class.name },
  topic: value.topic,
  enteredAt: value.entered_at ?? undefined,
  lastActivityAt: value.last_activity_at ?? undefined,
  knowledgeGapCount: value.knowledge_gap_count,
  reasoningIssueCount: value.reasoning_issue_count,
  nextAction: value.next_action,
})
const toDiagnostic = (v: z.infer<typeof diagnostic>): PblDiagnostic => ({
  id: String(v.id),
  diagnosticStatus: v.diagnostic_status,
  assistantReply: v.assistant_reply,
  followUpQuestion: v.follow_up_question || undefined,
  knowledgeGaps: v.knowledge_gaps,
  reasoningIssues: v.reasoning_issues,
  recommendedQuestions: v.recommended_questions?.map(toSuggestion),
  schemaVersion: v.schema_version,
  revision: v.revision,
  safetyNotice: v.safety_notice,
  createdAt: v.created_at ?? undefined,
  studentId: v.student_id == null ? undefined : String(v.student_id),
  studentName: v.student_name,
  classId: v.class_id == null ? undefined : String(v.class_id),
  className: v.class_name,
  sessionId: v.session_id == null ? undefined : String(v.session_id),
  topicCode: v.topic_code,
  phase: v.phase ?? undefined,
  phaseDecision: v.phase_decision ?? undefined,
  phaseEvidenceSummary: v.phase_evidence_summary,
  phaseMissingElements: v.phase_missing_elements,
  sessionKind: v.session_kind,
  interactionStyle: v.interaction_style,
})
const messageSchema = z.object({
  id: z.string(),
  sequence: z.number(),
  role: z.string(),
  content: z.string(),
  processing_status: z.string(),
  client_message_id: z.string().nullable().optional(),
})
const participationSchema = z.object({
  messages: z.array(messageSchema),
  diagnostic: diagnostic.nullable(),
  current_phase: z.enum(['problem_framing', 'hypothesis', 'evidence', 'synthesis', 'completed']),
  phase_started_revision: z.number(),
  phase_status: z.enum(['active', 'completed']),
  phase_completed_at: z.string().nullable(),
  interaction_style: z.enum(['guided', 'direct']),
  style_selected_at: z.string().nullable(),
})
const toParticipation = (value: z.infer<typeof participationSchema>) => ({
  messages: value.messages,
  diagnostic: value.diagnostic ? toDiagnostic(value.diagnostic) : undefined,
  currentPhase: value.current_phase,
  phaseStartedRevision: value.phase_started_revision,
  phaseStatus: value.phase_status,
  phaseCompletedAt: value.phase_completed_at ?? undefined,
  interactionStyle: value.interaction_style,
  styleSelectedAt: value.style_selected_at ?? undefined,
})
const dialogueDetailSchema = z.object({ session, participation: participationSchema.nullable() })
const submissionSchema = z.object({
  session_id: z.number(),
  snapshot_id: z.number(),
  knowledge_gaps: z.array(
    z.object({ ...finding, point_code: z.string(), confidence: z.enum(['low', 'medium', 'high']) }),
  ),
  reasoning_issues: z.array(
    z.object({ ...finding, dimension_id: z.string(), issue_type: z.string(), improvement: z.string() }),
  ),
  evidence_summary: z.string(),
  questions: z.array(z.object({ id: z.number(), title: z.string(), prompt: z.string() })),
  submission: z
    .object({
      session_id: z.number(),
      snapshot_id: z.number(),
      class_id: z.number(),
      source: z.string(),
      submitted_at: z.string().nullable(),
    })
    .nullable(),
  teacher_status: z.enum(['pending', 'responded', 'task_published', 'closed']).nullable().optional(),
  feedbacks: z
    .array(
      z.object({
        id: z.number(),
        action_type: z.string(),
        body: z.string(),
        created_at: z.string().nullable(),
        plan_id: z.number().nullable(),
      }),
    )
    .optional(),
  next_action: z.string().optional(),
})
const toSubmission = (value: z.infer<typeof submissionSchema>): LearningDialogueSubmission => ({
  sessionId: String(value.session_id),
  snapshotId: String(value.snapshot_id),
  knowledgeGaps: value.knowledge_gaps,
  reasoningIssues: value.reasoning_issues,
  evidenceSummary: value.evidence_summary,
  questions: value.questions.map((item) => ({ id: String(item.id), title: item.title, prompt: item.prompt })),
  submission: value.submission
    ? {
        sessionId: String(value.submission.session_id),
        snapshotId: String(value.submission.snapshot_id),
        classId: String(value.submission.class_id),
        source: value.submission.source,
        submittedAt: value.submission.submitted_at || undefined,
      }
    : undefined,
  teacherStatus: value.teacher_status ?? undefined,
  feedbacks: value.feedbacks?.map((item) => ({
    id: String(item.id),
    actionType: item.action_type,
    body: item.body,
    createdAt: item.created_at ?? undefined,
    planId: item.plan_id == null ? undefined : String(item.plan_id),
  })),
  nextAction: value.next_action,
})
const plan = z.object({
  id: z.number(),
  student_id: z.number(),
  source_type: z.literal('pbl_suggestion'),
  source_id: z.number(),
  source_context: z.object({
    teacher_id: z.number(),
    class_id: z.number(),
    class_name: z.string(),
    session_id: z.number(),
    snapshot_id: z.number(),
    suggestion_id: z.number(),
    point_codes: z.array(z.string()),
    dimension_ids: z.array(z.string()),
    topic_code: z.string(),
  }),
  status: z.string(),
  verification_status: z.enum(['not_ready', 'pending_teacher', 'improved', 'needs_reinforcement']),
  verification_note: z.string(),
  verified_at: z.string().nullable(),
  version: z.number(),
  due_at: z.string(),
  current_cycle: z.number(),
  max_cycles: z.number(),
  automation_exhausted: z.boolean(),
  decision_policy_version: z.string(),
  decision_basis: z.record(z.string(), z.unknown()),
  evaluated_at: z.string().nullable(),
  tasks: z.array(
    z.object({
      id: z.number(),
      position: z.number(),
      task_type: z.enum(['discussion', 'knowledge_review', 'retest', 'micro_drill', 'focused_retry']),
      status: z.string(),
      problem_id: z.number().nullable(),
      cycle_number: z.number(),
      target_type: z.string(),
      target_code: z.string(),
      variant_code: z.string(),
      public_definition: z.object({
        prompt: z.string(),
        options: z.array(z.string()).optional(),
        point_code: z.string().optional(),
        card_code: z.string().optional(),
        target_label: z.string().optional(),
        reference: z.string().optional(),
      }),
      result: z
        .object({
          score: z.number().nullable(),
          feedback: z.string(),
          evidence: z.array(z.string()),
          answer: z.object({
            text: z.string().optional(),
            selected_option: z.number().optional(),
            dimension_scores: z.record(z.string(), z.number()).optional(),
          }),
          submitted_at: z.string().nullable(),
        })
        .nullable(),
    }),
  ),
})
const summary = z.object({
  participants: z.number(),
  diagnoses: z.number(),
  published_suggestions: z.number(),
  plans: z.number(),
  tasks: z.number(),
  completed_tasks: z.number(),
  pending_verification: z.number(),
  improved: z.number(),
  needs_reinforcement: z.number(),
  objective_retest_count: z.number(),
  objective_retest_average: z.number().nullable(),
  phase_counts: z.record(z.string(), z.number()),
  automation_exhausted: z.number(),
})
export class ApiPblRepository implements PblRepository {
  async classes() {
    const values = await apiRequest({
      path: '/student/classes',
      schema: z.array(z.object({ id: z.number(), name: z.string(), code: z.string() })),
    })
    return values.map((item) => ({ id: String(item.id), name: item.name, code: item.code }))
  }
  async dialogues(limit = 20, offset = 0) {
    const value = await apiRequest({
      path: '/student/learning-dialogues',
      query: { limit, offset },
      schema: z.object({ items: z.array(session), total: z.number(), limit: z.number(), offset: z.number() }),
    })
    return { ...value, items: value.items.map(toSession) }
  }
  async dialogue(id: string) {
    const value = await apiRequest({ path: `/student/learning-dialogues/${id}`, schema: dialogueDetailSchema })
    return {
      session: toSession(value.session),
      participation: value.participation ? toParticipation(value.participation) : undefined,
    }
  }
  async createDialogue(input: {
    clientSessionId: string
    classId?: string
    interactionStyle: InteractionStyle
    goalPointCodes: string[]
  }) {
    const value = await apiRequest({
      path: '/student/learning-dialogues',
      method: 'POST',
      body: {
        client_session_id: input.clientSessionId,
        class_id: input.classId ? Number(input.classId) : null,
        interaction_style: input.interactionStyle,
        goal_point_codes: input.goalPointCodes,
      },
      schema: dialogueDetailSchema,
    })
    return {
      session: toSession(value.session),
      participation: value.participation ? toParticipation(value.participation) : undefined,
    }
  }
  async startDialogue(id: string, interactionStyle: InteractionStyle) {
    const value = await apiRequest({
      path: `/student/learning-dialogues/${id}/start`,
      method: 'POST',
      body: { interaction_style: interactionStyle },
      schema: dialogueDetailSchema,
    })
    return {
      session: toSession(value.session),
      participation: value.participation ? toParticipation(value.participation) : undefined,
    }
  }
  async active() {
    return (await apiRequest({ path: '/student/pbl-sessions', schema: z.array(session) })).map(toSession)
  }
  async sessions(classId: string) {
    return (await apiRequest({ path: `/classes/${classId}/pbl-sessions`, schema: z.array(session) })).map(toSession)
  }
  async createSession(classId: string, topicCode: string, caseId: string, goals: string[]) {
    return toSession(
      await apiRequest({
        path: `/classes/${classId}/pbl-sessions`,
        method: 'POST',
        body: { topic_code: topicCode, case_id: Number(caseId), goal_point_codes: goals },
        schema: session,
      }),
    )
  }
  async closeSession(classId: string, id: string) {
    return toSession(
      await apiRequest({ path: `/classes/${classId}/pbl-sessions/${id}/close`, method: 'POST', schema: session }),
    )
  }
  async participation(id: string) {
    const value = await apiRequest({
      path: `/student/pbl-sessions/${id}/participation`,
      schema: participationSchema,
    })
    return toParticipation(value)
  }
  async message(id: string, content: string, clientMessageId: string) {
    const value = await apiRequest({
      path: `/student/learning-dialogues/${id}/messages`,
      timeoutMs: 35000,
      method: 'POST',
      body: { content, client_message_id: clientMessageId },
      schema: z.object({
        diagnostic,
        messages: z.array(messageSchema),
        current_phase: z.enum(['problem_framing', 'hypothesis', 'evidence', 'synthesis', 'completed']),
        phase_status: z.enum(['active', 'completed']),
        phase_completed_at: z.string().nullable(),
        interaction_style: z.enum(['guided', 'direct']),
        style_selected_at: z.string().nullable(),
      }),
    })
    return {
      messages: value.messages,
      diagnostic: toDiagnostic(value.diagnostic),
      currentPhase: value.current_phase,
      phaseStartedRevision: value.diagnostic.revision,
      phaseStatus: value.phase_status,
      phaseCompletedAt: value.phase_completed_at ?? undefined,
      interactionStyle: value.interaction_style,
      styleSelectedAt: value.style_selected_at ?? undefined,
    }
  }
  async dialogueSubmission(id: string) {
    return toSubmission(
      await apiRequest({ path: `/student/learning-dialogues/${id}/submission`, schema: submissionSchema }),
    )
  }
  async submitDialogue(input: { id: string; snapshotId: string; classId: string; clientSubmissionId: string }) {
    return toSubmission(
      await apiRequest({
        path: `/student/learning-dialogues/${input.id}/submission`,
        method: 'POST',
        body: {
          snapshot_id: Number(input.snapshotId),
          class_id: Number(input.classId),
          client_submission_id: input.clientSubmissionId,
        },
        schema: submissionSchema,
        invalidateCache: ['/teacher/pbl-diagnostics'],
      }),
    )
  }
  async diagnostics(filters: PblFilters = {}) {
    const value = await apiRequest({
      path: '/teacher/pbl-diagnostics',
      query: {
        class_id: filters.classId,
        session_id: filters.sessionId,
        student_id: filters.studentId,
        status: filters.status,
        offset: filters.offset ?? 0,
        limit: 20,
      },
      schema: z.object({ items: z.array(diagnostic), total: z.number(), limit: z.number(), offset: z.number() }),
    })
    return { items: value.items.map(toDiagnostic), total: value.total }
  }
  async workItems(filters: PblFilters & { source?: PblWorkItem['source']; workStatus?: PblWorkItem['status'] } = {}) {
    const value = await apiRequest({
      path: '/teacher/pbl-work-items',
      query: {
        class_id: filters.classId,
        session_id: filters.sessionId,
        student_id: filters.studentId,
        source: filters.source,
        status: filters.workStatus,
        offset: filters.offset ?? 0,
        limit: 20,
      },
      schema: z.object({
        items: z.array(workItem),
        total: z.number(),
        limit: z.number(),
        offset: z.number(),
        summary: z.object({
          pending: z.number(),
          responded: z.number(),
          task_published: z.number(),
          closed: z.number(),
        }),
      }),
    })
    return { items: value.items.map(toWorkItem), total: value.total, summary: value.summary }
  }
  async workItem(snapshotId: string) {
    const value = await apiRequest({
      path: `/teacher/pbl-work-items/${snapshotId}`,
      schema: z.object({ work_item: workItem.nullable(), diagnostic, feedbacks: z.array(teacherFeedback) }),
    })
    return {
      workItem: value.work_item ? toWorkItem(value.work_item) : undefined,
      diagnostic: toDiagnostic(value.diagnostic),
      feedbacks: value.feedbacks.map(toFeedback),
    }
  }
  async feedback(input: {
    snapshotId: string
    clientFeedbackId: string
    body: string
    actionType: 'feedback_only' | 'task_published' | 'closed'
    suggestion?: PblSuggestion
    targets?: PblTargets
  }) {
    return toFeedback(
      await apiRequest({
        path: `/teacher/pbl-work-items/${input.snapshotId}/feedback`,
        method: 'POST',
        body: {
          client_feedback_id: input.clientFeedbackId,
          body: input.body,
          action_type: input.actionType,
          suggestion_id: input.suggestion ? Number(input.suggestion.id) : undefined,
          suggestion_version: input.suggestion?.version,
          title: input.suggestion?.title ?? '',
          prompt: input.suggestion?.prompt ?? '',
          target_student_ids: input.targets?.studentIds ?? [],
          whole_class: input.targets?.wholeClass ?? false,
          include_case_retry: input.targets?.includeCaseRetry ?? false,
        },
        schema: teacherFeedback,
      }),
    )
  }
  async diagnostic(id: string) {
    return toDiagnostic(await apiRequest({ path: `/teacher/pbl-diagnostics/${id}`, schema: diagnostic }))
  }
  async editSuggestion(item: PblSuggestion, reject = false) {
    return toSuggestion(
      await apiRequest({
        path: `/teacher/pbl-question-suggestions/${item.id}`,
        method: 'PATCH',
        body: { version: item.version, title: item.title, prompt: item.prompt, reject },
        schema: suggestion,
      }),
    )
  }
  async adopt(item: PblSuggestion, targets: PblTargets = {}) {
    return toSuggestion(
      await apiRequest({
        path: `/teacher/pbl-question-suggestions/${item.id}/adopt-and-publish`,
        method: 'POST',
        body: {
          version: item.version,
          title: item.title,
          prompt: item.prompt,
          target_student_ids: targets.studentIds ?? [],
          whole_class: targets.wholeClass ?? false,
          include_case_retry: targets.includeCaseRetry ?? false,
        },
        schema: suggestion,
      }),
    )
  }
  async revisions(id: string) {
    return (await apiRequest({ path: `/teacher/pbl-diagnostics/${id}/revisions`, schema: z.array(diagnostic) })).map(
      toDiagnostic,
    )
  }
  async plans() {
    return apiRequest({ path: '/student/pbl-learning-plans', schema: z.array(plan) })
  }
  async reports(limit = 20, offset = 0) {
    return mapReportPage(
      await apiRequest({ path: '/student/pbl-learning-reports', query: { limit, offset }, schema: reportPageSchema }),
    )
  }
  async report(sessionId: string) {
    return mapLearningReport(
      await apiRequest({ path: `/student/pbl-learning-reports/${sessionId}`, schema: reportDetailSchema }),
    )
  }
  async results(sessionId?: string) {
    return apiRequest({
      path: '/teacher/pbl-learning-results',
      query: { session_id: sessionId },
      schema: z.array(plan),
    })
  }
  async teacherSessions(filters: { classId?: string; status?: string; offset?: number } = {}) {
    const value = await apiRequest({
      path: '/teacher/pbl-sessions',
      query: { class_id: filters.classId, status: filters.status, offset: filters.offset ?? 0, limit: 20 },
      schema: z.object({
        items: z.array(
          z.object({
            id: z.number(),
            class_id: z.number(),
            class_name: z.string(),
            topic_code: z.string(),
            status: z.string(),
            created_at: z.string(),
            closed_at: z.string().nullable(),
          }),
        ),
        total: z.number(),
        limit: z.number(),
        offset: z.number(),
      }),
    })
    return {
      items: value.items.map((item): TeacherPblSession => ({
        id: String(item.id),
        classId: String(item.class_id),
        className: item.class_name,
        topicCode: item.topic_code,
        status: item.status,
        createdAt: item.created_at,
        closedAt: item.closed_at ?? undefined,
      })),
      total: value.total,
    }
  }
  async dashboard(classId: string, sessionId: string) {
    const value = await apiRequest({
      path: `/classes/${classId}/pbl-sessions/${sessionId}/dashboard`,
      schema: z.object({
        session: z.object({ id: z.number(), class_id: z.number(), status: z.string() }),
        summary,
        students: z.array(
          z.object({
            student_id: z.number(),
            student_name: z.string(),
            current_phase: z.string(),
            phase_status: z.string(),
            snapshot_id: z.number().nullable(),
            work_item_status: z.enum(['pending', 'responded', 'task_published', 'closed']).nullable(),
            task_progress: z.object({ completed: z.number(), total: z.number() }),
            current_cycle: z.number().nullable(),
            verification_status: z.string().nullable(),
          }),
        ),
      }),
    })
    return {
      session: { id: String(value.session.id), classId: String(value.session.class_id), status: value.session.status },
      summary: value.summary as TeacherPblDashboard['summary'],
      students: value.students.map((item) => ({
        studentId: String(item.student_id),
        studentName: item.student_name,
        currentPhase: item.current_phase,
        phaseStatus: item.phase_status,
        snapshotId: item.snapshot_id == null ? undefined : String(item.snapshot_id),
        workItemStatus: item.work_item_status ?? undefined,
        taskProgress: item.task_progress,
        currentCycle: item.current_cycle ?? undefined,
        verificationStatus: item.verification_status ?? undefined,
      })),
    }
  }
  async followUps(
    filters: {
      classId?: string
      sessionId?: string
      studentId?: string
      status?: PblFollowUpStatus
      offset?: number
    } = {},
  ) {
    const value = await apiRequest({
      path: '/teacher/pbl-follow-ups',
      query: {
        class_id: filters.classId,
        session_id: filters.sessionId,
        student_id: filters.studentId,
        status: filters.status,
        offset: filters.offset ?? 0,
        limit: 20,
      },
      schema: z.object({
        items: z.array(
          z.object({
            plan_id: z.number(),
            student_id: z.number(),
            student_name: z.string(),
            class_id: z.number(),
            class_name: z.string(),
            session_id: z.number(),
            session_topic: z.string(),
            status: z.enum(['in_progress', 'cycle_2', 'support_needed', 'improved']),
            current_cycle: z.number(),
            verification_status: z.string(),
            automation_exhausted: z.boolean(),
            failed_targets: z.array(
              z.object({ target_type: z.string(), target_code: z.string(), label: z.string().nullable().optional() }),
            ),
          }),
        ),
        total: z.number(),
        limit: z.number(),
        offset: z.number(),
      }),
    })
    return {
      items: value.items.map((item): PblFollowUp => ({
        planId: item.plan_id,
        studentId: item.student_id,
        studentName: item.student_name,
        classId: item.class_id,
        className: item.class_name,
        sessionId: item.session_id,
        sessionTopic: item.session_topic,
        status: item.status,
        currentCycle: item.current_cycle,
        verificationStatus: item.verification_status,
        automationExhausted: item.automation_exhausted,
        failedTargets: item.failed_targets.map((target) => ({ ...target, label: target.label ?? undefined })),
      })),
      total: value.total,
    }
  }
  async followUp(planId: number) {
    const value = await apiRequest({
      path: `/teacher/pbl-follow-ups/${planId}`,
      schema: z.object({ plan, feedbacks: z.array(teacherFeedback) }),
    })
    return { plan: value.plan as PblPlan, feedbacks: value.feedbacks.map(toFeedback) }
  }
  async followUpFeedback(planId: number, clientFeedbackId: string, body: string) {
    return toFeedback(
      await apiRequest({
        path: `/teacher/pbl-follow-ups/${planId}/feedback`,
        method: 'POST',
        body: { client_feedback_id: clientFeedbackId, body },
        schema: teacherFeedback,
      }),
    )
  }
  async submitTask(taskId: number, submissionId: string, answer: { text?: string; selected_option?: number }) {
    return apiRequest({
      path: `/student/pbl-learning-tasks/${taskId}/submit`,
      method: 'POST',
      body: { client_submission_id: submissionId, answer },
      schema: plan,
    })
  }
  async summary(item: SessionType) {
    return apiRequest({ path: `/classes/${item.classId}/pbl-sessions/${item.id}/summary`, schema: summary })
  }
}
