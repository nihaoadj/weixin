import { z } from 'zod'
import type {
  apiCaseAssessmentSchema,
  apiCaseAttemptSchema,
  apiCaseAttemptSummarySchema,
  apiPatientMessageSchema,
  apiStageAnswerSchema,
} from '@/platform/contracts/case'
import type { CaseAssessment, CaseAttempt, CaseMessage, StageAnswer } from '@/types/case'
export function toCaseMessage(value: z.infer<typeof apiPatientMessageSchema>): CaseMessage {
  return { id: String(value.id), role: value.role, content: value.content, createdAt: value.created_at }
}

export function toStageAnswer(value: z.infer<typeof apiStageAnswerSchema>): StageAnswer {
  switch (value.stage_id) {
    case 'history':
      return { stageId: value.stage_id, summary: value.summary, keyFindings: value.key_findings }
    case 'problem_representation':
      return { stageId: value.stage_id, summary: value.summary }
    case 'differential':
      return {
        stageId: value.stage_id,
        items: value.items.map((item) => ({
          diagnosis: item.diagnosis,
          supportingEvidence: item.supporting_evidence,
          opposingEvidence: item.opposing_evidence,
        })),
      }
    case 'tests':
      return {
        stageId: value.stage_id,
        items: value.items.map((item) => ({
          testName: item.test_name,
          rationale: item.rationale,
          priority: item.priority,
        })),
      }
    case 'management':
      return { stageId: value.stage_id, items: value.items, safetyConsiderations: value.safety_considerations }
  }
}

export function toApiAnswer(value: StageAnswer): z.infer<typeof apiStageAnswerSchema> {
  switch (value.stageId) {
    case 'history':
      return { stage_id: value.stageId, summary: value.summary, key_findings: value.keyFindings }
    case 'problem_representation':
      return { stage_id: value.stageId, summary: value.summary }
    case 'differential':
      return {
        stage_id: value.stageId,
        items: value.items.map((item) => ({
          diagnosis: item.diagnosis,
          supporting_evidence: item.supportingEvidence,
          opposing_evidence: item.opposingEvidence,
        })),
      }
    case 'tests':
      return {
        stage_id: value.stageId,
        items: value.items.map((item) => ({
          test_name: item.testName,
          rationale: item.rationale,
          priority: item.priority,
        })),
      }
    case 'management':
      return { stage_id: value.stageId, items: value.items, safety_considerations: value.safetyConsiderations }
  }
}

export function toCaseAttempt(value: z.infer<typeof apiCaseAttemptSchema>): CaseAttempt {
  return {
    id: String(value.id),
    problemId: String(value.problem_id),
    problemVersion: value.problem_version,
    status: value.status,
    currentStage: value.current_stage,
    focusStage: value.focus_stage ?? undefined,
    retryOfId: value.retry_of_id == null ? undefined : String(value.retry_of_id),
    opening: {
      setting: value.opening.setting,
      patientIntro: value.opening.patient_intro,
      chiefComplaint: value.opening.chief_complaint,
    },
    messages: value.messages.map(toCaseMessage),
    submissions: value.submissions.map((item) => ({
      id: String(item.id),
      stageId: item.stage_id,
      answer: toStageAnswer(item.answer),
      feedback: item.feedback,
      inheritedFromId: item.inherited_from_id == null ? undefined : String(item.inherited_from_id),
      createdAt: item.created_at,
    })),
    assessmentReady: value.assessment_ready,
    startedAt: value.started_at,
  }
}

// The public training entry returns CaseAttempt[]; summary defaults are presentation-only.
// Always fetch the full attempt before resuming training.
export function toCaseAttemptSummary(value: z.infer<typeof apiCaseAttemptSummarySchema>): CaseAttempt {
  return {
    id: String(value.id),
    problemId: String(value.problem_id),
    status: value.status,
    currentStage: value.current_stage,
    focusStage: value.focus_stage ?? undefined,
    startedAt: value.started_at,
    problemVersion: 1,
    opening: { setting: '', patientIntro: '', chiefComplaint: '' },
    messages: [],
    submissions: [],
    assessmentReady: value.status === 'assessed',
  }
}

export function toCaseAssessment(value: z.infer<typeof apiCaseAssessmentSchema>): CaseAssessment {
  return {
    attemptId: String(value.attempt_id),
    totalScore: value.total_score,
    dimensions: value.dimensions.map((item) => ({
      dimensionId: item.dimension_id,
      label: item.label,
      score: item.score,
      weightedScore: item.weighted_score,
      evidence: item.evidence,
      feedback: item.feedback,
      nextStep: item.next_step,
    })),
    strengths: value.strengths,
    weaknesses: value.weaknesses,
    nextSteps: value.next_steps,
    summary: value.summary,
    focusStage: value.focus_stage,
    modelName: value.model_name,
    promptVersion: value.prompt_version,
    fallbackUsed: value.fallback_used,
    comparison: value.comparison
      ? {
          totalDelta: value.comparison.total_delta,
          dimensions: value.comparison.dimensions.map((item) => ({
            dimensionId: item.dimension_id,
            previousScore: item.previous_score,
            currentScore: item.current_score,
            delta: item.delta,
          })),
        }
      : undefined,
  }
}
