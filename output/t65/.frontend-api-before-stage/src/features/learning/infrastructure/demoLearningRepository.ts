import type { LearningRepository } from '@/features/learning/domain/ports'
import type {
  KnowledgePoint,
  RecallReveal,
  ReviewCard,
  ReviewDashboard,
  ReviewGrade,
  ReviewItem,
} from '@/types/knowledge'
import type { StudyPathState, StudySession } from '@/types/study'
import { getSessionContext } from '@/platform/session/context'
import { AppError } from '@/types/errors'
import catalog from '@/features/content/infrastructure/pathologyCatalog.generated.json'

type DemoDialoguePort = {
  dialogues(
    limit?: number,
    offset?: number,
  ): Promise<{
    items: Array<{ id: string; goalPointCodes: string[]; phase: string; studentPhase?: string }>
    total: number
    limit: number
    offset: number
  }>
  createDialogue(input: {
    clientSessionId: string
    interactionStyle: 'guided' | 'direct'
    goalPointCodes: string[]
  }): Promise<{ session: { id: string }; participation?: { currentPhase: string; learningRouteId?: string } }>
  dialogue(id: string): Promise<{ participation?: { currentPhase: string; learningRouteId?: string } }>
}

let demoDialogues: DemoDialoguePort | undefined
export const configureDemoStudyDialogues = (dialogues: DemoDialoguePort) => {
  demoDialogues = dialogues
}

const knowledgeCatalog = (): KnowledgePoint[] =>
  catalog.map((point) => ({
    code: point.code,
    systemCode: point.system_code,
    systemLabel: point.system_label,
    topic: point.topic,
    title: point.title,
    objective: point.objective,
    learningObjectives: point.learning_objectives,
    reference: point.reference,
    cardCount: point.card_count,
    catalogVersion: point.catalog_version,
    description: point.description,
    prerequisiteCodes: point.prerequisite_codes,
    relatedCodes: point.related_codes,
    caseSlug: point.case_slug,
    catalogEvidenceStatus: point.catalog_evidence_status,
    catalogMedicalReviewStatus: point.catalog_medical_review_status,
    evidenceStatus: point.evidence_status,
    medicalReviewStatus: point.medical_review_status,
    relationshipNote: point.relationship_note,
    sources: point.sources.map((source) => ({
      sourceKey: source.source_key,
      title: source.title,
      publisher: source.publisher,
      url: source.url,
      sourceType: source.source_type,
      accessedOn: source.accessed_on,
    })),
    dependencies: point.dependencies.map((dependency) => ({
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

// Historical state remains available to the knowledge-map projection only.
const demoReviewItems: ReviewItem[] = []
const demoDueCards: ReviewCard[] = []
function currentStudentKey() {
  const session = getSessionContext()
  if (!session) throw new AppError('请先登录', { code: 'AUTH_REQUIRED', statusCode: 401 })
  if (session.role !== 'student') throw new AppError('无权执行此操作', { code: 'FORBIDDEN', statusCode: 403 })
  return session.openid
}
function retiredReview(): never {
  currentStudentKey()
  throw new AppError('独立知识巩固与到期复习流程已退役', { code: 'RETIRED_FLOW', statusCode: 409 })
}
const studyMaterial = (pointCode: string) => {
  const point = knowledgeCatalog().find((item) => item.code === pointCode)
  if (!point) throw new AppError('知识点不存在', { code: 'RESOURCE_NOT_FOUND' })
  return {
    version: 'pathology-study-v1-demo',
    pointCode,
    title: point.title,
    objective: point.objective,
    learningObjectives: point.learningObjectives,
    scenario: `围绕“${point.title}”，请先描述题目给出的观察线索，并提出需要核对的机制。`,
    background: [{ title: '观察与解释', text: '先区分已观察到的形态或情境线索，以及据此作出的推断。' }],
    example: { title: '引导实例', text: point.description ?? '' },
    remediation: [{ title: '机制回顾', text: point.description ?? '' }],
    reference: point.reference,
    evidenceStatus: point.evidenceStatus,
    medicalReviewStatus: point.medicalReviewStatus,
  }
}
export const demoLearningRepository: LearningRepository = {
  async getStudyPath(pointCode): Promise<StudyPathState> {
    const material = studyMaterial(pointCode)
    if (!demoDialogues) return { material, sessions: [], phase: 'not_started' }
    const page = await demoDialogues.dialogues(100, 0)
    const sessions: StudySession[] = []
    for (const session of page.items.filter((item) => item.goalPointCodes.includes(pointCode))) {
      const detail = await demoDialogues.dialogue(session.id)
      sessions.push({
        sessionId: session.id,
        pointCode,
        phase: detail.participation?.currentPhase || session.studentPhase || session.phase,
        learningRouteId: detail.participation?.learningRouteId,
      })
    }
    const activeSession = sessions[0]
    return {
      material,
      sessions,
      activeSession,
      phase: activeSession?.phase || 'not_started',
      learningRouteId: activeSession?.learningRouteId,
    }
  },
  async startStudyPath(input): Promise<StudyPathState> {
    if (!demoDialogues) throw new AppError('Demo 研讨服务未装配', { code: 'SERVICE_UNAVAILABLE' })
    const dialogue = await demoDialogues.createDialogue({
      clientSessionId: input.clientId,
      interactionStyle: input.interactionStyle,
      goalPointCodes: [input.pointCode],
    })
    const state = await this.getStudyPath(input.pointCode)
    const started = state.sessions.find((session) => session.sessionId === dialogue.session.id) || {
      sessionId: dialogue.session.id,
      pointCode: input.pointCode,
      phase: dialogue.participation?.currentPhase || 'problem_framing',
      learningRouteId: dialogue.participation?.learningRouteId,
    }
    const sessions = [started, ...state.sessions.filter((session) => session.sessionId !== started.sessionId)]
    return {
      ...state,
      sessions,
      activeSession: started,
      phase: started.phase,
      learningRouteId: started.learningRouteId,
    }
  },
  async getKnowledgeCatalog() {
    return knowledgeCatalog()
  },
  async getKnowledgeMap() {
    const studentKey = currentStudentKey()
    const weak = new Set(
      demoReviewItems
        .filter((item) => item.active && item.sourceId.startsWith(`${studentKey}:`))
        .map((item) => item.pointCode),
    )
    const due = new Set(
      demoDueCards.filter((item) => item.cardCode.startsWith(`${studentKey}:`)).map((item) => item.pointCode),
    )
    return knowledgeCatalog().map((point) => ({
      ...point,
      status: weak.has(point.code) ? 'weak' : due.has(point.code) ? 'due' : 'not_started',
    }))
  },
  async createExitQuiz(_topicCodes: string[]): Promise<ReviewCard[]> {
    return retiredReview()
  },
  async getReviewDashboard(): Promise<ReviewDashboard> {
    currentStudentKey()
    return { dueCount: 0, weakPointCodes: [], items: [] }
  },
  async getDueReviewQueue(): Promise<ReviewCard[]> {
    currentStudentKey()
    return []
  },
  async gradeObjectiveCard(_cardCode, _selectedOption, _confidence): Promise<ReviewGrade> {
    return retiredReview()
  },
  async revealRecallCard(_cardId: number): Promise<RecallReveal> {
    return retiredReview()
  },
  async rateRecallCard(_cardId: number, _rating: 'again' | 'hard' | 'good' | 'easy'): Promise<ReviewGrade> {
    return retiredReview()
  },
  async captureManualReviewItem(_input): Promise<ReviewItem> {
    return retiredReview()
  },
  async dismissReviewItem(_id: number): Promise<void> {
    return retiredReview()
  },
}
