import { z } from 'zod'
import type {
  PblCycleCheck,
  PblCycleEvaluation,
  PblLearningReport,
  PblReportAction,
  PblReportPage,
  PblReportSession,
  PblReportStatus,
} from '../domain/ports'

const reportStatus = z.enum([
  'discussing',
  'awaiting_learning',
  'learning_cycle_1',
  'learning_cycle_2',
  'improved',
  'support_needed',
])
const phase = z.enum(['problem_framing', 'hypothesis', 'evidence', 'synthesis', 'completed'])
const action = z.object({ kind: z.enum(['discussion', 'tasks', 'none']), label: z.string() })
const reportSession = z.object({
  id: z.number(),
  topic_code: z.string(),
  topic_label: z.string(),
  case_title: z.string(),
  status: z.string(),
  created_at: z.string(),
  closed_at: z.string().nullable(),
})
const cycleCheck = z.object({
  target_type: z.string(),
  target_code: z.string(),
  label: z.string(),
  threshold: z.number().nullable(),
  score: z.number().nullable(),
  evidence_present: z.boolean(),
  passed: z.boolean(),
})
const evaluation = z.object({
  cycle_number: z.number(),
  policy_version: z.string(),
  result: z.string(),
  checks: z.array(cycleCheck),
  failed_targets: z.array(z.object({ target_type: z.string(), target_code: z.string(), label: z.string() })),
  automation_exhausted: z.boolean(),
  record_source: z.string(),
  evaluated_at: z.string(),
})
const taskProgress = z.object({ completed: z.number(), total: z.number() })
const dashboard = z.object({
  data_basis: z.enum(['student_pbl_evidence', 'synthetic_demo']),
  period_start: z.string(),
  period_end: z.string(),
  mastery_score: z.number().min(0).max(100).nullable(),
  mastery_delta: z.number().nullable(),
  mastery_sample_count: z.number().min(0),
  study_minutes: z.number().min(0),
  study_duration_basis: z.enum(['estimated_activity_intervals', 'synthetic_demo']),
  plan_completion_rate: z.number().min(0).max(100).nullable(),
  mastered_knowledge_count: z.number().min(0),
  ai_diagnostic_count: z.number().min(0),
  status_label: z.string(),
  trend: z.array(
    z.object({
      period_start: z.string(),
      period_end: z.string(),
      score: z.number().min(0).max(100).nullable(),
      sample_count: z.number().min(0),
    }),
  ),
  weaknesses: z.array(
    z.object({
      target_type: z.string(),
      target_code: z.string(),
      label: z.string(),
      occurrences: z.number().min(0),
      mastery_percentage: z.number().min(0).max(100).nullable(),
    }),
  ),
  ai_summary: z.string(),
})
const listItem = z.object({
  session: reportSession,
  status: reportStatus,
  current_phase: phase.nullable(),
  phase_status: z.enum(['active', 'completed']).nullable(),
  knowledge_gap_count: z.number(),
  reasoning_issue_count: z.number(),
  task_progress: taskProgress,
  summary_text: z.string(),
  next_action: action,
  updated_at: z.string(),
})
export const reportPageSchema = z.object({
  summary: z.object({
    total_reports: z.number(),
    completed_personal_discussions: z.number(),
    status_counts: z.record(z.string(), z.number()),
    recurring_targets: z.array(
      z.object({ target_type: z.string(), target_code: z.string(), label: z.string(), occurrences: z.number() }),
    ),
    dashboard,
    next_action: action.extend({ session_id: z.number(), case_title: z.string() }).nullable(),
  }),
  items: z.array(listItem),
  total: z.number(),
  limit: z.number(),
  offset: z.number(),
})
export const reportDetailSchema = z.object({
  session: reportSession,
  status: reportStatus,
  visibility: z.enum(['private', 'classroom', 'legacy_shared']),
  current_phase: phase.nullable(),
  phase_status: z.enum(['active', 'completed']).nullable(),
  phase_progress: z.array(
    z.object({
      phase: z.enum(['problem_framing', 'hypothesis', 'evidence', 'synthesis']),
      label: z.string(),
      state: z.enum(['completed', 'current', 'pending']),
      evidence_summary: z.string(),
      missing_elements: z.array(z.string()),
      evidenced_at: z.string().nullable(),
    }),
  ),
  diagnosis: z.object({
    created_at: z.string().nullable(),
    knowledge_gaps: z.array(
      z.object({
        id: z.string(),
        point_code: z.string(),
        label: z.string(),
        summary: z.string(),
        confidence: z.string(),
        evidence_summary: z.string(),
      }),
    ),
    reasoning_issues: z.array(
      z.object({
        id: z.string(),
        dimension_id: z.string(),
        label: z.string(),
        summary: z.string(),
        issue_type: z.string(),
        improvement: z.string(),
        evidence_summary: z.string(),
      }),
    ),
  }),
  plans: z.array(
    z.object({
      id: z.number(),
      assignment_basis: z.enum(['personal', 'classroom']),
      status: z.string(),
      verification_status: z.string(),
      current_cycle: z.number(),
      max_cycles: z.number(),
      automation_exhausted: z.boolean(),
      decision_policy_version: z.string(),
      due_at: z.string(),
      created_at: z.string(),
      tasks: z.array(
        z.object({
          id: z.number(),
          task_type: z.string(),
          status: z.string(),
          cycle_number: z.number(),
          target_type: z.string(),
          target_code: z.string(),
          target_label: z.string(),
          prompt: z.string(),
          reference: z.string().nullable(),
          score: z.number().nullable(),
          feedback: z.string(),
          evidence_present: z.boolean(),
          submitted_at: z.string().nullable(),
        }),
      ),
      evaluations: z.array(evaluation),
    }),
  ),
  target_progress: z.array(
    z.object({
      plan_id: z.number(),
      target_type: z.string(),
      target_code: z.string(),
      label: z.string(),
      cycles: z.array(cycleCheck.extend({ cycle_number: z.number() })),
    }),
  ),
  task_progress: taskProgress,
  summary_text: z.string(),
  next_action: action,
  teacher_feedbacks: z.array(
    z.object({
      id: z.number(),
      plan_id: z.number().nullable(),
      action_type: z.string(),
      body: z.string(),
      created_at: z.string().nullable(),
    }),
  ),
  timeline: z.array(
    z.object({
      type: z.string(),
      label: z.string(),
      cycle_number: z.number().nullable().optional(),
      occurred_at: z.string(),
    }),
  ),
  updated_at: z.string(),
})

