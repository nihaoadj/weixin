import type {
  PblDiagnostic,
  PblRepository,
  PblSession,
  PblParticipation,
  PblMessageSubmission,
  PblPlan,
  PblFilters,
  InteractionStyle,
  LearningDialogueSubmission,
  PblTeacherFeedback,
  PblWorkItem,
  TeacherPblSession,
  TeacherPblDashboard,
} from '../domain/ports'
import { getSessionContext } from '@/platform/session/context'
import { storage } from '@/platform/storage/storage'
import { AppError } from '@/types/errors'
import type { ContentRepository } from '@/features/content/domain/ports'
import { demoPblStateSchema } from './demoPblStorage'
import { demoReportPage } from './demoPblReports'

type DemoLearningRouteCompletion = (input: {
  sessionId: string
  studentOpenid: string
  sourceKind: 'classroom' | 'autonomous'
  goalPointCodes: string[]
  diagnosisSummary: Record<string, unknown>
}) => Promise<{
  learningRouteId: string
  finalTestId: string
  routeGenerationState: string
  testGenerationState: string
}>
let learningRouteCompletion: DemoLearningRouteCompletion | undefined
export function configureDemoLearningRouteCompletion(handler: DemoLearningRouteCompletion): void {
  learningRouteCompletion = handler
}
type DemoClassroomRouteState = {
  routeId: string
  finalTestId: string
  studentId: number
  status: string
  resultId?: string
  score?: number
  updatedAt: string
  completedSteps?: number
  totalSteps?: number
}
let readClassroomRouteState:
  ((classId: number, sessionId: number | string) => Promise<DemoClassroomRouteState[]>) | undefined
export function configureDemoClassroomRouteStateReader(
  reader: (classId: number, sessionId: number | string) => Promise<DemoClassroomRouteState[]>,
): void {
  readClassroomRouteState = reader
}

export type DemoPblLearningNotification = {
  id: number
  sessionId: string
  actionType: 'feedback_only' | 'task_published' | 'closed'
  body: string
  createdAt: string
}

export type DemoPblStudentInsightsRecord = {
  sessionId: string
  topicCode: string
  caseTitle: string
  createdAt: string
  updatedAt: string
  learningRouteId?: string
  diagnosisCreatedAt?: string
  diagnosis?: {
    knowledgeGapCodes: string[]
    reasoningIssueCodes: string[]
  }
}

const copy = <T>(value: T): T => JSON.parse(JSON.stringify(value)) as T
const renderResponse = (opening: string, keyPoints: string[], nextStep: string) =>
  `回应\n${opening}\n\n关键要点\n${keyPoints.map((item) => `• ${item}`).join('\n')}\n\n下一步\n${nextStep}`
const actor = () => {
  const user = getSessionContext()
  if (!user) throw new AppError('请先登录', { code: 'AUTH_REQUIRED' })
  return user
}
const analysis: PblDiagnostic = {
  schemaVersion: 8,
  diagnosticStatus: 'probing',
  assistantReply: '演示追问：请说明你如何把血管变化与红肿联系起来。',
  followUpQuestion: '你认为通透性变化会造成什么表现？',
  knowledgeGaps: [],
  reasoningIssues: [],
  safetyNotice: 'Demo 合成教学演示，不代表真实 AI 诊断。',
  phase: 'problem_framing',
  phaseDecision: 'advance',
  phaseEvidenceSummary: 'Demo 使用当前阶段的新学生消息作为证据。',
  phaseMissingElements: [],
}

function retiredDemoFlow(): never {
  throw new AppError('RETIRED_FLOW：请打开学习路线及最终测试', { code: 'STATE_CONFLICT', statusCode: 409 })
}
function synthesisSeed(sessionId: string): PblParticipation {
  const answers = [
    '观察到局部红肿热痛，病理问题是急性炎症的血管反应。',
    '假设血流增加引起红热，内皮通透性升高导致渗出。',
    '蛋白丰富的渗出与局部肿胀支持通透性变化，还需结合组织形态核对。',
  ]
  return {
    messages: answers.flatMap((content, index) => [
      {
        id: `${sessionId}-student-${index}`,
        sequence: index * 2 + 1,
        role: 'student',
        content,
        interactionStyle: 'guided' as const,
        processing_status: 'completed',
        client_message_id: `${sessionId}-seed-${index}`,
        turnScope: 'evidence' as const,
      },
      {
        id: `${sessionId}-assistant-${index}`,
        sequence: index * 2 + 2,
        role: 'assistant',
        content: 'Demo 合成教学数据：本阶段证据已记录，请继续整合机制与证据。',
        interactionStyle: 'guided' as const,
        processing_status: 'completed',
        replyToMessageId: `${sessionId}-student-${index}`,
        turnScope: 'evidence' as const,
      },
    ]),
    startedAt: '2026-09-27T00:00:00Z',
    currentPhase: 'synthesis',
    phaseStartedRevision: 3,
    phaseStatus: 'active',
    interactionStyle: 'guided',
    evidenceLocked: false,
    conversationMode: 'evidence',
    diagnostic: {
      ...copy(analysis),
      revision: 3,
      phase: 'evidence',
      phaseDecision: 'advance',
      assistantReply: 'Demo 合成教学数据：前三阶段已完成，请整合观察、机制与证据，并指出尚待核对的线索。',
    },
  }
}

