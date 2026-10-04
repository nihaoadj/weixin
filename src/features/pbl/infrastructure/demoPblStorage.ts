import { z } from 'zod'

const phase = z.enum(['problem_framing', 'hypothesis', 'evidence', 'synthesis', 'completed'])
const style = z.enum(['guided', 'direct'])
const scope = z.enum(['evidence', 'private_follow_up'])
const finding = z
  .object({
    id: z.string(),
    summary: z.string(),
    evidence_message_ids: z.array(z.string()),
    evidence_summary: z.string(),
  })
  .strict()
const diagnostic = z
  .object({
    id: z.string().optional(),
    revision: z.number().int().nonnegative().optional(),
    schemaVersion: z.literal(8),
    diagnosticStatus: z.string(),
    assistantReply: z.string(),
    followUpQuestion: z.string().optional(),
    knowledgeGaps: z.array(finding.extend({ point_code: z.string(), confidence: z.enum(['low', 'medium', 'high']) })),
    reasoningIssues: z.array(
      finding.extend({ dimension_id: z.string(), issue_type: z.string(), improvement: z.string() }),
    ),
    recommendedQuestions: z.array(z.never()).optional(),
    safetyNotice: z.string().optional(),
    createdAt: z.string().optional(),
    studentId: z.string().optional(),
    studentName: z.string().optional(),
    classId: z.string().optional(),
    className: z.string().optional(),
    sessionId: z.string().optional(),
    topicCode: z.string().optional(),
    phase: phase.exclude(['completed']).optional(),
    phaseDecision: z.enum(['continue', 'advance', 'complete', 'unavailable']).optional(),
    phaseEvidenceSummary: z.string().optional(),
    phaseMissingElements: z.array(z.string()).optional(),
    sessionKind: z.enum(['classroom', 'student_initiated']).optional(),
    interactionStyle: style.optional(),
  })
  .strict()
const participation = z
  .object({
    startedAt: z.string().datetime({ offset: true }).optional(),
    messages: z.array(
      z
        .object({
          id: z.string(),
          sequence: z.number().int().positive(),
          role: z.string(),
          content: z.string(),
          interactionStyle: style,
          processing_status: z.string().optional(),
          client_message_id: z.string().nullable().optional(),
          turnScope: scope,
          replyToMessageId: z.string().optional(),
        })
        .strict(),
    ),
    diagnostic: diagnostic.optional(),
    currentPhase: phase,
    phaseStartedRevision: z.number().int().nonnegative(),
    phaseStatus: z.enum(['active', 'completed']),
    phaseCompletedAt: z.string().optional(),
    interactionStyle: style,
    styleSelectedAt: z.string().optional(),
    evidenceLocked: z.boolean(),
    conversationMode: scope,
    completionSnapshotId: z.string().optional(),
    evidenceCompletedRevision: z.number().int().nonnegative().optional(),
    learningRouteId: z.string().uuid().optional(),
    finalTestId: z.string().uuid().optional(),
    routeGenerationState: z.string().optional(),
    testGenerationState: z.string().optional(),
  })
  .strict()
const response = participation
  .extend({
    responseKind: z.enum(['evidence_assessment', 'private_follow_up']),
    turnScope: scope,
    privateFollowUp: z
      .object({
        studentMessageId: z.string(),
        assistantMessageId: z.string(),
        processingStatus: z.enum(['completed', 'unavailable']),
        safetyStatus: z.string(),
        fallbackUsed: z.boolean(),
      })
      .strict()
      .optional(),
  })
  .strict()
const session = z
  .object({
    id: z.string(),
    classId: z.string().optional(),
    topicCode: z.string(),
    status: z.string(),
    createdAt: z.string().optional(),
    closedAt: z.string().optional(),
    caseId: z.string().optional(),
    caseVersion: z.number().int().positive().optional(),
    caseContext: z
      .object({
        title: z.string(),
        opening: z
          .object({ setting: z.string(), patient_intro: z.string(), chief_complaint: z.string() })
          .strict()
          .optional(),
      })
      .strict()
      .optional(),
    goalPointCodes: z.array(z.string()),
    phase,
    studentPhase: phase.optional(),
    phaseStatus: z.enum(['active', 'completed']).optional(),
    version: z.number().int().positive(),
    sessionKind: z.enum(['classroom', 'student_initiated']),
    interactionStyle: style.optional(),
    styleSelectedAt: z.string().optional(),
    evidenceLocked: z.boolean().optional(),
    conversationMode: scope.optional(),
    completionSnapshotId: z.string().optional(),
    evidenceCompletedRevision: z.number().int().nonnegative().optional(),
  })
  .strict()
export const demoPblStateSchema = z
  .object({
    version: z.literal(1),
    classrooms: z.array(session),
    histories: z.array(z.tuple([z.string(), participation])),
    queue: z.array(diagnostic),
    responses: z.array(
      z.tuple([z.string(), z.object({ content: z.string(), interactionStyle: style, result: response }).strict()]),
    ),
    owners: z.array(z.tuple([z.string(), z.number().int().positive()])),
    sessionOwners: z.array(z.tuple([z.string(), z.string()])),
    counter: z.number().int().positive(),
  })
  .strict()
