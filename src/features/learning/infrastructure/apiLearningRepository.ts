import { z } from 'zod'
import { apiKnowledgeCatalogSchema, apiKnowledgeMapSchema } from '@/platform/contracts/learning'
import { apiRequest, encodePathSegment } from '@/platform/http/apiClient'
import type { KnowledgePoint, KnowledgeMapPoint } from '@/types/knowledge'
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

import type { LearningRepository } from '@/features/learning/domain/ports'
export const apiLearningRepository: LearningRepository = {
  getStudyPath,
  startStudyPath,
  getKnowledgeCatalog,
  getKnowledgeMap,
}