const mapSession = (value: z.infer<typeof reportSession>): PblReportSession => ({
  id: String(value.id),
  topicCode: value.topic_code,
  topicLabel: value.topic_label,
  caseTitle: value.case_title,
  status: value.status,
  createdAt: value.created_at,
  closedAt: value.closed_at ?? undefined,
})
const mapAction = (value: z.infer<typeof action>): PblReportAction => ({ kind: value.kind, label: value.label })
const mapCheck = (value: z.infer<typeof cycleCheck>): PblCycleCheck => ({
  target_type: value.target_type,
  target_code: value.target_code,
  label: value.label,
  threshold: value.threshold,
  score: value.score,
  evidence_present: value.evidence_present,
  passed: value.passed,
})
const mapEvaluation = (value: z.infer<typeof evaluation>): PblCycleEvaluation => ({
  cycle_number: value.cycle_number,
  policy_version: value.policy_version,
  result: value.result,
  checks: value.checks.map(mapCheck),
  failed_targets: value.failed_targets,
  automation_exhausted: value.automation_exhausted,
  record_source: value.record_source,
  evaluated_at: value.evaluated_at,
})
const statusCounts = (value: Record<string, number>): Record<PblReportStatus, number> => ({
  discussing: value.discussing ?? 0,
  awaiting_learning: value.awaiting_learning ?? 0,
  learning_cycle_1: value.learning_cycle_1 ?? 0,
  learning_cycle_2: value.learning_cycle_2 ?? 0,
  improved: value.improved ?? 0,
  support_needed: value.support_needed ?? 0,
})

