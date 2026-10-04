import { z } from 'zod'
import {
  apiKnowledgeCatalogSchema,
  apiKnowledgeMapSchema,
  apiExitQuizSchema,
  apiReviewDashboardSchema,
  apiReviewGradeSchema,
  apiRecallRevealSchema,
  apiReviewItemSchema,
  apiReviewQueueSchema,
} from '@/platform/contracts/learning'
import { apiRequest, encodePathSegment } from '@/platform/http/apiClient'
import type {
  KnowledgePoint,
  KnowledgeMapPoint,
  RecallReveal,
  ReviewCard,
  ReviewDashboard,
  ReviewGrade,
  ReviewItem,
} from '@/types/knowledge'
import type { StudyPathState, StudySession } from '@/types/study'

const ANALYTICS_TTL = 60_000
const STATE_TTL = 15_000
const studySectionSchema = z.object({ title: z.string(), text: z.string() })
const studyMaterialSchema = z
  .object({
    material: z
      .object({
        version: z.string(),
        point_code: z.string(),
        title: z.string(),
        objective: z.string(),
        learning_objectives: z.array(z.string().min(1)).min(2),
        scenario: z.string(),
        background: z.array(studySectionSchema),
        example: studySectionSchema,
        remediation: z.array(studySectionSchema),
        reference: z.string(),
        evidence_status: z.string().min(1),
        medical_review_status: z.string().min(1),
      })
      .strict(),
  })
  .strict()
const studySessionSchema = z
  .object({
    session_id: z.number().int().positive(),
    point_code: z.string(),
    phase: z.string(),
    learning_route_id: z.string().uuid().nullable(),
  })
  .strict()
const studyReadSchema = z
  .object({ material: studyMaterialSchema.shape.material, sessions: z.array(studySessionSchema) })
  .strict()
const mapStudyMaterial = (value: z.infer<typeof studyMaterialSchema>['material']) => ({
  version: value.version,
  pointCode: value.point_code,
  title: value.title,
  objective: value.objective,
  learningObjectives: value.learning_objectives,
  scenario: value.scenario,
  background: value.background,
  example: value.example,
  remediation: value.remediation,
  reference: value.reference,
  evidenceStatus: value.evidence_status,
  medicalReviewStatus: value.medical_review_status,
})
const mapStudySession = (value: z.infer<typeof studySessionSchema>): StudySession => ({
  sessionId: String(value.session_id),
  pointCode: value.point_code,
  phase: value.phase,
  learningRouteId: value.learning_route_id || undefined,
})

export async function getStudyPath(pointCode: string): Promise<StudyPathState> {
  const value = await apiRequest({
    path: `/learning/knowledge-points/${encodePathSegment(pointCode)}/study`,
    cacheTtlMs: STATE_TTL,
    schema: studyReadSchema,
  })
  const sessions = value.sessions.map(mapStudySession)
  const activeSession = sessions[0]
  return {
    material: mapStudyMaterial(value.material),
    sessions,
    activeSession,
    phase: activeSession?.phase || 'not_started',
    learningRouteId: activeSession?.learningRouteId,
  }
}

export async function startStudyPath(input: {
  pointCode: string
  clientId: string
  interactionStyle: 'guided' | 'direct'
}): Promise<StudyPathState> {
  const started = mapStudySession(
    await apiRequest({
      path: `/learning/knowledge-points/${encodePathSegment(input.pointCode)}/study/start`,
      method: 'POST',
      body: { client_id: input.clientId, interaction_style: input.interactionStyle },
      schema: studySessionSchema,
      invalidateCache: [`/learning/knowledge-points/${encodePathSegment(input.pointCode)}/study`],
    }),
  )
  const state = await getStudyPath(input.pointCode)
  const sessions = state.sessions.some((session) => session.sessionId === started.sessionId)
    ? state.sessions
    : [started, ...state.sessions]
  return { ...state, sessions, activeSession: started, phase: started.phase, learningRouteId: started.learningRouteId }
}

export async function getKnowledgeCatalog(): Promise<KnowledgePoint[]> {
  const catalog = await apiRequest({
    path: '/knowledge/tree',
    cacheTtlMs: ANALYTICS_TTL,
    schema: apiKnowledgeCatalogSchema,
  })
  return catalog.items.map((item) => ({
    code: item.code,
    systemCode: item.system_code,
    systemLabel: item.system_label,
    topic: item.topic,
    title: item.title,
    objective: item.objective,
    learningObjectives: item.learning_objectives,
    reference: item.reference,
    cardCount: item.card_count,
    catalogVersion: item.catalog_version,
    description: item.description,
    prerequisiteCodes: item.prerequisite_codes,
    relatedCodes: item.related_codes,
    caseSlug: item.case_slug,
    catalogEvidenceStatus: item.catalog_evidence_status,
    catalogMedicalReviewStatus: item.catalog_medical_review_status,
    evidenceStatus: item.evidence_status,
    medicalReviewStatus: item.medical_review_status,
    relationshipNote: item.relationship_note,
    sources: item.sources.map((source) => ({
      sourceKey: source.source_key,
      title: source.title,
      publisher: source.publisher,
      url: source.url,
      sourceType: source.source_type,
      accessedOn: source.accessed_on,
    })),
    dependencies: item.dependencies.map((dependency) => ({
      id: dependency.id,
      prerequisiteCode: dependency.prerequisite_code,
      dependentCode: dependency.dependent_code,
      relationKind: dependency.relation_kind,
      rationale: dependency.rationale,
      limitation: dependency.limitation,
      confidence: dependency.confidence,
      evidenceStatus: dependency.evidence_status,
      medicalReviewStatus: dependency.medical_review_status,
      sources: dependency.sources.map((source) => ({
        sourceKey: source.source_key,
        title: source.title,
        publisher: source.publisher,
        url: source.url,
        sourceType: source.source_type,
        accessedOn: source.accessed_on,
      })),
    })),
  }))
}

