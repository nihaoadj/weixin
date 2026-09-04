import { z } from 'zod'
import { apiProblemSchema } from './core'

export const caseStageSchema = z.enum(['history', 'problem_representation', 'differential', 'tests', 'management'])
const timestamp = z.string().min(1)

export const apiCaseOpeningSchema = z.object({
  setting: z.string(),
  patient_intro: z.string(),
  chief_complaint: z.string(),
})

const practiceCriterionSchema = z.object({
  id: z.string(),
  weight: z.number(),
  keywords: z.array(z.string()),
  feedback: z.string(),
  critical: z.boolean().optional().default(false),
})

const practiceBlueprintSchema = z.object({
  id: z.string(),
  dimension_id: z.string(),
  stage_id: caseStageSchema,
  learner_level: z.string(),
  public_instruction: z.string(),
  allowed_variants: z.array(z.string()).optional().default([]),
  fixed_facts: z.array(z.string()).optional().default([]),
  fallback_prompt: z.string(),
  reinforcement_prompt: z.string().nullable().optional(),
  reinforcement_variant_code: z.string().nullable().optional(),
  answer_schema: z.enum(['short_text', 'evidence_grid', 'decision_cards']),
  criteria: z.array(practiceCriterionSchema),
})

export const apiReferenceReasoningSchema = z.object({
  problem_representation: z.string(),
  differentials: z.array(
    z.object({
      diagnosis: z.string(),
      supporting_fact_ids: z.array(z.string()).default([]),
      opposing_fact_ids: z.array(z.string()).default([]),
      priority: z.number(),
    }),
  ),
  tests: z.array(
    z.object({
      name: z.string(),
      purpose: z.string(),
      priority: z.enum(['necessary', 'optional', 'avoid']),
      result_fact_id: z.string().nullable().optional(),
    }),
  ),
  management: z.array(
    z.object({
      action: z.string(),
      rationale: z.string(),
      priority: z.number(),
      safety_critical: z.boolean().default(false),
    }),
  ),
})

export const apiCaseDefinitionSchema = z.object({
  schema_version: z
    .union([z.literal(1), z.literal(2), z.literal(3)])
    .optional()
    .default(1),
  opening: apiCaseOpeningSchema,
  stage_instructions: z.object({
    history: z.string(),
    problem_representation: z.string(),
    differential: z.string(),
    tests: z.string(),
    management: z.string(),
  }),
  facts: z.array(
    z.object({
      id: z.string(),
      category: z.enum(['history', 'exam', 'test']),
      label: z.string(),
      value: z.string(),
      triggers: z.array(z.string()),
      reveal_stage: caseStageSchema,
    }),
  ),
  reference_reasoning: apiReferenceReasoningSchema,
  practice_blueprints: z.array(practiceBlueprintSchema).optional().default([]),
})

export const apiCaseRubricSchema = z.object({
  dimensions: z.array(
    z.object({
      id: z.string(),
      label: z.string(),
      weight: z.number(),
      stage_ids: z.array(caseStageSchema),
      criteria: z.array(
        z.object({
          id: z.string(),
          label: z.string(),
          keywords: z.array(z.string()),
          feedback: z.string(),
          critical: z.boolean().optional().default(false),
        }),
      ),
    }),
  ),
})

export const apiCaseDraftSchema = z.object({
  title: z.string(),
  description: z.string().optional().default(''),
  specialty: z.string(),
  difficulty: z.enum(['basic', 'intermediate', 'advanced']).optional().default('basic'),
  estimated_minutes: z.number().int().positive().optional().default(10),
  case_definition: apiCaseDefinitionSchema,
  rubric: apiCaseRubricSchema,
  generation_mode: z.enum(['model', 'fallback']),
  safety_notice: z.string(),
})

export const apiPatientMessageSchema = z.object({
  id: z.number().int(),
  role: z.enum(['user', 'assistant']),
  content: z.string(),
  created_at: timestamp,
  response_mode: z.enum(['model', 'fallback', 'safety']).nullable().optional(),
  generation_mode: z.enum(['model', 'fallback']).nullable().optional(),
})

