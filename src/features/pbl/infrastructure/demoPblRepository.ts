import type {
  PblDiagnostic,
  PblRepository,
  PblSession,
  PblSuggestion,
  PblParticipation,
  PblPhase,
  PblPlan,
  PblTargets,
  PblFilters,
  PblTask,
} from '../domain/ports'
import { getSessionContext } from '@/platform/session/context'
import { AppError } from '@/types/errors'
import type { ContentRepository } from '@/features/content/domain/ports'
const copy = <T>(value: T): T => JSON.parse(JSON.stringify(value)) as T
const actor = () => {
  const user = getSessionContext()
  if (!user) throw new AppError('请先登录', { code: 'AUTH_REQUIRED' })
  return user
}
const analysis: PblDiagnostic = {
  schemaVersion: 2,
  diagnosticStatus: 'probing',
  assistantReply: '演示追问：请说明你如何把血管变化与红肿联系起来。',
  followUpQuestion: '你认为通透性变化会造成什么表现？',
  knowledgeGaps: [],
  reasoningIssues: [],
  safetyNotice: 'Demo 合成教学演示，不代表真实 AI 诊断。',
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
    },
  ]
  private histories = new Map<string, PblParticipation>()
  private responses = new Map<string, PblParticipation>()
  private queue: PblDiagnostic[] = []
  private learning: PblPlan[] = []
  private owners = new Map<string, number>([
    ['demo_student', 1],
    ['demo_student_b', 2],
  ])
  private submissions = new Map<number, { id: string; answer: string }>()
  private counter = 1
  private studentId() {
    const key = actor().openid
    if (!this.owners.has(key)) this.owners.set(key, this.owners.size + 1)
    return this.owners.get(key)!
  }
  private teacher() {
    if (actor().role !== 'teacher') throw new AppError('仅教师可操作', { code: 'FORBIDDEN' })
  }
  async active() {
    actor()
    return copy(this.classrooms)
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
  async phase(item: PblSession, phase: PblPhase) {
    const value = this.classrooms.find((s) => s.id === item.id)
    if (!value) throw new Error('课堂不存在')
    value.phase = phase
    value.version++
    return copy(value)
  }
  async participation(id: string) {
    return copy(this.histories.get(`${actor().openid}:${id}`) ?? { messages: [] })
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
    value.messages.push({
      id: mid,
      sequence: value.messages.length + 1,
      role: 'student',
      content,
      client_message_id: clientMessageId,
      processing_status: 'completed',
    })
    const diagnostic: PblDiagnostic =
      value.messages.length === 1
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
    value.diagnostic = diagnostic
    value.messages.push({
      id: String(value.messages.length + 1),
      sequence: value.messages.length + 1,
      role: 'assistant',
      content: diagnostic.assistantReply,
    })
    this.histories.set(key, copy(value))
    this.responses.set(requestKey, copy(value))
    if (diagnostic.diagnosticStatus === 'ready') {
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
      }> = [
        { task_type: 'discussion', prompt: item.prompt },
        ...diagnostic.knowledgeGaps.flatMap((gap) => [
          {
            task_type: 'knowledge_review' as const,
            point_code: gap.point_code,
            prompt: 'Demo 巩固：如何建立机制解释？',
            options: ['结合形态与机制核对证据', '只记结论'],
          },
          {
            task_type: 'retest' as const,
            point_code: gap.point_code,
            prompt: 'Demo 再测：另一切片与原解释不符，应怎样处理？',
            options: ['比较新证据并修订假设', '忽略差异'],
          },
        ]),
        ...(targets.includeCaseRetry
          ? [
              {
                task_type: 'micro_drill' as const,
                prompt: 'Demo 病例回顾：重新描述课堂病例的观察、假设与证据限制。正式完整重练由 API 训练流程执行。',
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
        due_at: new Date(Date.now() + 7 * 86400000).toISOString(),
        tasks: definitions.map(({ task_type, ...public_definition }, position) => ({
          id: this.counter++,
          position: position + 1,
          task_type,
          status: 'pending',
          problem_id: null,
          public_definition,
          result: null,
        })),
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
    if (plan.tasks.some((t) => t.position < task.position && t.status !== 'completed'))
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
      score: objective ? (answer.selected_option === 0 ? 100 : 0) : null,
      feedback: 'Demo 学习证据已保存，待教师核验。',
      evidence: [objective ? 'Demo 客观题作答' : 'Demo 学生作答'],
      answer,
      submitted_at: new Date().toISOString(),
    }
    this.submissions.set(taskId, { id: submissionId, answer: JSON.stringify(answer) })
    if (plan.tasks.every((t) => t.status === 'completed')) {
      plan.status = 'completed'
      plan.verification_status = 'pending_teacher'
      plan.version++
    }
    return copy(plan)
  }
  async verify(plan: PblPlan, decision: 'improved' | 'needs_reinforcement', note: string) {
    this.teacher()
    const value = this.learning.find((p) => p.id === plan.id)
    if (!value || value.version !== plan.version || value.verification_status !== 'pending_teacher')
      throw new Error('结果尚未完成或版本已更新')
    Object.assign(value, {
      verification_status: decision,
      verification_note: note,
      verified_at: new Date().toISOString(),
      version: value.version + 1,
    })
    return copy(value)
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
      pending_verification: plans.filter((p) => p.verification_status === 'pending_teacher').length,
      improved: plans.filter((p) => p.verification_status === 'improved').length,
      needs_reinforcement: plans.filter((p) => p.verification_status === 'needs_reinforcement').length,
      objective_retest_count: scores.length,
      objective_retest_average: scores.length ? scores.reduce((a, b) => a + b, 0) / scores.length : null,
    }
  }
}
