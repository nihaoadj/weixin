import type { LearningRepository } from '@/features/learning/domain/ports'
import type { KnowledgePoint } from '@/types/knowledge'
import type { StudyPathState, StudySession } from '@/types/study'
import { getSessionContext } from '@/platform/session/context'
import { AppError } from '@/types/errors'

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

let readKnowledgeCatalog: (() => KnowledgePoint[]) | undefined
export const configureDemoKnowledgeCatalog = (readCatalog: () => KnowledgePoint[]) => {
  readKnowledgeCatalog = readCatalog
}

const knowledgeCatalog = (): KnowledgePoint[] => {
  if (!readKnowledgeCatalog) throw new Error('Demo knowledge catalog has not been configured')
  return readKnowledgeCatalog()
}

function requireCurrentStudent() {
  const session = getSessionContext()
  if (!session) throw new AppError('请先登录', { code: 'AUTH_REQUIRED', statusCode: 401 })
  if (session.role !== 'student') throw new AppError('无权执行此操作', { code: 'FORBIDDEN', statusCode: 403 })
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
    requireCurrentStudent()
    return knowledgeCatalog().map((point) => ({
      ...point,
      status: 'not_started' as const,
    }))
  },
}
