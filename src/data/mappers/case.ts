import { z } from 'zod'
import type {
  apiCaseAssessmentSchema,
  apiCaseAttemptSchema,
  apiCaseAttemptSummarySchema,
  apiCaseAuthoringSchema,
  apiCaseDefinitionSchema,
  apiCaseDraftSchema,
  apiCaseRubricSchema,
  apiPatientMessageSchema,
  apiStageAnswerSchema,
} from '@/data/contracts/case'
import type {
  CaseAssessment,
  CaseAttempt,
  CaseDefinition,
  CaseDraftGenerateResult,
  CaseMessage,
  StageAnswer,
} from '@/types/case'
import { AppError } from '@/types/errors'

import { apiReferenceReasoningSchema as apiReasoning } from '@/data/contracts/case'
const domainReasoning = z.object({
  problemRepresentation: z.string(),
  differentials: z.array(
    z.object({
      diagnosis: z.string(),
      supportingFactIds: z.array(z.string()).default([]),
      opposingFactIds: z.array(z.string()).default([]),
      priority: z.number(),
    }),
  ),
  tests: z.array(
    z.object({
      name: z.string(),
      purpose: z.string(),
      priority: z.enum(['necessary', 'optional', 'avoid']),
      resultFactId: z.string().nullable().optional(),
    }),
  ),
  management: z.array(
    z.object({
      action: z.string(),
      rationale: z.string(),
      priority: z.number(),
      safetyCritical: z.boolean().default(false),
    }),
  ),
})

export function toCaseDefinition(value: z.infer<typeof apiCaseDefinitionSchema>): CaseDefinition {
  const parsed = apiReasoning.safeParse(value.reference_reasoning)
  if (!parsed.success) throw new AppError('病例推理数据不符合契约', { code: 'CONTRACT_ERROR', cause: parsed.error })
  const ref = parsed.data
  return {
    schemaVersion: value.schema_version,
    opening: {
      setting: value.opening.setting,
      patientIntro: value.opening.patient_intro,
      chiefComplaint: value.opening.chief_complaint,
    },
    stageInstructions: value.stage_instructions,
    facts: value.facts.map((item) => ({
      id: item.id,
      category: item.category,
      label: item.label,
      value: item.value,
      triggers: item.triggers,
      revealStage: item.reveal_stage,
    })),
    referenceReasoning: {
      problemRepresentation: ref.problem_representation,
      differentials: ref.differentials.map((item) => ({
        diagnosis: item.diagnosis,
        supportingFactIds: item.supporting_fact_ids,
        opposingFactIds: item.opposing_fact_ids,
        priority: item.priority,
      })),
      tests: ref.tests.map((item) => ({
        name: item.name,
        purpose: item.purpose,
        priority: item.priority,
        resultFactId: item.result_fact_id,
      })),
      management: ref.management.map((item) => ({
        action: item.action,
        rationale: item.rationale,
        priority: item.priority,
        safetyCritical: item.safety_critical,
      })),
    },
    practiceBlueprints: value.practice_blueprints.map((item) => ({
      id: item.id,
      dimensionId: item.dimension_id,
      stageId: item.stage_id,
      learnerLevel: item.learner_level,
      publicInstruction: item.public_instruction,
      allowedVariants: item.allowed_variants,
      fixedFacts: item.fixed_facts,
      fallbackPrompt: item.fallback_prompt,
      answerSchema: item.answer_schema,
      criteria: item.criteria,
    })),
  }
}

export function toCaseRubric(value: z.infer<typeof apiCaseRubricSchema>): CaseDraftGenerateResult['rubric'] {
  return {
    dimensions: value.dimensions.map((item) => ({
      id: item.id,
      label: item.label,
      weight: item.weight,
      stageIds: item.stage_ids,
      criteria: item.criteria,
    })),
  }
}

export function toCaseDraft(value: z.infer<typeof apiCaseDraftSchema>): CaseDraftGenerateResult {
  return {
    title: value.title,
    description: value.description,
    specialty: value.specialty,
    difficulty: value.difficulty,
    estimatedMinutes: value.estimated_minutes,
    caseDefinition: toCaseDefinition(value.case_definition),
    rubric: toCaseRubric(value.rubric),
    generationMode: value.generation_mode,
    safetyNotice: value.safety_notice,
  }
}

export function toAuthoring(value: z.infer<typeof apiCaseAuthoringSchema>): CaseDraftGenerateResult {
  if (!value.case_definition || !value.rubric) throw new AppError('病例编排数据缺失', { code: 'CONTRACT_ERROR' })
  return toCaseDraft({
    ...value,
    case_definition: value.case_definition,
    rubric: value.rubric,
    generation_mode: 'fallback',
    safety_notice: '合成教学病例，不构成诊疗建议。',
  })
}

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

// The existing facade returns CaseAttempt[]; summary defaults are presentation-only.
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

export function toApiDefinition(value: CaseDefinition) {
  const ref = domainReasoning.parse(value.referenceReasoning)
  return {
    schema_version: value.schemaVersion,
    opening: {
      setting: value.opening.setting,
      patient_intro: value.opening.patientIntro,
      chief_complaint: value.opening.chiefComplaint,
    },
    stage_instructions: value.stageInstructions,
    facts: value.facts.map((item) => ({
      id: item.id,
      category: item.category,
      label: item.label,
      value: item.value,
      triggers: item.triggers,
      reveal_stage: item.revealStage,
    })),
    reference_reasoning: {
      problem_representation: ref.problemRepresentation,
      differentials: ref.differentials.map((item) => ({
        diagnosis: item.diagnosis,
        supporting_fact_ids: item.supportingFactIds,
        opposing_fact_ids: item.opposingFactIds,
        priority: item.priority,
      })),
      tests: ref.tests.map((item) => ({
        name: item.name,
        purpose: item.purpose,
        priority: item.priority,
        result_fact_id: item.resultFactId,
      })),
      management: ref.management.map((item) => ({
        action: item.action,
        rationale: item.rationale,
        priority: item.priority,
        safety_critical: item.safetyCritical,
      })),
    },
    practice_blueprints: (value.practiceBlueprints || []).map((item) => ({
      id: item.id,
      dimension_id: item.dimensionId,
      stage_id: item.stageId,
      learner_level: item.learnerLevel,
      public_instruction: item.publicInstruction,
      allowed_variants: item.allowedVariants,
      fixed_facts: item.fixedFacts,
      fallback_prompt: item.fallbackPrompt,
      answer_schema: item.answerSchema,
      criteria: item.criteria,
    })),
  }
}

export function toApiRubric(value: CaseDraftGenerateResult['rubric']) {
  return {
    dimensions: value.dimensions.map((item) => ({
      id: item.id,
      label: item.label,
      weight: item.weight,
      stage_ids: item.stageIds,
      criteria: item.criteria,
    })),
  }
}