export const apiStageAnswerSchema = z.discriminatedUnion('stage_id', [
  z.object({ stage_id: z.literal('history'), summary: z.string(), key_findings: z.array(z.string()).default([]) }),
  z.object({ stage_id: z.literal('problem_representation'), summary: z.string() }),
  z.object({
    stage_id: z.literal('differential'),
    items: z.array(
      z.object({
        diagnosis: z.string(),
        supporting_evidence: z.array(z.string()).default([]),
        opposing_evidence: z.array(z.string()).default([]),
      }),
    ),
  }),
  z.object({
    stage_id: z.literal('tests'),
    items: z.array(
      z.object({
        test_name: z.string(),
        rationale: z.string(),
        priority: z.enum(['necessary', 'optional', 'avoid']),
      }),
    ),
  }),
  z.object({
    stage_id: z.literal('management'),
    items: z.array(
      z.object({
        action: z.string(),
        rationale: z.string(),
      }),
    ),
    safety_considerations: z.array(z.string()).default([]),
  }),
])

export const apiStageSubmissionSchema = z.object({
  id: z.number().int(),
  stage_id: caseStageSchema,
  answer: apiStageAnswerSchema,
  feedback: z.string(),
  inherited_from_id: z.number().int().nullable().optional(),
  created_at: timestamp,
})

export const apiCaseAttemptSchema = z.object({
  id: z.number().int(),
  problem_id: z.number().int(),
  problem_version: z.number().int(),
  status: z.enum(['in_progress', 'completed', 'assessed']),
  current_stage: z.union([caseStageSchema, z.literal('completed')]),
  focus_stage: caseStageSchema.nullable().optional(),
  retry_of_id: z.number().int().nullable().optional(),
  opening: apiCaseOpeningSchema,
  messages: z.array(apiPatientMessageSchema).optional().default([]),
  submissions: z.array(apiStageSubmissionSchema).optional().default([]),
  assessment_ready: z.boolean().optional().default(false),
  started_at: timestamp,
})
export const apiCaseAttemptSummarySchema = apiCaseAttemptSchema
  .pick({
    id: true,
    problem_id: true,
    status: true,
    current_stage: true,
    focus_stage: true,
    started_at: true,
  })
  .extend({ total_score: z.number().nullable().optional() })
export const apiCaseAttemptListSchema = z.array(apiCaseAttemptSummarySchema)

const assessmentDimensionSchema = z.object({
  dimension_id: z.string(),
  label: z.string(),
  score: z.number(),
  weighted_score: z.number(),
  evidence: z.array(z.string()).optional().default([]),
  feedback: z.string(),
  next_step: z.string(),
})

export const apiCaseAssessmentSchema = z.object({
  attempt_id: z.number().int(),
  total_score: z.number(),
  dimensions: z.array(assessmentDimensionSchema),
  strengths: z.array(z.string()).optional().default([]),
  weaknesses: z.array(z.string()).optional().default([]),
  next_steps: z.array(z.string()).optional().default([]),
  summary: z.string(),
  focus_stage: caseStageSchema,
  model_name: z.string(),
  prompt_version: z.string(),
  fallback_used: z.boolean(),
  comparison: z
    .object({
      total_delta: z.number(),
      dimensions: z
        .array(
          z.object({
            dimension_id: z.string(),
            previous_score: z.number(),
            current_score: z.number(),
            delta: z.number(),
          }),
        )
        .optional()
        .default([]),
    })
    .nullable()
    .optional(),
})

export const apiCaseAuthoringSchema = apiProblemSchema.extend({
  case_definition: apiCaseDefinitionSchema.nullable().optional(),
  rubric: apiCaseRubricSchema.nullable().optional(),
})

const medicalReviewSchema = z.object({
  id: z.number().int(),
  problem_id: z.number().int(),
  reviewer_id: z.number().int(),
  decision: z.enum(['approved', 'rejected']),
  comment: z.string(),
  problem_version: z.number().int(),
  case_digest: z.string(),
  created_at: timestamp,
})

export const apiMedicalReviewViewSchema = apiCaseAuthoringSchema.extend({
  current_digest: z.string(),
  author_nickname: z.string().nullable().optional(),
  reviews: z.array(medicalReviewSchema).optional().default([]),
})