export class DemoPblRepository implements PblRepository {
  constructor(private readonly content: Pick<ContentRepository, 'getGuidedCasesAsync' | 'upsertProblem'>) {
    this.restore()
  }
  private classrooms: PblSession[] = [
    {
      id: 'demo-pbl-1',
      classId: '1',
      topicCode: 'pathology.inflammation',
      status: 'active',
      caseId: 'pathology.inflammation-showcase',
      caseVersion: 1,
      caseContext: { title: 'D02 Demo 合成教学数据：课堂炎症研讨' },
      goalPointCodes: ['pathology.inflammation.vascular'],
      phase: 'synthesis',
      version: 1,
      createdAt: '2026-09-27T00:00:00Z',
      sessionKind: 'classroom',
    },
    {
      id: 'demo-t44-autonomous',
      topicCode: 'pathology.inflammation',
      status: 'active',
      caseContext: { title: 'D01 Demo 合成教学数据：自主炎症研讨' },
      goalPointCodes: ['pathology.inflammation.vascular'],
      phase: 'synthesis',
      version: 1,
      createdAt: '2026-09-27T00:00:00Z',
      sessionKind: 'student_initiated',
      interactionStyle: 'guided',
    },
  ]
  private histories = new Map<string, PblParticipation>([
    ['demo_student:demo-pbl-1', synthesisSeed('demo-pbl-1')],
    ['demo_student:demo-t44-autonomous', synthesisSeed('demo-t44-autonomous')],
  ])
  private responses = new Map<
    string,
    { content: string; interactionStyle: InteractionStyle; result: PblMessageSubmission }
  >()
  private queue: PblDiagnostic[] = []
  private learning: PblPlan[] = []
  private owners = new Map<string, number>([
    ['demo_student', 1],
    ['demo_student_b', 2],
    ['演示学生·周宁', 3],
  ])
  private submissions = new Map<number, { id: string; answer: string }>()
  private dialogueSubmissions = new Map<
    string,
    { clientSubmissionId: string; snapshotId: string; classId: string; submittedAt: string }
  >()
  private feedbackBySnapshot = new Map<string, PblTeacherFeedback[]>()
  private learningNotificationsByStudent = new Map<string, DemoPblLearningNotification[]>()
  // Keep newly created diagnostics out of the seeded queue's numeric ID space.
  // Otherwise a submitted dialogue can be mistaken for a fixture and teacher feedback
  // is no longer associated with the student's actual session.
  private counter = 1000
  private notificationCounter = 1
  private sessionOwners = new Map<string, string>([['demo-t44-autonomous', 'demo_student']])
  private restore() {
    const stored = storage.readRaw('pbl:t44-demo')
    if (stored) {
      const parsed = demoPblStateSchema.safeParse(stored)
      if (parsed.success) {
        const value = parsed.data
        this.classrooms = value.classrooms
        this.histories = new Map(value.histories)
        this.responses = new Map(value.responses)
        this.queue = value.queue
        this.owners = new Map(value.owners)
        this.sessionOwners = new Map(value.sessionOwners)
        this.counter = value.counter
        return
      }
    }
    this.persist()
  }
  /** Add the reference classroom without replacing any existing participation. */
  ensureReferenceStudents() {
    const referenceSession = this.classrooms.find((item) => item.id === 'demo-pbl-1')
    if (referenceSession?.topicCode === 'pathology.inflammation') referenceSession.topicCode = '炎症：病理证据讨论'
    const names = ['李同学', '王同学', '陈同学', '周同学', '林同学', '赵同学', '孙同学', '吴同学']
    const students = names.map((name, index) => ({
      name,
      index,
      studentId: 5501 + index,
      openid: `demo_pbl_reference_${index + 1}`,
      routeId: `55000000-0000-4000-8000-${String(5501 + index).padStart(12, '0')}`,
      finalTestId: `f0000000-0000-4000-8000-${String(5501 + index).padStart(12, '0')}`,
    }))
    for (const student of students) {
      this.owners.set(student.openid, student.studentId)
      const key = `${student.openid}:demo-pbl-1`
      if (this.histories.has(key)) continue
      const snapshotId = String(student.studentId)
      const participation = synthesisSeed('demo-pbl-1')
      const diagnostic: PblDiagnostic = {
        ...copy(analysis),
        id: snapshotId,
        revision: 4,
        diagnosticStatus: 'ready',
        studentId: String(student.studentId),
        studentName: student.name,
        classId: '1',
        className: '病理学演示班',
        sessionId: 'demo-pbl-1',
        topicCode: '炎症：病理证据讨论',
        sessionKind: 'classroom',
        createdAt: '2026-10-02T00:00:00Z',
        phase: 'synthesis',
        phaseDecision: 'complete',
        assistantReply: 'Demo 合成教学数据：已结合血管扩张、通透性升高与中性粒细胞聚集解释急性炎症。',
        followUpQuestion: undefined,
        recommendedQuestions: [],
        knowledgeGaps: [
          {
            id: `gap-${snapshotId}`,
            point_code: 'pathology.inflammation.vascular',
            summary: '需进一步巩固血管通透性变化与组织水肿的联系。',
            evidence_message_ids: [`${snapshotId}-answer`],
            evidence_summary: '合成教学回答已解释主要机制，证据之间的联系尚需巩固。',
            confidence: 'medium',
          },
        ],
      }
      participation.messages.push(
        {
          id: `${snapshotId}-answer`,
          sequence: 7,
          role: 'student',
          content: '小血管扩张解释红热，通透性升高解释渗出和水肿，中性粒细胞聚集支持急性炎症。',
          interactionStyle: 'guided',
          turnScope: 'evidence',
        },
        {
          id: `${snapshotId}-reply`,
          sequence: 8,
          role: 'assistant',
          content: diagnostic.assistantReply,
          interactionStyle: 'guided',
          turnScope: 'evidence',
          replyToMessageId: `${snapshotId}-answer`,
        },
      )
      Object.assign(participation, {
        diagnostic,
        currentPhase: 'completed',
        phaseStatus: 'completed',
        phaseCompletedAt: diagnostic.createdAt,
        evidenceLocked: true,
        conversationMode: 'private_follow_up',
        completionSnapshotId: snapshotId,
        evidenceCompletedRevision: 4,
        learningRouteId: student.routeId,
        finalTestId: student.finalTestId,
        routeGenerationState: student.index < 6 ? 'generating' : 'published',
        testGenerationState: 'ready',
      })
      this.histories.set(key, participation)
      if (!this.queue.some((item) => item.id === snapshotId)) this.queue.push(diagnostic)
    }
    this.counter = Math.max(this.counter, 5600)
    this.persist()
    return students
  }
  private persist() {
    const value = demoPblStateSchema.parse({
      version: 1,
      classrooms: this.classrooms,
      histories: [...this.histories],
      responses: [...this.responses],
      queue: this.queue,
      owners: [...this.owners],
      sessionOwners: [...this.sessionOwners],
      counter: this.counter,
    })
    storage.write('pbl:t44-demo', value, demoPblStateSchema)
  }
  private studentId() {
    const key = actor().openid
    if (!this.owners.has(key)) this.owners.set(key, this.owners.size + 1)
    return this.owners.get(key)!
  }
  private teacher() {
    if (actor().role !== 'teacher') throw new AppError('仅教师可操作', { code: 'FORBIDDEN' })
    if (actor().openid !== 'demo_teacher')
      throw new AppError('资源不存在', { code: 'RESOURCE_NOT_FOUND', statusCode: 404 })
  }
  async classes() {
    actor()
    return [{ id: '1', name: '病理学演示班', code: 'demo-class' }]
  }
  async dialogues(limit = 20, offset = 0) {
    const current = actor().openid
    const items = this.classrooms
      .filter((item) => item.sessionKind === 'classroom' || this.sessionOwners.get(item.id) === current)
      .map((item) => {
        const participation = this.histories.get(`${current}:${item.id}`)
        return {
          ...item,
          studentPhase: participation?.currentPhase,
          phaseStatus: participation?.phaseStatus,
          interactionStyle: participation?.interactionStyle,
          styleSelectedAt: participation?.styleSelectedAt,
          evidenceLocked: participation?.evidenceLocked,
          conversationMode: participation?.conversationMode,
          completionSnapshotId: participation?.completionSnapshotId,
          evidenceCompletedRevision: participation?.evidenceCompletedRevision,
        }
      })
      // Keep the autonomous completion scenario visible first.
      .sort((left, right) => Number(right.id === 'demo-t44-autonomous') - Number(left.id === 'demo-t44-autonomous'))
    return { items: copy(items.slice(offset, offset + limit)), total: items.length, limit, offset }
  }
  async dialogue(id: string) {
    const current = actor().openid
    const session = this.classrooms.find(
      (item) => item.id === id && (item.sessionKind === 'classroom' || this.sessionOwners.get(item.id) === current),
    )
    if (!session) throw new AppError('研讨不存在', { code: 'RESOURCE_NOT_FOUND' })
    const participation = this.histories.get(`${current}:${id}`)
    return { session: copy(session), participation: participation ? copy(participation) : undefined }
  }
  async studentInsightsRecords(): Promise<DemoPblStudentInsightsRecord[]> {
    const user = actor()
    if (user.role !== 'student') throw new AppError('学生身份不可用', { code: 'ROLE_REQUIRED', statusCode: 403 })
    const current = user.openid
    return this.classrooms.flatMap((session) => {
      if (session.sessionKind !== 'classroom' && this.sessionOwners.get(session.id) !== current) return []
      const participation = this.histories.get(`${current}:${session.id}`)
      if (!participation) return []

      const value = participation.diagnostic
      const completedDiagnostic =
        participation.phaseStatus === 'completed' &&
        participation.currentPhase === 'completed' &&
        participation.evidenceLocked &&
        Boolean(participation.completionSnapshotId) &&
        participation.evidenceCompletedRevision != null &&
        value?.diagnosticStatus === 'ready' &&
        value.phase === 'synthesis' &&
        value.phaseDecision === 'complete' &&
        value.id === participation.completionSnapshotId &&
        value.revision === participation.evidenceCompletedRevision
      const diagnostic = completedDiagnostic && value
      const createdAt = session.createdAt || new Date(0).toISOString()
      return [
        {
          sessionId: session.id,
          topicCode: session.topicCode,
          caseTitle: session.caseContext?.title || 'PBL 研讨',
          createdAt,
          updatedAt: (diagnostic ? value?.createdAt : undefined) || participation.phaseCompletedAt || createdAt,
          learningRouteId: participation.learningRouteId,
          diagnosisCreatedAt: diagnostic ? value?.createdAt || participation.phaseCompletedAt || createdAt : undefined,
          diagnosis: diagnostic
            ? {
                knowledgeGapCodes: [...new Set(value.knowledgeGaps.map((item) => item.point_code))],
                reasoningIssueCodes: [...new Set(value.reasoningIssues.map((item) => item.dimension_id))],
              }
            : undefined,
        },
      ]
    })
  }
  async teacherDiscussionRecords() {
    this.teacher()
    return this.classrooms.flatMap((session) => {
      if (session.sessionKind !== 'classroom') return []
      return [...this.owners.entries()].flatMap(([openid, studentId]) => {
        const participation = this.histories.get(`${openid}:${session.id}`)
        if (!participation) return []
        return [
          {
            participationId: `${session.id}:${studentId}`,
            sessionId: session.id,
            classId: Number(session.classId),
            studentId,
            studentName: studentId === 1 ? '演示学生' : '演示学生（二）',
            phase: participation.currentPhase,
            status: participation.phaseStatus,
            startedAt: participation.startedAt ?? null,
            completedAt: participation.phaseCompletedAt ?? null,
          },
        ]
      })
    })
  }

