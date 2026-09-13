import type {
  PblDiagnostic,
  PblRepository,
  PblSession,
  PblSuggestion,
  PblParticipation,
  PblPlan,
  PblTargets,
  PblFilters,
  PblTask,
  InteractionStyle,
  LearningDialogueSubmission,
  PblTeacherFeedback,
  PblWorkItem,
  TeacherPblSession,
  TeacherPblDashboard,
  PblFollowUp,
  PblFollowUpStatus,
} from '../domain/ports'
import { demoReportDetail, demoReportPage } from './demoPblReports'
import { getSessionContext } from '@/platform/session/context'
import { AppError } from '@/types/errors'
import type { ContentRepository } from '@/features/content/domain/ports'

export type DemoPblLearningNotification = {
  id: number
  sessionId: string
  actionType: 'feedback_only' | 'task_published' | 'closed'
  body: string
  createdAt: string
}

const copy = <T>(value: T): T => JSON.parse(JSON.stringify(value)) as T
const actor = () => {
  const user = getSessionContext()
  if (!user) throw new AppError('请先登录', { code: 'AUTH_REQUIRED' })
  return user
}
const analysis: PblDiagnostic = {
  schemaVersion: 4,
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

const demoTeacherDiagnostics: PblDiagnostic[] = [
  {
    id: '90001',
    revision: 1,
    schemaVersion: 4,
    diagnosticStatus: 'ready',
    assistantReply: '已整理为待教师审阅的合成诊断建议，供演示教师反馈与采用发布流程。',
    knowledgeGaps: [
      {
        id: 'demo-gap-vascular',
        point_code: 'pathology.inflammation.vascular',
        summary: '能描述局部红肿，但尚未把血管通透性增加与渗出形成明确连接。',
        evidence_message_ids: ['demo-evidence-vascular'],
        evidence_summary: '学生提到血流增加，却没有说明液体和蛋白外渗的机制。',
        confidence: 'medium',
      },
    ],
    reasoningIssues: [
      {
        id: 'demo-reasoning-evidence',
        dimension_id: 'evidence_reasoning',
        issue_type: 'missing_link',
        summary: '观察到的表现与病理机制之间缺少逐项证据连接。',
        evidence_message_ids: ['demo-evidence-vascular'],
        evidence_summary: '固定证据摘要仅用于演示诊断处置界面。',
        improvement: '先分别列出血流、通透性与渗出，再说明每项如何支持解释。',
      },
    ],
    recommendedQuestions: [
      {
        id: '900011',
        title: '说明炎症中血管反应与渗出的关系',
        prompt: '请分别说明血流变化和血管通透性增加如何共同造成局部红肿与渗出。',
        linkedFindings: ['demo-gap-vascular', 'demo-reasoning-evidence'],
        status: 'proposed',
        version: 1,
      },
    ],
    safetyNotice: 'Demo 合成教学记录，仅用于界面与流程演示，不代表真实 AI 诊断或医学建议。',
    createdAt: '2026-09-10T08:30:00.000Z',
    studentId: '1',
    studentName: '演示学生·林晓',
    classId: '1',
    className: '病理学演示班',
    sessionId: 'demo-pbl-1',
    topicCode: 'pathology.inflammation',
    phase: 'synthesis',
    phaseDecision: 'complete',
    phaseEvidenceSummary: '学生已经完成综合解释，但血管反应与渗出机制的证据链仍需教师带教。',
    phaseMissingElements: [],
    sessionKind: 'classroom',
    interactionStyle: 'guided',
  },
  {
    id: '90002',
    revision: 1,
    schemaVersion: 4,
    diagnosticStatus: 'ready',
    assistantReply: '该合成诊断已由教师采用并形成两轮正式任务，用于展示后续学习跟进。',
    knowledgeGaps: [
      {
        id: 'demo-gap-published',
        point_code: 'pathology.inflammation.vascular',
        summary: '对血管通透性变化的机制解释仍不完整。',
        evidence_message_ids: ['demo-evidence-published'],
        evidence_summary: '固定证据摘要仅用于演示正式任务的来源关系。',
        confidence: 'medium',
      },
    ],
    reasoningIssues: [],
    recommendedQuestions: [
      {
        id: '900021',
        title: '核对炎症中血管通透性改变',
        prompt: '结合形态观察，说明血管通透性增加如何影响渗出。',
        linkedFindings: ['demo-gap-published'],
        status: 'published',
        version: 2,
        problemId: 'demo-pbl-question-900021',
      },
    ],
    safetyNotice: 'Demo 合成教学记录，仅用于界面与流程演示，不代表真实 AI 诊断或医学建议。',
    createdAt: '2026-09-09T08:30:00.000Z',
    studentId: '3',
    studentName: '演示学生·周宁',
    classId: '1',
    className: '病理学演示班',
    sessionId: 'demo-pbl-1',
    topicCode: 'pathology.inflammation',
    phase: 'synthesis',
    phaseDecision: 'complete',
    phaseEvidenceSummary: '固定合成诊断已用于创建正式任务。',
    phaseMissingElements: [],
    sessionKind: 'classroom',
    interactionStyle: 'guided',
  },
]

const demoFollowUpPlan: PblPlan = {
  id: 9001,
  student_id: 3,
  source_type: 'pbl_suggestion',
  source_id: 900021,
  source_context: {
    teacher_id: 1,
    class_id: 1,
    class_name: '病理学演示班',
    session_id: 1,
    snapshot_id: 90002,
    suggestion_id: 900021,
    point_codes: ['pathology.inflammation.vascular'],
    dimension_ids: ['evidence_reasoning'],
    topic_code: 'pathology.inflammation',
  },
  status: 'completed',
  verification_status: 'needs_reinforcement',
  verification_note: '两轮正式任务已完成，血管通透性与渗出的证据连接仍需教师补充带教。',
  verified_at: '2026-09-11T08:30:00.000Z',
  version: 2,
  due_at: '2026-09-12T08:30:00.000Z',
  current_cycle: 2,
  max_cycles: 2,
  automation_exhausted: true,
  decision_policy_version: 'pbl-mastery-v1',
  decision_basis: {
    result: 'needs_reinforcement',
    cycle: 2,
    offline_support_required: true,
    failed_targets: [
      {
        target_type: 'knowledge_gap',
        target_code: 'pathology.inflammation.vascular',
        label: '炎症的血管反应',
      },
    ],
    checks: [
      {
        target_type: 'knowledge_gap',
        target_code: 'pathology.inflammation.vascular',
        threshold: 100,
        score: 60,
        evidence_present: true,
        passed: false,
      },
    ],
  },
  evaluated_at: '2026-09-11T08:30:00.000Z',
  evaluations: [
    {
      cycle_number: 1,
      policy_version: 'pbl-mastery-v1',
      result: 'next_cycle_activated',
      checks: [
        {
          target_type: 'knowledge_gap',
          target_code: 'pathology.inflammation.vascular',
          threshold: 100,
          score: 60,
          evidence_present: true,
          passed: false,
        },
      ],
      failed_targets: [
        {
          target_type: 'knowledge_gap',
          target_code: 'pathology.inflammation.vascular',
          label: '炎症的血管反应',
        },
      ],
      automation_exhausted: false,
      record_source: 'system',
      evaluated_at: '2026-09-10T08:30:00.000Z',
    },
    {
      cycle_number: 2,
      policy_version: 'pbl-mastery-v1',
      result: 'needs_reinforcement',
      checks: [
        {
          target_type: 'knowledge_gap',
          target_code: 'pathology.inflammation.vascular',
          threshold: 100,
          score: 60,
          evidence_present: true,
          passed: false,
        },
      ],
      failed_targets: [
        {
          target_type: 'knowledge_gap',
          target_code: 'pathology.inflammation.vascular',
          label: '炎症的血管反应',
        },
      ],
      automation_exhausted: true,
      record_source: 'system',
      evaluated_at: '2026-09-11T08:30:00.000Z',
    },
  ],
  tasks: [
    {
      id: 90011,
      position: 1,
      task_type: 'discussion',
      status: 'completed',
      problem_id: null,
      public_definition: {
        prompt: '先用观察到的形态表现说明血管反应，再补充不确定之处。',
        target_label: '正式讨论',
        reference: 'Demo 合成教学资料；仅用于界面合同演示。',
      },
      result: {
        score: null,
        feedback: '已提交合成反思证据。',
        evidence: ['Demo 第一轮讨论证据'],
        answer: { text: '我会区分血流增加与血管通透性增加的表现。' },
        submitted_at: '2026-09-10T08:30:00.000Z',
      },
      cycle_number: 1,
      target_type: 'discussion',
      target_code: 'discussion',
      variant_code: 'demo:900021:discussion:v1',
    },
    {
      id: 90012,
      position: 2,
      task_type: 'retest',
      status: 'completed',
      problem_id: null,
      public_definition: {
        prompt: '当新证据削弱原解释时，应怎样处理？',
        options: ['比较新证据并修订假设', '忽略差异'],
        point_code: 'pathology.inflammation.vascular',
        target_label: '炎症的血管反应',
        reference: 'Demo 合成教学资料；仅用于界面合同演示。',
      },
      result: {
        score: 60,
        feedback: '仍需把通透性增加与渗出逐项连接。',
        evidence: ['Demo 第一轮再测作答'],
        answer: { selected_option: 1 },
        submitted_at: '2026-09-10T08:31:00.000Z',
      },
      cycle_number: 1,
      target_type: 'knowledge_gap',
      target_code: 'pathology.inflammation.vascular',
      variant_code: 'pathology.inflammation.vascular.retest',
    },
    {
      id: 90013,
      position: 3,
      task_type: 'discussion',
      status: 'completed',
      problem_id: null,
      public_definition: {
        prompt: '第二轮：先写出反例，再修订血管反应与渗出的解释。',
        target_label: '正式讨论',
        reference: 'Demo 合成教学资料；仅用于界面合同演示。',
      },
      result: {
        score: null,
        feedback: '已提交第二轮合成反思证据。',
        evidence: ['Demo 第二轮讨论证据'],
        answer: { text: '我会先核对反例是否能由血流变化单独解释。' },
        submitted_at: '2026-09-11T08:30:00.000Z',
      },
      cycle_number: 2,
      target_type: 'discussion',
      target_code: 'discussion',
      variant_code: 'demo:900021:discussion:v2',
    },
    {
      id: 90014,
      position: 4,
      task_type: 'retest',
      status: 'completed',
      problem_id: null,
      public_definition: {
        prompt: '第二轮再测：新证据削弱原假设时应怎样处理？',
        options: ['降低原假设优先级并继续核对', '忽略新证据'],
        point_code: 'pathology.inflammation.vascular',
        target_label: '炎症的血管反应',
        reference: 'Demo 合成教学资料；仅用于界面合同演示。',
      },
      result: {
        score: 60,
        feedback: '两轮后仍需教师补充反馈。',
        evidence: ['Demo 第二轮再测作答'],
        answer: { selected_option: 1 },
        submitted_at: '2026-09-11T08:31:00.000Z',
      },
      cycle_number: 2,
      target_type: 'knowledge_gap',
      target_code: 'pathology.inflammation.vascular',
      variant_code: 'pathology.inflammation.vascular.retest.v2',
    },
  ],
}

export class DemoPblRepository implements PblRepository {
  constructor(private readonly content: Pick<ContentRepository, 'getGuidedCasesAsync' | 'upsertProblem'>) {}
  private classrooms: PblSession[] = [
    {
      id: 'demo-pbl-1',
      classId: '1',
      topicCode: 'pathology.inflammation',
      status: 'active',
      caseId: 'pathology.inflammation-showcase',
      caseVersion: 1,
      caseContext: { title: '炎症：血管反应讨论' },
      goalPointCodes: ['pathology.inflammation.vascular'],
      phase: 'problem_framing',
      version: 1,
      createdAt: new Date().toISOString(),
      sessionKind: 'classroom',
    },
  ]
  private histories = new Map<string, PblParticipation>()
  private responses = new Map<string, PblParticipation>()
  private queue: PblDiagnostic[] = copy(demoTeacherDiagnostics)
  private learning: PblPlan[] = [copy(demoFollowUpPlan)]
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
  private sessionOwners = new Map<string, string>()
  private studentId() {
    const key = actor().openid
    if (!this.owners.has(key)) this.owners.set(key, this.owners.size + 1)
    return this.owners.get(key)!
  }
  private teacher() {
    if (actor().role !== 'teacher') throw new AppError('仅教师可操作', { code: 'FORBIDDEN' })
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
        }
      })
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
  async teacherFeedbackNotifications() {
    return copy(this.learningNotificationsByStudent.get(actor().openid) || [])
  }
  async createDialogue(input: {
    clientSessionId: string
    classId?: string
    interactionStyle: InteractionStyle
    goalPointCodes: string[]
  }) {
    const current = actor().openid
    const existing = this.classrooms.find(
      (item) => this.sessionOwners.get(item.id) === current && item.id === `demo-dialogue-${input.clientSessionId}`,
    )
    if (existing) {
      const value = await this.dialogue(existing.id)
      if (
        existing.classId !== input.classId ||
        existing.goalPointCodes.join('|') !== input.goalPointCodes.join('|') ||
        value.participation?.interactionStyle !== input.interactionStyle
      )
        throw new AppError('会话标识已用于其他设置', { code: 'STATE_CONFLICT' })
      return value
    }
    const points = [...new Set(input.goalPointCodes)]
    const topics = new Set(points.map((code) => code.split('.').slice(0, 2).join('.')))
    if ((input.classId && input.classId !== '1') || points.length < 1 || points.length > 3 || topics.size !== 1)
      throw new AppError('请选择同一主题下 1～3 个知识点', { code: 'VALIDATION_ERROR' })
    const session: PblSession = {
      id: `demo-dialogue-${input.clientSessionId}`,
      classId: input.classId,
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
    return { session: copy(session), participation: copy(participation) }
  }
  async startDialogue(id: string, interactionStyle: InteractionStyle) {
    const value = await this.dialogue(id)
    if (value.participation && value.participation.interactionStyle !== interactionStyle)
      throw new AppError('本次研讨的沟通方式已经确定', { code: 'STATE_CONFLICT' })
    if (!value.participation) {
      value.participation = this.emptyParticipation(interactionStyle)
      this.histories.set(`${actor().openid}:${id}`, copy(value.participation))
    }
    return copy(value)
  }
  async dialogueSubmission(id: string) {
    const value = await this.dialogue(id)
    if (value.session.sessionKind !== 'student_initiated' || value.participation?.currentPhase !== 'completed')
      throw new AppError('完成四阶段研讨后可提交', { code: 'STATE_CONFLICT' })
    const diagnostic = value.participation.diagnostic
    if (!diagnostic?.id) throw new AppError('尚未形成可提交诊断', { code: 'STATE_CONFLICT' })
    const submitted = this.dialogueSubmissions.get(id)
    const feedbacks = this.feedbackBySnapshot.get(diagnostic.id) || []
    const teacherStatus: LearningDialogueSubmission['teacherStatus'] = diagnostic.recommendedQuestions?.some(
      (item) => item.status === 'published',
    )
      ? 'task_published'
      : feedbacks.some((item) => item.actionType === 'closed')
        ? 'closed'
        : feedbacks.length
          ? 'responded'
          : submitted
            ? 'pending'
            : undefined
    return {
      sessionId: id,
      snapshotId: diagnostic.id,
      knowledgeGaps: diagnostic.knowledgeGaps,
      reasoningIssues: diagnostic.reasoningIssues,
      evidenceSummary: diagnostic.phaseEvidenceSummary || '',
      questions: (diagnostic.recommendedQuestions || []).map((item) => ({
        id: item.id,
        title: item.title,
        prompt: item.prompt,
      })),
      submission: submitted
        ? {
            sessionId: id,
            snapshotId: submitted.snapshotId,
            classId: submitted.classId,
            source: 'student',
            submittedAt: submitted.submittedAt,
          }
        : undefined,
      teacherStatus,
      feedbacks: copy(feedbacks),
      nextAction:
        teacherStatus === 'task_published'
          ? '进入正式任务'
          : teacherStatus === 'responded'
            ? '按反馈开启新一轮研讨'
            : teacherStatus === 'closed'
              ? '查看教师结论'
              : submitted
                ? '等待教师审阅'
                : '完成后可提交给教师',
    }
  }
  async submitDialogue(input: { id: string; snapshotId: string; classId: string; clientSubmissionId: string }) {
    if (input.classId !== '1') throw new AppError('请选择本人有效班级', { code: 'RESOURCE_NOT_FOUND' })
    const preview = await this.dialogueSubmission(input.id)
    if (preview.snapshotId !== input.snapshotId)
      throw new AppError('诊断版本已经改变，请重新预览', { code: 'STATE_CONFLICT' })
    const existing = this.dialogueSubmissions.get(input.id)
    if (
      existing &&
      (existing.clientSubmissionId !== input.clientSubmissionId ||
        existing.snapshotId !== input.snapshotId ||
        existing.classId !== input.classId)
    )
      throw new AppError('本轮已提交，不能改投', { code: 'STATE_CONFLICT' })
    if (!existing)
      this.dialogueSubmissions.set(input.id, {
        clientSubmissionId: input.clientSubmissionId,
        snapshotId: input.snapshotId,
        classId: input.classId,
        submittedAt: new Date().toISOString(),
      })
    if (!this.queue.some((item) => item.id === preview.snapshotId)) {
      const diagnostic = (await this.dialogue(input.id)).participation?.diagnostic
      if (diagnostic?.id === preview.snapshotId)
        this.queue.unshift(
          copy({
            ...diagnostic,
            classId: input.classId,
            className: '病理学演示班',
          }),
        )
    }
    const diagnostic = (await this.dialogue(input.id)).participation?.diagnostic
    if (diagnostic && !this.queue.some((item) => item.id === diagnostic.id)) this.queue.unshift(copy(diagnostic))
    return this.dialogueSubmission(input.id)
  }
  private emptyParticipation(interactionStyle: InteractionStyle): PblParticipation {
    return {
      messages: [],
      currentPhase: 'problem_framing',
      phaseStartedRevision: 0,
      phaseStatus: 'active',
      interactionStyle,
      styleSelectedAt: new Date().toISOString(),
    }
  }
  async active() {
    actor()
    return copy(
      this.classrooms.map((item) => {
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
    if (
      !selected ||
      goals.length < 1 ||
      goals.length > 3 ||
      goals.some((code) => !selected.knowledgePointCodes?.includes(code))
    )
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
    return copy(value)
  }
  async closeSession(classId: string, id: string) {
    const value = this.classrooms.find((s) => s.id === id && s.classId === classId)
    if (!value) throw new Error('课堂不存在')
    value.status = 'closed'
    value.version++
    return copy(value)
  }
  async participation(id: string) {
    const key = `${actor().openid}:${id}`
    const existing = this.histories.get(key)
    if (existing) return copy(existing)
    const empty = this.emptyParticipation('guided')
    this.histories.set(key, copy(empty))
    return copy(empty)
  }
  async message(id: string, content: string, clientMessageId: string) {
    const key = `${actor().openid}:${id}`,
      requestKey = `${key}:${clientMessageId}`
    const existing = this.responses.get(requestKey)
    if (existing) return copy(existing)
    const session = this.classrooms.find((s) => s.id === id)
    if (!session || session.status === 'closed') throw new Error('课堂已关闭')
    const value = await this.participation(id),
      mid = String(value.messages.length + 1)
    if (value.phaseStatus === 'completed' || value.currentPhase === 'completed')
      throw new Error('四阶段讨论已完成，不能继续发送新消息')
    const phase = value.currentPhase
    value.messages.push({
      id: mid,
      sequence: value.messages.length + 1,
      role: 'student',
      content,
      client_message_id: clientMessageId,
      processing_status: 'completed',
    })
    const directPrefix =
      value.interactionStyle === 'direct' ? '先说明：炎症表现需结合血流和通透性变化理解。理解检验：' : ''
    const diagnostic: PblDiagnostic =
      phase !== 'synthesis'
        ? copy(analysis)
        : {
            ...copy(analysis),
            id: String(this.counter++),
            revision: value.messages.length,
            diagnosticStatus: 'ready',
            assistantReply: '演示结果：需要补充血管反应的机制解释。',
            followUpQuestion: undefined,
            studentId: String(this.studentId()),
            studentName: '演示学生',
            classId: session.classId,
            className: '病理学演示班',
            sessionId: id,
            topicCode: session.topicCode,
            sessionKind: session.sessionKind,
            interactionStyle: value.interactionStyle,
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
            recommendedQuestions: [
              {
                id: String(this.counter++),
                title: '解释局部红肿的病理基础',
                prompt: '分别说明血流与血管通透性改变造成的表现。',
                linkedFindings: ['gap'],
                status: 'proposed',
                version: 1,
              },
            ],
          }
    if (directPrefix) diagnostic.assistantReply = `${directPrefix}${diagnostic.assistantReply}`
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
    }
    value.diagnostic = diagnostic
    value.messages.push({
      id: String(value.messages.length + 1),
      sequence: value.messages.length + 1,
      role: 'assistant',
      content: diagnostic.assistantReply,
    })
    this.histories.set(key, copy(value))
    this.responses.set(requestKey, copy(value))
    if (diagnostic.diagnosticStatus === 'ready' && session.sessionKind === 'classroom') {
      for (const prior of this.queue.filter(
        (item) => item.studentId === diagnostic.studentId && item.sessionId === id,
      )) {
        for (const suggestion of prior.recommendedQuestions ?? [])
          if (['proposed', 'edited'].includes(suggestion.status)) suggestion.status = 'superseded'
      }
      this.queue.unshift(copy(diagnostic))
    }
    return copy(value)
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
          nextAction:
            status === 'pending'
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
  async feedback(input: {
    snapshotId: string
    clientFeedbackId: string
    body: string
    actionType: 'feedback_only' | 'task_published' | 'closed'
    suggestion?: PblSuggestion
    targets?: PblTargets
  }) {
    this.teacher()
    const current = this.feedbackBySnapshot.get(input.snapshotId) || []
    const previous = current.find((item) => item.id === input.clientFeedbackId)
    if (previous) return copy(previous)
    if (current.some((item) => item.actionType === 'closed'))
      throw new AppError('该工作项已关闭', { code: 'STATE_CONFLICT' })
    if (current.some((item) => item.actionType === 'task_published'))
      throw new AppError('正式任务已发布，请在学习跟进中继续反馈', { code: 'STATE_CONFLICT' })
    if (input.actionType === 'task_published') {
      if (!input.suggestion) throw new AppError('请选择建议题', { code: 'VALIDATION_ERROR' })
      await this.adopt(input.suggestion, input.targets)
    }
    if (input.actionType === 'closed') {
      const diagnostic = await this.diagnostic(input.snapshotId)
      for (const question of diagnostic.recommendedQuestions || [])
        if (['proposed', 'edited'].includes(question.status)) question.status = 'rejected'
    }
    const row: PblTeacherFeedback = {
      id: input.clientFeedbackId,
      snapshotId: input.snapshotId,
      actionType: input.actionType,
      body: input.body.trim(),
      createdAt: new Date().toISOString(),
    }
    this.feedbackBySnapshot.set(input.snapshotId, [...current, row])
    const submitted = [...this.dialogueSubmissions.entries()].find(([, item]) => item.snapshotId === input.snapshotId)
    const sessionId = submitted?.[0]
    const student = sessionId ? this.sessionOwners.get(sessionId) : undefined
    if (student && sessionId) {
      const id = this.notificationCounter++
      const notification: DemoPblLearningNotification = {
        id,
        sessionId,
        actionType: input.actionType,
        body: row.body,
        createdAt: row.createdAt || new Date().toISOString(),
      }
      this.learningNotificationsByStudent.set(student, [
        notification,
        ...(this.learningNotificationsByStudent.get(student) || []),
      ])
    }
    return copy(row)
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
  async editSuggestion(item: PblSuggestion, reject = false) {
    this.teacher()
    const value = this.queue.flatMap((d) => d.recommendedQuestions ?? []).find((s) => s.id === item.id)
    if (!value) throw new Error('建议不存在')
    if (value.version !== item.version || !['proposed', 'edited'].includes(value.status))
      throw new Error('建议版本已更新')
    Object.assign(value, item, { status: reject ? 'rejected' : 'edited', version: item.version + 1 })
    return copy(value)
  }
  async adopt(item: PblSuggestion, targets: PblTargets = {}) {
    this.teacher()
    const diagnostic = this.queue.find((d) => d.recommendedQuestions?.some((s) => s.id === item.id))
    const value = diagnostic?.recommendedQuestions?.find((s) => s.id === item.id)
    if (!value || !diagnostic) throw new Error('建议不存在')
    if (value.status === 'published') return copy(value)
    if (value.version !== item.version || !['proposed', 'edited'].includes(value.status))
      throw new Error('建议版本已更新')
    const recipients = targets.wholeClass
      ? [1, 2]
      : targets.studentIds?.length
        ? targets.studentIds
        : [Number(diagnostic.studentId)]
    if (recipients.some((id) => ![...this.owners.values()].includes(id))) throw new Error('目标学生不属于演示班')
    const problemId = `demo-pbl-question-${item.id}`
    await this.content.upsertProblem({
      id: problemId,
      type: '病例分析',
      title: item.title,
      description: item.prompt,
      target: 'individual',
      targetIds: [...this.owners.entries()].filter(([, id]) => recipients.includes(id)).map(([key]) => key),
      status: 'published',
      time: new Date().toISOString(),
      contentType: 'question',
      specialty: '病理学',
      knowledgePointCodes: diagnostic.knowledgeGaps.map((gap) => gap.point_code),
    })
    for (const recipient of new Set(recipients)) {
      const planId = this.counter++
      const definitions: Array<{
        task_type: PblTask['task_type']
        prompt: string
        options?: string[]
        point_code?: string
        target_label?: string
        reference?: string
        cycle_number: number
        target_type: string
        target_code: string
        variant_code: string
      }> = [
        {
          task_type: 'discussion',
          prompt: item.prompt,
          target_label: '正式讨论',
          reference: 'Demo 合成教学资料；仅用于界面合同演示。',
          cycle_number: 1,
          target_type: 'discussion',
          target_code: 'discussion',
          variant_code: `demo:${item.id}:discussion:v1`,
        },
        {
          task_type: 'discussion',
          prompt: '第二轮反思：重新说明证据链与不确定性。',
          target_label: '正式讨论',
          reference: 'Demo 合成教学资料；仅用于界面合同演示。',
          cycle_number: 2,
          target_type: 'discussion',
          target_code: 'discussion',
          variant_code: `demo:${item.id}:discussion:v2`,
        },
        ...diagnostic.knowledgeGaps.flatMap((gap) => [
          {
            task_type: 'knowledge_review' as const,
            point_code: gap.point_code,
            target_label: gap.point_code === 'pathology.inflammation.vascular' ? '炎症的血管反应' : gap.point_code,
            reference: 'Demo 合成教学资料；仅用于界面合同演示。',
            prompt: 'Demo 巩固：如何建立机制解释？',
            options: ['结合形态与机制核对证据', '只记结论'],
            cycle_number: 1,
            target_type: 'knowledge_gap',
            target_code: gap.point_code,
            variant_code: `${gap.point_code}.practice`,
          },
          {
            task_type: 'retest' as const,
            point_code: gap.point_code,
            target_label: gap.point_code === 'pathology.inflammation.vascular' ? '炎症的血管反应' : gap.point_code,
            reference: 'Demo 合成教学资料；仅用于界面合同演示。',
            prompt: 'Demo 再测：另一切片与原解释不符，应怎样处理？',
            options: ['比较新证据并修订假设', '忽略差异'],
            cycle_number: 1,
            target_type: 'knowledge_gap',
            target_code: gap.point_code,
            variant_code: `${gap.point_code}.retest`,
          },
          {
            task_type: 'knowledge_review' as const,
            point_code: gap.point_code,
            target_label: gap.point_code === 'pathology.inflammation.vascular' ? '炎症的血管反应' : gap.point_code,
            reference: 'Demo 合成教学资料；仅用于界面合同演示。',
            prompt: 'Demo 第二轮巩固：从相反证据重新建立机制解释。',
            options: ['比较证据后修订解释', '只重复原结论'],
            cycle_number: 2,
            target_type: 'knowledge_gap',
            target_code: gap.point_code,
            variant_code: `${gap.point_code}.practice.v2`,
          },
          {
            task_type: 'retest' as const,
            point_code: gap.point_code,
            target_label: gap.point_code === 'pathology.inflammation.vascular' ? '炎症的血管反应' : gap.point_code,
            reference: 'Demo 合成教学资料；仅用于界面合同演示。',
            prompt: 'Demo 第二轮再测：新证据削弱原假设时应怎样处理？',
            options: ['降低原假设优先级并继续核对', '忽略新证据'],
            cycle_number: 2,
            target_type: 'knowledge_gap',
            target_code: gap.point_code,
            variant_code: `${gap.point_code}.retest.v2`,
          },
        ]),
        ...(targets.includeCaseRetry
          ? [
              {
                task_type: 'micro_drill' as const,
                prompt: 'Demo 病例回顾：重新描述课堂病例的观察、假设与证据限制。正式完整重练由 API 训练流程执行。',
                target_label: '证据推理',
                reference: 'Demo 合成教学资料；仅用于界面合同演示。',
                cycle_number: 1,
                target_type: 'reasoning_issue',
                target_code: 'evidence_reasoning',
                variant_code: 'demo.evidence_reasoning.v1',
              },
              {
                task_type: 'micro_drill' as const,
                prompt: 'Demo 第二轮病例回顾：先写反例，再修订观察、假设与证据限制。',
                target_label: '证据推理',
                reference: 'Demo 合成教学资料；仅用于界面合同演示。',
                cycle_number: 2,
                target_type: 'reasoning_issue',
                target_code: 'evidence_reasoning',
                variant_code: 'demo.evidence_reasoning.v2',
              },
            ]
          : []),
      ]
      this.learning.push({
        id: planId,
        student_id: recipient,
        source_type: 'pbl_suggestion',
        source_id: Number(item.id),
        source_context: {
          teacher_id: 1,
          class_id: 1,
          class_name: '病理学演示班',
          session_id: Number(diagnostic.sessionId?.replace(/\D/g, '') || 1),
          snapshot_id: Number(diagnostic.id),
          suggestion_id: Number(item.id),
          point_codes: diagnostic.knowledgeGaps.map((gap) => gap.point_code),
          dimension_ids: [],
          topic_code: diagnostic.topicCode!,
        },
        status: 'active',
        verification_status: 'not_ready',
        verification_note: '',
        verified_at: null,
        version: 1,
        current_cycle: 1,
        max_cycles: 2,
        automation_exhausted: false,
        decision_policy_version: 'pbl-mastery-v1',
        decision_basis: {},
        evaluated_at: null,
        evaluations: [],
        due_at: new Date(Date.now() + 7 * 86400000).toISOString(),
        tasks: definitions.map(
          ({ task_type, cycle_number, target_type, target_code, variant_code, ...public_definition }, position) => ({
            id: this.counter++,
            position: position + 1,
            task_type,
            cycle_number,
            target_type,
            target_code,
            variant_code,
            status: cycle_number === 1 ? 'pending' : 'inactive',
            problem_id: null,
            public_definition,
            result: null,
          }),
        ),
      })
    }
    Object.assign(value, item, { status: 'published', problemId, version: item.version + 1 })
    return copy(value)
  }
  async plans() {
    return copy(this.learning.filter((plan) => plan.student_id === this.studentId()))
  }
  async results(sessionId?: string) {
    this.teacher()
    return copy(
      this.learning.filter(
        (plan) => !sessionId || plan.source_context.session_id === Number(sessionId.replace(/\D/g, '')),
      ),
    )
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
    const students = [...this.owners.entries()].map(([openid, studentId]) => {
      const participation = this.histories.get(`${openid}:${sessionId}`)
      const plan = this.learning.find(
        (item) =>
          item.student_id === studentId && item.source_context.session_id === Number(sessionId.replace(/\D/g, '') || 0),
      )
      return {
        studentId: String(studentId),
        studentName: openid,
        currentPhase: participation?.currentPhase || 'problem_framing',
        phaseStatus: participation?.phaseStatus || 'active',
        snapshotId: participation?.diagnostic?.id,
        workItemStatus: participation?.diagnostic
          ? workItems.items.find((item) => item.snapshotId === participation.diagnostic?.id)?.status
          : undefined,
        taskProgress: {
          completed: plan?.tasks.filter((task) => task.status === 'completed').length || 0,
          total: plan?.tasks.length || 0,
        },
        currentCycle: plan?.current_cycle,
        verificationStatus: plan?.verification_status,
      }
    })
    return {
      session: { id: sessionId, classId, status: session.status },
      summary: await this.summary(session),
      students,
    }
  }
  async followUps(
    filters: {
      classId?: string
      sessionId?: string
      studentId?: string
      status?: PblFollowUpStatus
      offset?: number
    } = {},
  ) {
    this.teacher()
    const items: PblFollowUp[] = this.learning
      .map((plan): PblFollowUp => ({
        planId: plan.id,
        studentId: plan.student_id,
        studentName: [...this.owners.entries()].find(([, id]) => id === plan.student_id)?.[0] || '学生',
        classId: plan.source_context.class_id,
        className: plan.source_context.class_name || `班级 ${plan.source_context.class_id}`,
        sessionId: plan.source_context.session_id,
        sessionTopic: plan.source_context.topic_code || 'PBL 课堂',
        status:
          plan.verification_status === 'improved'
            ? 'improved'
            : plan.verification_status === 'needs_reinforcement'
              ? 'support_needed'
              : plan.current_cycle === 2
                ? 'cycle_2'
                : 'in_progress',
        currentCycle: plan.current_cycle,
        verificationStatus: plan.verification_status,
        automationExhausted: plan.automation_exhausted,
        failedTargets: plan.decision_basis.failed_targets || [],
      }))
      .filter(
        (item) =>
          (!filters.classId || item.classId === Number(filters.classId)) &&
          (!filters.sessionId || item.sessionId === Number(filters.sessionId)) &&
          (!filters.studentId || item.studentId === Number(filters.studentId)) &&
          (!filters.status || item.status === filters.status),
      )
    return { items: copy(items.slice(filters.offset ?? 0, (filters.offset ?? 0) + 20)), total: items.length }
  }
  async followUp(planId: number) {
    this.teacher()
    const plan = this.learning.find((item) => item.id === planId)
    if (!plan) throw new AppError('学习跟进不存在', { code: 'RESOURCE_NOT_FOUND' })
    return { plan: copy(plan), feedbacks: [] }
  }
  async followUpFeedback(planId: number, clientFeedbackId: string, body: string) {
    const followUp = await this.followUp(planId)
    if (!followUp.plan.automation_exhausted) throw new AppError('当前计划不需要补充反馈', { code: 'STATE_CONFLICT' })
    return {
      id: clientFeedbackId,
      snapshotId: String(followUp.plan.source_context.snapshot_id),
      planId: String(planId),
      actionType: 'follow_up',
      body,
      createdAt: new Date().toISOString(),
    }
  }
  async submitTask(
    taskId: number,
    submissionId: string,
    answer: { text?: string; selected_option?: number },
  ): Promise<PblPlan> {
    const plan = this.learning.find((p) => p.student_id === this.studentId() && p.tasks.some((t) => t.id === taskId))
    const task = plan?.tasks.find((t) => t.id === taskId)
    if (!plan || !task) throw new Error('任务不存在')
    const previous = this.submissions.get(taskId)
    if (previous) {
      if (previous.id !== submissionId || previous.answer !== JSON.stringify(answer)) throw new Error('任务已经提交')
      return copy(plan)
    }
    if (task.status === 'inactive' || task.status === 'skipped' || task.cycle_number !== plan.current_cycle)
      throw new Error('该轮任务尚未激活')
    if (
      plan.tasks.some(
        (t) =>
          t.cycle_number === task.cycle_number &&
          t.position < task.position &&
          !['completed', 'skipped'].includes(t.status),
      )
    )
      throw new Error('请先完成前面的任务')
    const objective = !!task.public_definition.options
    if (
      objective
        ? !Number.isInteger(answer.selected_option) || !task.public_definition.options?.[answer.selected_option!]
        : !answer.text?.trim()
    )
      throw new Error('请填写有效答案')
    task.status = 'completed'
    task.result = {
      score: objective ? (answer.selected_option === 0 ? 100 : 0) : task.task_type === 'micro_drill' ? 80 : null,
      feedback: 'Demo 学习证据已保存，系统将在本轮完成后自动判定。',
      evidence: [objective ? 'Demo 客观题作答' : 'Demo 学生作答'],
      answer,
      submitted_at: new Date().toISOString(),
    }
    this.submissions.set(taskId, { id: submissionId, answer: JSON.stringify(answer) })
    const active = plan.tasks.filter(
      (item) => item.cycle_number === plan.current_cycle && !['inactive', 'skipped'].includes(item.status),
    )
    if (active.every((item) => item.status === 'completed')) {
      const retests = active.filter((item) => item.task_type === 'retest')
      const micro = active.filter((item) => item.task_type === 'micro_drill')
      const failed = [
        ...retests.filter((item) => item.result?.score !== 100),
        ...micro.filter((item) => (item.result?.score ?? -1) < 70),
      ]
      plan.evaluated_at = new Date().toISOString()
      plan.version++
      plan.decision_basis = {
        result: failed.length
          ? plan.current_cycle === 1
            ? 'next_cycle_activated'
            : 'needs_reinforcement'
          : 'improved',
        cycle: plan.current_cycle,
        failed_targets: failed.map((item) => ({ target_type: item.target_type, target_code: item.target_code })),
        checks: [...retests, ...micro].map((item) => ({
          target_type: item.target_type,
          target_code: item.target_code,
          threshold: item.task_type === 'retest' ? 100 : 70,
          score: item.result?.score ?? null,
          evidence_present: Boolean(item.result?.evidence.length),
          passed: item.task_type === 'retest' ? item.result?.score === 100 : (item.result?.score ?? -1) >= 70,
        })),
      }
      plan.evaluations ??= []
      plan.evaluations.push({
        cycle_number: plan.current_cycle,
        policy_version: plan.decision_policy_version,
        result: String(plan.decision_basis.result),
        checks: plan.decision_basis.checks ?? [],
        failed_targets: plan.decision_basis.failed_targets ?? [],
        automation_exhausted: plan.current_cycle === 2 && failed.length > 0,
        record_source: 'runtime',
        evaluated_at: plan.evaluated_at,
      })
      if (!failed.length) {
        plan.status = 'completed'
        plan.verification_status = 'improved'
      } else if (plan.current_cycle === 1) {
        const failedKeys = new Set(failed.map((item) => `${item.target_type}:${item.target_code}`))
        plan.current_cycle = 2
        for (const item of plan.tasks.filter((candidate) => candidate.cycle_number === 2))
          item.status =
            item.target_type === 'discussion' || failedKeys.has(`${item.target_type}:${item.target_code}`)
              ? 'pending'
              : 'skipped'
      } else {
        plan.status = 'completed'
        plan.verification_status = 'needs_reinforcement'
        plan.automation_exhausted = true
        plan.decision_basis.offline_support_required = true
      }
    }
    return copy(plan)
  }
  async summary(session: PblSession) {
    const plans = await this.results(session.id),
      tasks = plans.flatMap((p) => p.tasks)
    const scores = tasks.filter((t) => t.task_type === 'retest' && t.result).map((t) => t.result!.score!)
    return {
      participants: [...this.histories.keys()].filter((key) => key.endsWith(`:${session.id}`)).length,
      diagnoses: this.queue.filter((d) => d.sessionId === session.id).length,
      published_suggestions: this.queue
        .filter((d) => d.sessionId === session.id)
        .flatMap((d) => d.recommendedQuestions ?? [])
        .filter((s) => s.status === 'published').length,
      plans: plans.length,
      tasks: tasks.length,
      completed_tasks: tasks.filter((t) => t.status === 'completed').length,
      pending_verification: 0,
      improved: plans.filter((p) => p.verification_status === 'improved').length,
      needs_reinforcement: plans.filter((p) => p.verification_status === 'needs_reinforcement').length,
      objective_retest_count: scores.length,
      objective_retest_average: scores.length ? scores.reduce((a, b) => a + b, 0) / scores.length : null,
      phase_counts: Object.fromEntries(
        ['problem_framing', 'hypothesis', 'evidence', 'synthesis', 'completed'].map((phase) => [
          phase,
          [...this.histories.entries()].filter(
            ([key, participation]) => key.endsWith(`:${session.id}`) && participation.currentPhase === phase,
          ).length,
        ]),
      ),
      automation_exhausted: plans.filter((p) => p.automation_exhausted).length,
    }
  }
  async reports(limit = 20, offset = 0) {
    const studentId = this.studentId()
    const keyPrefix = `${actor().openid}:`
    const plans = this.learning.filter((plan) => plan.student_id === studentId)
    const sessions = this.classrooms.filter((session) => {
      const numeric = Number(session.id.replace(/\D/g, '') || 0)
      return (
        this.histories.has(`${keyPrefix}${session.id}`) ||
        plans.some((plan) => plan.source_context.session_id === numeric)
      )
    })
    return demoReportPage(
      sessions.map((session) => {
        const numeric = Number(session.id.replace(/\D/g, '') || 0)
        const participation = this.histories.get(`${keyPrefix}${session.id}`)
        return demoReportDetail(
          session,
          participation,
          plans.filter((plan) => plan.source_context.session_id === numeric),
          studentId,
          this.feedbackBySnapshot.get(participation?.diagnostic?.id || '') || [],
          this.dialogueSubmissions.get(session.id)?.submittedAt,
        )
      }),
      limit,
      offset,
    )
  }
  async report(sessionId: string) {
    const page = await this.reports(100, 0)
    if (!page.items.some((item) => item.session.id === sessionId)) throw new Error('学情报告不存在')
    const studentId = this.studentId()
    const session = this.classrooms.find((item) => item.id === sessionId)!
    const numeric = Number(session.id.replace(/\D/g, '') || 0)
    const participation = this.histories.get(`${actor().openid}:${session.id}`)
    return demoReportDetail(
      session,
      participation,
      this.learning.filter((plan) => plan.student_id === studentId && plan.source_context.session_id === numeric),
      studentId,
      this.feedbackBySnapshot.get(participation?.diagnostic?.id || '') || [],
      this.dialogueSubmissions.get(session.id)?.submittedAt,
    )
  }
}