export function mapReportPage(value: z.infer<typeof reportPageSchema>): PblReportPage {
  return {
    summary: {
      totalReports: value.summary.total_reports,
      completedPersonalDiscussions: value.summary.completed_personal_discussions,
      statusCounts: statusCounts(value.summary.status_counts),
      recurringTargets: value.summary.recurring_targets.map((item) => ({
        targetType: item.target_type,
        targetCode: item.target_code,
        label: item.label,
        occurrences: item.occurrences,
      })),
      dashboard: {
        dataBasis: value.summary.dashboard.data_basis,
        periodStart: value.summary.dashboard.period_start,
        periodEnd: value.summary.dashboard.period_end,
        masteryScore: value.summary.dashboard.mastery_score,
        masteryDelta: value.summary.dashboard.mastery_delta,
        masterySampleCount: value.summary.dashboard.mastery_sample_count,
        studyMinutes: value.summary.dashboard.study_minutes,
        studyDurationBasis: value.summary.dashboard.study_duration_basis,
        planCompletionRate: value.summary.dashboard.plan_completion_rate,
        masteredKnowledgeCount: value.summary.dashboard.mastered_knowledge_count,
        aiDiagnosticCount: value.summary.dashboard.ai_diagnostic_count,
        statusLabel: value.summary.dashboard.status_label,
        trend: value.summary.dashboard.trend.map((item) => ({
          periodStart: item.period_start,
          periodEnd: item.period_end,
          score: item.score,
          sampleCount: item.sample_count,
        })),
        weaknesses: value.summary.dashboard.weaknesses.map((item) => ({
          targetType: item.target_type,
          targetCode: item.target_code,
          label: item.label,
          occurrences: item.occurrences,
          masteryPercentage: item.mastery_percentage,
        })),
        aiSummary: value.summary.dashboard.ai_summary,
      },
      nextAction: value.summary.next_action
        ? {
            ...mapAction(value.summary.next_action),
            sessionId: String(value.summary.next_action.session_id),
            caseTitle: value.summary.next_action.case_title,
          }
        : undefined,
    },
    items: value.items.map((item) => ({
      session: mapSession(item.session),
      status: item.status,
      currentPhase: item.current_phase ?? undefined,
      phaseStatus: item.phase_status ?? undefined,
      knowledgeGapCount: item.knowledge_gap_count,
      reasoningIssueCount: item.reasoning_issue_count,
      taskProgress: item.task_progress,
      summaryText: item.summary_text,
      nextAction: mapAction(item.next_action),
      updatedAt: item.updated_at,
    })),
    total: value.total,
    limit: value.limit,
    offset: value.offset,
  }
}

export function mapLearningReport(value: z.infer<typeof reportDetailSchema>): PblLearningReport {
  return {
    session: mapSession(value.session),
    status: value.status,
    visibility: value.visibility,
    currentPhase: value.current_phase ?? undefined,
    phaseStatus: value.phase_status ?? undefined,
    phaseProgress: value.phase_progress.map((item) => ({
      phase: item.phase,
      label: item.label,
      state: item.state,
      evidenceSummary: item.evidence_summary,
      missingElements: item.missing_elements,
      evidencedAt: item.evidenced_at ?? undefined,
    })),
    diagnosis: {
      createdAt: value.diagnosis.created_at ?? undefined,
      knowledgeGaps: value.diagnosis.knowledge_gaps.map((item) => ({
        id: item.id,
        pointCode: item.point_code,
        label: item.label,
        summary: item.summary,
        confidence: item.confidence,
        evidenceSummary: item.evidence_summary,
      })),
      reasoningIssues: value.diagnosis.reasoning_issues.map((item) => ({
        id: item.id,
        dimensionId: item.dimension_id,
        label: item.label,
        summary: item.summary,
        issueType: item.issue_type,
        improvement: item.improvement,
        evidenceSummary: item.evidence_summary,
      })),
    },
    plans: value.plans.map((plan) => ({
      id: plan.id,
      assignmentBasis: plan.assignment_basis,
      status: plan.status,
      verificationStatus: plan.verification_status,
      currentCycle: plan.current_cycle,
      maxCycles: plan.max_cycles,
      automationExhausted: plan.automation_exhausted,
      decisionPolicyVersion: plan.decision_policy_version,
      dueAt: plan.due_at,
      createdAt: plan.created_at,
      tasks: plan.tasks.map((task) => ({
        id: task.id,
        taskType: task.task_type,
        status: task.status,
        cycleNumber: task.cycle_number,
        targetType: task.target_type,
        targetCode: task.target_code,
        targetLabel: task.target_label,
        prompt: task.prompt,
        reference: task.reference ?? undefined,
        score: task.score,
        feedback: task.feedback,
        evidencePresent: task.evidence_present,
        submittedAt: task.submitted_at ?? undefined,
      })),
      evaluations: plan.evaluations.map(mapEvaluation),
    })),
    targetProgress: value.target_progress.map((item) => ({
      planId: item.plan_id,
      targetType: item.target_type,
      targetCode: item.target_code,
      label: item.label,
      cycles: item.cycles.map((cycle) => ({ cycleNumber: cycle.cycle_number, ...mapCheck(cycle) })),
    })),
    taskProgress: value.task_progress,
    summaryText: value.summary_text,
    nextAction: mapAction(value.next_action),
    teacherFeedbacks: value.teacher_feedbacks.map((item) => ({
      id: String(item.id),
      planId: item.plan_id == null ? undefined : String(item.plan_id),
      actionType: item.action_type,
      body: item.body,
      createdAt: item.created_at ?? undefined,
    })),
    timeline: value.timeline.map((item) => ({
      type: item.type,
      label: item.label,
      cycleNumber: item.cycle_number ?? undefined,
      occurredAt: item.occurred_at,
    })),
    updatedAt: value.updated_at,
  }
}