  async teacherInsightsRecords() {
    const user = actor()
    if (user.role !== 'teacher') throw new AppError('仅教师可操作', { code: 'ROLE_REQUIRED', statusCode: 403 })
    if (user.openid !== 'demo_teacher') return []
    return this.classrooms.flatMap((session) => {
      if (session.sessionKind !== 'classroom') return []
      return [...this.owners.entries()].flatMap(([openid, studentId]) => {
        const participation = this.histories.get(`${openid}:${session.id}`)
        const diagnostic = participation?.diagnostic
        if (
          !participation ||
          participation.phaseStatus !== 'completed' ||
          participation.currentPhase !== 'completed' ||
          !participation.evidenceLocked ||
          !participation.completionSnapshotId ||
          participation.evidenceCompletedRevision == null ||
          diagnostic?.diagnosticStatus !== 'ready' ||
          diagnostic.phaseDecision !== 'complete' ||
          diagnostic.phase !== 'synthesis' ||
          diagnostic.id !== participation.completionSnapshotId ||
          diagnostic.revision !== participation.evidenceCompletedRevision
        )
          return []
        const project = (code: string, summary: string) => ({
          code,
          summary: summary.replace(/\s+/g, ' ').slice(0, 160),
        })
        return [
          {
            participationId: `${session.id}:${studentId}`,
            sessionId: session.id,
            classId: Number(session.classId || 1),
            className: '病理学演示班',
            studentId,
            studentName: diagnostic.studentName || (studentId === 1 ? '演示学生' : '演示学生（二）'),
            completedAt:
              diagnostic.createdAt || participation.phaseCompletedAt || session.createdAt || new Date(0).toISOString(),
            knowledgeGapCodes: [...new Set(diagnostic.knowledgeGaps.map((item) => item.point_code))],
            reasoningIssueCodes: [...new Set(diagnostic.reasoningIssues.map((item) => item.dimension_id))],
            knowledgeGaps: diagnostic.knowledgeGaps.map((item) => project(item.point_code, item.summary)),
            reasoningIssues: diagnostic.reasoningIssues.map((item) => project(item.dimension_id, item.summary)),
          },
        ]
      })
    })
  }
  async teacherFeedbackNotifications() {
    return copy(this.learningNotificationsByStudent.get(actor().openid) || [])
  }
  async createDialogue(input: {
    clientSessionId: string
    interactionStyle: InteractionStyle
    goalPointCodes: string[]
  }) {
    const current = actor().openid
    const existing = this.classrooms.find(
      (item) => this.sessionOwners.get(item.id) === current && item.id === `demo-dialogue-${input.clientSessionId}`,
    )
    if (existing) {
      const value = await this.dialogue(existing.id)
      if (existing.goalPointCodes.join('|') !== input.goalPointCodes.join('|'))
        throw new AppError('会话标识已用于其他设置', { code: 'STATE_CONFLICT' })
      return value
    }
    const points = [...new Set(input.goalPointCodes)]
    const topics = new Set(points.map((code) => code.split('.').slice(0, 2).join('.')))
    if (points.length !== 1 || input.goalPointCodes.length !== 1 || topics.size !== 1)
      throw new AppError('请选择一个知识点', { code: 'VALIDATION_ERROR' })
    const session: PblSession = {
      id: `demo-dialogue-${input.clientSessionId}`,
      classId: undefined,
      topicCode: [...topics][0],
      status: 'active',
      goalPointCodes: points,
      phase: 'problem_framing',
      version: 1,
      sessionKind: 'student_initiated',
      interactionStyle: input.interactionStyle,
      styleSelectedAt: new Date().toISOString(),
      caseContext: { title: '学生主动研讨' },
      createdAt: new Date().toISOString(),
    }
    const participation = this.emptyParticipation(input.interactionStyle)
    this.classrooms.unshift(session)
    this.sessionOwners.set(session.id, current)
    this.histories.set(`${current}:${session.id}`, participation)
    this.persist()
    return { session: copy(session), participation: copy(participation) }
  }
  async startDialogue(id: string, interactionStyle: InteractionStyle) {
    const value = await this.dialogue(id)
    if (!value.participation) {
      value.participation = this.emptyParticipation(interactionStyle)
    } else if (value.participation.phaseStatus === 'completed') {
      return copy(value)
    } else {
      value.participation.interactionStyle = interactionStyle
      value.participation.styleSelectedAt = new Date().toISOString()
    }
    this.histories.set(`${actor().openid}:${id}`, copy(value.participation))
    this.persist()
    return copy(value)
  }
  async dialogueSubmission(_id: string): Promise<LearningDialogueSubmission> {
    throw new AppError('资源不存在', { code: 'RESOURCE_NOT_FOUND', statusCode: 404 })
  }