export async function getKnowledgeMap(): Promise<KnowledgeMapPoint[]> {
  const [catalog, map] = await Promise.all([
    getKnowledgeCatalog(),
    apiRequest({ path: '/learning/knowledge-map', cacheTtlMs: STATE_TTL, schema: apiKnowledgeMapSchema }),
  ])
  const statusByCode = new Map(map.items.map((item) => [item.code, item.status]))
  return catalog.map((point) => ({ ...point, status: statusByCode.get(point.code) || 'not_started' }))
}

function toReviewCard(value: {
  card_code: string
  point_code: string
  prompt: string
  options: string[]
  due_at?: string | null
}): ReviewCard {
  return {
    cardCode: value.card_code,
    pointCode: value.point_code,
    prompt: value.prompt,
    options: value.options,
    dueAt: value.due_at || undefined,
  }
}

function toReviewItem(value: ReturnType<typeof apiReviewItemSchema.parse>): ReviewItem {
  return {
    id: value.id,
    pointCode: value.point_code,
    cardCode: value.card_code || undefined,
    sourceType: value.source_type,
    sourceId: value.source_id,
    note: value.note,
    active: value.active,
    createdAt: value.created_at,
    updatedAt: value.updated_at,
  }
}

function toReviewDashboard(value: ReturnType<typeof apiReviewDashboardSchema.parse>): ReviewDashboard {
  return {
    dueCount: value.due_count,
    weakPointCodes: value.weak_point_codes,
    items: value.items.map(toReviewItem),
  }
}

export async function createExitQuiz(topicCodes: string[]): Promise<ReviewCard[]> {
  const value = await apiRequest({
    path: '/learning/exit-quiz',
    method: 'POST',
    body: { topic_codes: topicCodes },
    schema: apiExitQuizSchema,
  })
  return value.cards.map(toReviewCard)
}

export async function getReviewDashboard(): Promise<ReviewDashboard> {
  return toReviewDashboard(
    await apiRequest({ path: '/learning/review-dashboard', cacheTtlMs: STATE_TTL, schema: apiReviewDashboardSchema }),
  )
}

export async function getDueReviewQueue(): Promise<ReviewCard[]> {
  const value = await apiRequest({ path: '/learning/reviews/due', cacheTtlMs: STATE_TTL, schema: apiReviewQueueSchema })
  return value.map(toReviewCard)
}

export async function gradeObjectiveCard(
  cardCode: string,
  selectedOption: number,
  confidence: 'low' | 'medium' | 'high',
): Promise<ReviewGrade> {
  const value = await apiRequest({
    path: `/learning/reviews/${encodePathSegment(cardCode)}/grade`,
    method: 'POST',
    body: { selected_option: selectedOption, confidence },
    schema: apiReviewGradeSchema,
    invalidateCache: [
      '/learning/knowledge-map',
      '/learning/review-dashboard',
      '/learning/reviews/due',
      '/learning/review-items',
    ],
  })
  return {
    cardCode: value.card_code,
    correct: value.correct,
    rating: value.rating,
    explanation: value.explanation,
    dueAt: value.due_at,
  }
}

export async function revealRecallCard(cardId: number): Promise<RecallReveal> {
  const value = await apiRequest({
    path: `/learning/recall-cards/${encodePathSegment(cardId)}/reveal`,
    method: 'POST',
    schema: apiRecallRevealSchema,
  })
  return {
    cardCode: value.card_code,
    pointCode: value.point_code,
    prompt: value.prompt,
    explanation: value.explanation,
  }
}

export async function rateRecallCard(cardId: number, rating: 'again' | 'hard' | 'good' | 'easy'): Promise<ReviewGrade> {
  const value = await apiRequest({
    path: `/learning/recall-cards/${encodePathSegment(cardId)}/rate`,
    method: 'POST',
    body: { rating },
    schema: apiReviewGradeSchema,
    invalidateCache: [
      '/learning/knowledge-map',
      '/learning/review-dashboard',
      '/learning/reviews/due',
      '/learning/review-items',
    ],
  })
  return {
    cardCode: value.card_code,
    correct: value.correct,
    rating: value.rating,
    explanation: value.explanation,
    dueAt: value.due_at,
  }
}

export async function captureManualReviewItem(input: {
  pointCode: string
  sourceType: string
  sourceId: string
  note?: string
}): Promise<ReviewItem> {
  return toReviewItem(
    await apiRequest({
      path: '/learning/review-items',
      method: 'POST',
      body: {
        point_code: input.pointCode,
        source_type: input.sourceType,
        source_id: input.sourceId,
        note: input.note || '',
      },
      schema: apiReviewItemSchema,
      invalidateCache: ['/learning/knowledge-map', '/learning/review-dashboard', '/learning/review-items'],
    }),
  )
}

export async function dismissReviewItem(id: number): Promise<void> {
  await apiRequest({
    path: `/learning/review-items/${encodePathSegment(id)}/dismiss`,
    method: 'POST',
    invalidateCache: ['/learning/knowledge-map', '/learning/review-dashboard', '/learning/review-items'],
  })
}

import type { LearningRepository } from '@/features/learning/domain/ports'
export const apiLearningRepository: LearningRepository = {
  getStudyPath,
  startStudyPath,
  getKnowledgeCatalog,
  getKnowledgeMap,
  createExitQuiz,
  getReviewDashboard,
  getDueReviewQueue,
  gradeObjectiveCard,
  revealRecallCard,
  rateRecallCard,
  captureManualReviewItem,
  dismissReviewItem,
}
