import { z } from 'zod'
import type { CaseAssessment, CaseAttempt, CaseDraftGenerateResult, StageAnswer } from '@/types/case'
import { problemSchema } from '@/platform/storage/storage'

const stage = z.enum(['history', 'problem_representation', 'differential', 'tests', 'management'])
const opening = z.object({ setting: z.string(), patientIntro: z.string(), chiefComplaint: z.string() })
const answer: z.ZodType<StageAnswer> = z.discriminatedUnion('stageId', [
  z.object({ stageId: z.literal('history'), summary: z.string(), keyFindings: z.array(z.string()) }),
  z.object({ stageId: z.literal('problem_representation'), summary: z.string() }),
  z.object({
    stageId: z.literal('differential'),
    items: z.array(
      z.object({
        diagnosis: z.string(),
        supportingEvidence: z.array(z.string()),
        opposingEvidence: z.array(z.string()),
      }),
    ),
  }),
  z.object({
    stageId: z.literal('tests'),
    items: z.array(
      z.object({ testName: z.string(), rationale: z.string(), priority: z.enum(['necessary', 'optional', 'avoid']) }),
    ),
  }),
  z.object({
    stageId: z.literal('management'),
    items: z.array(z.object({ action: z.string(), rationale: z.string() })),
    safetyConsiderations: z.array(z.string()),
  }),
])

export const localAttemptSchema: z.ZodType<CaseAttempt> = z.object({
  id: z.string(),
  problemId: z.string(),
  problemVersion: z.number(),
  status: z.enum(['in_progress', 'completed', 'assessed']),
  currentStage: z.union([stage, z.literal('completed')]),
  focusStage: stage.optional(),
  retryOfId: z.string().optional(),
  opening,
  messages: z.array(
    z.object({
      id: z.string(),
      role: z.enum(['user', 'assistant']),
      content: z.string(),
      createdAt: z.string(),
      revealedFactIds: z.array(z.string()).optional(),
    }),
  ),
  submissions: z.array(
    z.object({
      id: z.string(),
      stageId: stage,
      answer,
      feedback: z.string(),
      inheritedFromId: z.string().optional(),
      createdAt: z.string(),
    }),
  ),
  assessmentReady: z.boolean(),
  startedAt: z.string(),
})

export const localAssessmentSchema: z.ZodType<CaseAssessment> = z.object({
  attemptId: z.string(),
  totalScore: z.number(),
  dimensions: z.array(
    z.object({
      dimensionId: z.string(),
      label: z.string(),
      score: z.number(),
      weightedScore: z.number(),
      evidence: z.array(z.string()),
      feedback: z.string(),
      nextStep: z.string(),
    }),
  ),
  strengths: z.array(z.string()),
  weaknesses: z.array(z.string()),
  nextSteps: z.array(z.string()),
  summary: z.string(),
  focusStage: stage,
  modelName: z.string(),
  promptVersion: z.string(),
  fallbackUsed: z.boolean(),
  comparison: z
    .object({
      totalDelta: z.number(),
      dimensions: z.array(
        z.object({ dimensionId: z.string(), previousScore: z.number(), currentScore: z.number(), delta: z.number() }),
      ),
    })
    .optional(),
})

export const localDraftSchema: z.ZodType<CaseDraftGenerateResult> = z.object({
  title: z.string(),
  description: z.string(),
  specialty: z.string(),
  difficulty: z.enum(['basic', 'intermediate', 'advanced']),
  estimatedMinutes: z.number(),
  generationMode: z.enum(['model', 'fallback']),
  safetyNotice: z.string(),
  caseDefinition: z.object({
    schemaVersion: z.union([z.literal(1), z.literal(2), z.literal(3)]),
    opening,
    stageInstructions: z.object({
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
        revealStage: stage,
      }),
    ),
    referenceReasoning: z.object({
      problemRepresentation: z.string().optional(),
      differentials: z
        .array(
          z.object({
            diagnosis: z.string(),
            supportingFactIds: z.array(z.string()),
            opposingFactIds: z.array(z.string()),
            priority: z.number(),
          }),
        )
        .optional(),
      tests: z
        .array(
          z.object({
            name: z.string(),
            purpose: z.string(),
            priority: z.enum(['necessary', 'optional', 'avoid']),
            resultFactId: z.string().nullable().optional(),
          }),
        )
        .optional(),
      management: z
        .array(
          z.object({ action: z.string(), rationale: z.string(), priority: z.number(), safetyCritical: z.boolean() }),
        )
        .optional(),
    }),
    practiceBlueprints: z
      .array(
        z.object({
          id: z.string(),
          dimensionId: z.string(),
          stageId: stage,
          learnerLevel: z.string(),
          publicInstruction: z.string(),
          allowedVariants: z.array(z.string()),
          fixedFacts: z.array(z.string()),
          fallbackPrompt: z.string(),
          reinforcementPrompt: z.string().optional(),
          reinforcementVariantCode: z.string().optional(),
          answerSchema: z.enum(['short_text', 'evidence_grid', 'decision_cards']),
          criteria: z.array(
            z.object({
              id: z.string(),
              weight: z.number(),
              keywords: z.array(z.string()),
              feedback: z.string(),
              critical: z.boolean(),
            }),
          ),
        }),
      )
      .optional(),
  }),
  rubric: z.object({
    dimensions: z.array(
      z.object({
        id: z.string(),
        label: z.string(),
        weight: z.number(),
        stageIds: z.array(stage),
        criteria: z.array(
          z.object({
            id: z.string(),
            label: z.string(),
            keywords: z.array(z.string()),
            feedback: z.string(),
            critical: z.boolean(),
          }),
        ),
      }),
    ),
  }),
})

export const localCaseRecordSchema = z.object({
  problem: problemSchema,
  draft: localDraftSchema,
  authorOpenid: z.string().default('demo_teacher'),
  reviews: z
    .array(
      z.object({
        id: z.string(),
        reviewerOpenid: z.string(),
        reviewerName: z.string(),
        decision: z.enum(['approved', 'rejected']),
        comment: z.string(),
        problemVersion: z.number(),
        caseDigest: z.string(),
        createdAt: z.string(),
      }),
    )
    .default([]),
})