  private emptyParticipation(interactionStyle: InteractionStyle): PblParticipation {
    return {
      startedAt: new Date().toISOString(),
      messages: [],
      currentPhase: 'problem_framing',
      phaseStartedRevision: 0,
      phaseStatus: 'active',
      interactionStyle,
      styleSelectedAt: new Date().toISOString(),
      evidenceLocked: false,
      conversationMode: 'evidence',
    }
  }
  async active() {
    actor()
    return copy(
      this.classrooms
        .filter((item) => item.sessionKind === 'classroom' || this.sessionOwners.get(item.id) === actor().openid)
        .map((item) => {
          const participation = this.histories.get(`${actor().openid}:${item.id}`)
          return {
            ...item,
            studentPhase: participation?.currentPhase ?? 'problem_framing',
            phaseStatus: participation?.phaseStatus ?? 'active',
          }
        }),
    )
  }
  async sessions(classId: string) {
    actor()
    return copy(this.classrooms.filter((s) => s.classId === classId))
  }
  async createSession(classId: string, topicCode: string, caseId: string, goals: string[]) {
    this.teacher()
    const selected = (await this.content.getGuidedCasesAsync()).find(
      (item) => item.id === caseId && item.status === 'published' && item.medicalReviewStatus === 'approved',
    )
    if (!selected || goals.length !== 1 || goals.some((code) => !selected.knowledgePointCodes?.includes(code)))
      throw new Error('请选择已审核病例及其目标')
    const value: PblSession = {
      caseVersion: selected.version,
      caseContext: { title: selected.title },
      id: `demo-${Date.now()}`,
      classId,
      topicCode,
      caseId,
      goalPointCodes: goals,
      phase: 'problem_framing',
      version: 1,
      status: 'active',
      createdAt: new Date().toISOString(),
      sessionKind: 'classroom',
    }
    this.classrooms.push(value)
    this.persist()
    return copy(value)
  }
  async closeSession(classId: string, id: string) {
    this.teacher()
    const value = this.classrooms.find((s) => s.id === id && s.classId === classId)
    if (!value) throw new Error('课堂不存在')
    value.status = 'closed'
    value.version++
    this.persist()
    return copy(value)
  }
  async participation(id: string) {
    if (actor().role !== 'student') throw new AppError('学生身份不可用', { code: 'ROLE_REQUIRED', statusCode: 403 })
    await this.dialogue(id)
    const key = `${actor().openid}:${id}`
    const existing = this.histories.get(key)
    if (existing) return copy(existing)
    const empty = this.emptyParticipation('guided')
    this.studentId()
    this.histories.set(key, copy(empty))
    this.persist()
    return copy(empty)
  }
  async message(id: string, content: string, clientMessageId: string, interactionStyle: InteractionStyle) {
    if (actor().role !== 'student') throw new AppError('学生身份不可用', { code: 'ROLE_REQUIRED', statusCode: 403 })
    await this.dialogue(id)
    const key = `${actor().openid}:${id}`,
      requestKey = `${key}:${clientMessageId}`
    const existing = this.responses.get(requestKey)
    if (existing) {
      if (existing.content !== content || existing.interactionStyle !== interactionStyle)
        throw new AppError('消息标识已用于其他内容或回应方式', { code: 'STATE_CONFLICT' })
      return copy(existing.result)
    }
    const session = this.classrooms.find((s) => s.id === id)
    if (!session) throw new AppError('研讨不存在', { code: 'RESOURCE_NOT_FOUND' })
    const value = await this.participation(id),
      mid = String(value.messages.length + 1)
    if (session.status === 'closed' && value.phaseStatus !== 'completed')
      throw new AppError('课堂已关闭', { code: 'STATE_CONFLICT' })
    if (value.phaseStatus === 'completed' || value.currentPhase === 'completed') {
      if (!value.evidenceLocked || !value.completionSnapshotId || value.evidenceCompletedRevision == null)
        throw new AppError('完成边界异常，暂时无法继续', { code: 'STATE_CONFLICT' })
      value.interactionStyle = interactionStyle
      value.styleSelectedAt = new Date().toISOString()
      value.messages.push({
        id: mid,
        sequence: value.messages.length + 1,
        role: 'student',
        content,
        client_message_id: clientMessageId,
        processing_status: 'completed',
        interactionStyle,
        turnScope: 'private_follow_up',
      })
      const assistantId = String(value.messages.length + 1)
      value.messages.push({
        id: assistantId,
        sequence: value.messages.length + 1,
        role: 'assistant',
        content: renderResponse(
          interactionStyle === 'direct'
            ? '炎症后的个人续问可以继续从机制与形态证据的联系来理解。'
            : '我们可以在不改变已完成研讨证据的前提下继续梳理这个疑问。',
          ['此前四阶段证据和诊断已经冻结。', '这段续问仅你自己可见，不提交教师或进入统计。'],
          interactionStyle === 'direct'
            ? '请指出你还想展开的具体机制或形态表现。'
            : '你现在最想澄清的是机制、形态，还是两者之间的联系？',
        ),
        interactionStyle,
        turnScope: 'private_follow_up',
        replyToMessageId: mid,
      })
      this.histories.set(key, copy(value))
      const result: PblMessageSubmission = {
        ...copy(value),
        responseKind: 'private_follow_up',
        turnScope: 'private_follow_up',
        privateFollowUp: {
          studentMessageId: mid,
          assistantMessageId: assistantId,
          processingStatus: 'completed',
          safetyStatus: 'standard',
          fallbackUsed: false,
        },
      }
      this.responses.set(requestKey, { content, interactionStyle, result: copy(result) })
      this.persist()
      return result
    }
    const phase = value.currentPhase
    value.interactionStyle = interactionStyle
    value.styleSelectedAt = new Date().toISOString()
    value.messages.push({
      id: mid,
      sequence: value.messages.length + 1,
      role: 'student',
      content,
      client_message_id: clientMessageId,
      processing_status: 'completed',
      interactionStyle,
      turnScope: 'evidence',
    })
    const opening =
      interactionStyle === 'direct'
        ? '炎症表现需要结合局部血流增加与血管通透性变化来解释。'
        : '你已经提出了当前病理问题，可以继续把观察与机制连接起来。'
    const nextStep =
      phase === 'synthesis'
        ? '研讨已完成，可查看后续学习安排。'
        : interactionStyle === 'direct'
          ? '请用自己的话说明其中一项机制怎样产生当前表现。'
          : '请指出当前最关键的形态线索，并说明它支持哪种机制。'
    const assistantReply = renderResponse(
      opening,
      ['Demo 合成教学演示，只用于验证界面合同。', '阶段证据仍只来自你的消息。'],
      nextStep,
    )
    const diagnostic: PblDiagnostic =
      phase !== 'synthesis'
        ? copy(analysis)
        : {
            ...copy(analysis),
            id: String(this.counter++),
            revision: value.messages.length,
            diagnosticStatus: 'ready',
            assistantReply,
            followUpQuestion: undefined,
            studentId: String(this.studentId()),
            studentName: '演示学生',
            classId: session.classId,
            className: '病理学演示班',
            sessionId: id,
            topicCode: session.topicCode,
            sessionKind: session.sessionKind,
            interactionStyle,
            phase: 'synthesis',
            phaseDecision: 'complete',
            phaseEvidenceSummary: 'Demo 合成回答整合了机制、证据与剩余疑问。',
            phaseMissingElements: [],
            knowledgeGaps: [
              {
                id: 'gap',
                point_code: session.goalPointCodes[0],
                summary: '血管变化的解释不完整',
                evidence_message_ids: [mid],
                evidence_summary: 'Demo 合成依据，仅演示核对流程。',
                confidence: 'medium',
              },
            ],
            recommendedQuestions: [],
          }
    diagnostic.schemaVersion = 8
    diagnostic.assistantReply = assistantReply
    diagnostic.interactionStyle = interactionStyle
    diagnostic.followUpQuestion = phase === 'synthesis' ? undefined : nextStep
    if (phase !== 'synthesis') {
      const phases = ['problem_framing', 'hypothesis', 'evidence', 'synthesis'] as const
      diagnostic.phase = phase
      diagnostic.phaseDecision = 'advance'
      diagnostic.phaseEvidenceSummary = 'Demo 当前回答满足本阶段目标。'
      value.currentPhase = phases[phases.indexOf(phase as (typeof phases)[number]) + 1]
      value.phaseStartedRevision += 1
    } else {
      value.currentPhase = 'completed'
      value.phaseStatus = 'completed'
      value.phaseCompletedAt = new Date().toISOString()
      value.phaseStartedRevision += 1
      value.evidenceLocked = true
      value.conversationMode = 'private_follow_up'
      value.completionSnapshotId = diagnostic.id
      value.evidenceCompletedRevision = diagnostic.revision
      if (learningRouteCompletion) {
        const locator = await learningRouteCompletion({
          sessionId: id,
          studentOpenid: actor().openid,
          sourceKind: session.sessionKind === 'classroom' ? 'classroom' : 'autonomous',
          goalPointCodes: session.goalPointCodes,
          diagnosisSummary: {
            outcome: diagnostic.assistantReply,
            knowledge_gaps: diagnostic.knowledgeGaps,
            reasoning_issues: diagnostic.reasoningIssues,
          },
        })
        value.learningRouteId = locator.learningRouteId
        value.finalTestId = locator.finalTestId
        value.routeGenerationState = locator.routeGenerationState
        value.testGenerationState = locator.testGenerationState
      }
    }
    value.diagnostic = diagnostic
    value.messages.push({
      id: String(value.messages.length + 1),
      sequence: value.messages.length + 1,
      role: 'assistant',
      content: diagnostic.assistantReply,
      interactionStyle,
      turnScope: 'evidence',
      replyToMessageId: mid,
    })
    this.histories.set(key, copy(value))
    const result: PblMessageSubmission = {
      ...copy(value),
      responseKind: 'evidence_assessment',
      turnScope: 'evidence',
    }
    this.responses.set(requestKey, { content, interactionStyle, result: copy(result) })
    if (diagnostic.diagnosticStatus === 'ready' && session.sessionKind === 'classroom') {
      for (const prior of this.queue.filter(
        (item) => item.studentId === diagnostic.studentId && item.sessionId === id,
      )) {
        for (const suggestion of prior.recommendedQuestions ?? [])
          if (['proposed', 'edited'].includes(suggestion.status)) suggestion.status = 'superseded'
      }
      this.queue.unshift(copy(diagnostic))
    }
    this.persist()
    return copy(result)
  }
  async diagnostics(filters: PblFilters = {}) {
    this.teacher()
    const seen = new Set<string>()
    const items = this.queue.filter((d) => {
      const key = `${d.sessionId}:${d.studentId}`
      if (seen.has(key)) return false
      seen.add(key)
      return (
        (!filters.classId || d.classId === filters.classId) &&
        (!filters.sessionId || d.sessionId === filters.sessionId) &&
        (!filters.studentId || d.studentId === filters.studentId) &&
        (!filters.status || d.recommendedQuestions?.some((s) => s.status === filters.status))
      )
    })
    return { items: copy(items.slice(filters.offset || 0, (filters.offset || 0) + 20)), total: items.length }
  }
  async workItems(filters: PblFilters & { source?: PblWorkItem['source']; workStatus?: PblWorkItem['status'] } = {}) {
    const page = await this.diagnostics({
      classId: filters.classId,
      sessionId: filters.sessionId,
      studentId: filters.studentId,
      status: filters.status,
    })
    const allItems: PblWorkItem[] = page.items
      .map((item): PblWorkItem => {
        const feedbacks = this.feedbackBySnapshot.get(item.id || '') || []
        const published = item.recommendedQuestions?.some((question) => question.status === 'published')
        const closed = feedbacks.some((feedback) => feedback.actionType === 'closed')
        const status: PblWorkItem['status'] = published
          ? 'task_published'
          : closed
            ? 'closed'
            : feedbacks.length
              ? 'responded'
              : 'pending'
        return {
          snapshotId: item.id || '',
          learningRouteId: [...this.histories.values()].find((value) => value.completionSnapshotId === item.id)
            ?.learningRouteId,
          finalTestId: [...this.histories.values()].find((value) => value.completionSnapshotId === item.id)
            ?.finalTestId,
          sessionId: item.sessionId || '',
          source: item.sessionKind === 'student_initiated' ? 'student_submission' : 'classroom_diagnostic',
          status,
          student: { id: item.studentId || '', name: item.studentName || '演示学生' },
          class: { id: item.classId || '1', name: item.className || '病理学演示班' },
          topic: item.topicCode || '',
          enteredAt: item.createdAt,
          lastActivityAt: feedbacks.at(-1)?.createdAt || item.createdAt,
          knowledgeGapCount: item.knowledgeGaps.length,
          reasoningIssueCount: item.reasoningIssues.length,
          readOnly: item.sessionKind === 'student_initiated',
          nextAction:
            item.sessionKind === 'student_initiated'
              ? '历史共享记录，仅供查看'
              : status === 'pending'
                ? '审阅并反馈'
                : status === 'task_published'
                  ? '查看学习进展'
                  : status === 'closed'
                    ? '已关闭'
                    : '发送补充反馈',
        }
      })
      .filter((item) => !filters.source || item.source === filters.source)
    const summary: Record<PblWorkItem['status'], number> = { pending: 0, responded: 0, task_published: 0, closed: 0 }
    allItems.forEach((item) => {
      summary[item.status] += 1
    })
    const items = allItems.filter((item) => !filters.workStatus || item.status === filters.workStatus)
    const offset = filters.offset || 0
    return { items: copy(items.slice(offset, offset + 20)), total: items.length, summary }
  }
  async workItem(snapshotId: string) {
    const diagnostic = await this.diagnostic(snapshotId)
    const items = await this.workItems()
    return {
      workItem: items.items.find((item) => item.snapshotId === snapshotId),
      diagnostic,
      feedbacks: copy(this.feedbackBySnapshot.get(snapshotId) || []),
    }
  }
  async diagnostic(id: string) {
    this.teacher()
    const found = this.queue.find((d) => d.id === id)
    if (!found) throw new Error('诊断不存在')
    return copy(found)
  }
  async revisions(id: string) {
    const found = await this.diagnostic(id)
    return copy(this.queue.filter((d) => d.studentId === found.studentId && d.sessionId === found.sessionId))
  }
  async plans(): Promise<PblPlan[]> {
    actor()
    return []
  }

  async teacherSessions(filters: { classId?: string; status?: string; offset?: number } = {}) {
    this.teacher()
    const items = this.classrooms
      .filter(
        (item) =>
          item.sessionKind === 'classroom' &&
          (!filters.classId || item.classId === filters.classId) &&
          (!filters.status || item.status === filters.status),
      )
      .map((item): TeacherPblSession => ({
        id: item.id,
        classId: item.classId || '1',
        className: `班级 ${item.classId || '1'}`,
        topicCode: item.topicCode,
        status: item.status,
        createdAt: item.createdAt,
        closedAt: item.closedAt,
      }))
    return { items: copy(items.slice(filters.offset ?? 0, (filters.offset ?? 0) + 20)), total: items.length }
  }
  async dashboard(classId: string, sessionId: string): Promise<TeacherPblDashboard> {
    this.teacher()
    const session = this.classrooms.find((item) => item.id === sessionId && item.classId === classId)
    if (!session) throw new AppError('课堂不存在', { code: 'RESOURCE_NOT_FOUND' })
    const workItems = await this.workItems({ classId, sessionId })
    const routeFacts = (await readClassroomRouteState?.(Number(classId), sessionId)) || []
    const routesByStudent = new Map(routeFacts.map((item) => [String(item.studentId), item]))
    const students = [...this.owners.entries()].flatMap(([openid, studentId]) => {
      const participation = this.histories.get(`${openid}:${sessionId}`)
      const diagnostic = this.queue.find(
        (item) =>
          item.studentId === String(studentId) &&
          item.sessionId === sessionId &&
          item.classId === classId &&
          item.sessionKind === 'classroom',
      )
      const route = routesByStudent.get(String(studentId))
      if (!participation && !diagnostic && !route) return []
      const snapshotId = participation?.diagnostic?.id || diagnostic?.id
      return [
        {
          studentId: String(studentId),
          studentName: diagnostic?.studentName || `演示学生 ${studentId}`,
          currentPhase: participation?.currentPhase || (diagnostic ? 'completed' : 'problem_framing'),
          phaseStatus: participation?.phaseStatus || 'active',
          lastActivityAt: route?.updatedAt,
          snapshotId,
          workItemStatus: snapshotId
            ? workItems.items.find((item) => item.snapshotId === snapshotId)?.status
            : undefined,
          taskProgress: {
            completed: route?.completedSteps || 0,
            total: route?.totalSteps || 0,
          },
          learningRouteId: route?.routeId,
          finalTestId: route?.finalTestId,
          resultId: route?.resultId,
          routeStatus: route?.status,
          score: route?.score,
        },
      ]
    })
    const completedRoutes = routeFacts.filter((item) => item.resultId)
    const scores = completedRoutes
      .map((item) => item.score)
      .filter((value): value is number => typeof value === 'number')
    const phaseCounts = students.reduce<Record<string, number>>((counts, student) => {
      counts[student.currentPhase] = (counts[student.currentPhase] || 0) + 1
      return counts
    }, {})
    return {
      session: { id: sessionId, classId, status: session.status },
      summary: {
        participants: students.length,
        diagnoses: students.filter((student) => student.snapshotId).length,
        publishedRoutes: routeFacts.filter((item) => !['generating', 'generation_failed'].includes(item.status)).length,
        completedRoutes: completedRoutes.length,
        completionRate: routeFacts.length ? Math.round((completedRoutes.length * 1000) / routeFacts.length) / 10 : null,
        averageScore: scores.length
          ? Math.round((scores.reduce((total, score) => total + score, 0) * 10) / scores.length) / 10
          : null,
        phaseCounts,
      },
      students,
    }
  }
  async submitTask(
    _taskId: number,
    _submissionId: string,
    _answer: { text?: string; selected_option?: number },
  ): Promise<PblPlan> {
    return retiredDemoFlow()
  }

  async reports(limit = 20, offset = 0) {
    actor()
    return demoReportPage([], limit, offset)
  }

  async report(_sessionId: string): Promise<never> {
    throw new AppError('资源不存在', { code: 'RESOURCE_NOT_FOUND', statusCode: 404 })
  }
}
