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
} from '../domain/ports'
import { demoReportDetail, demoReportPage } from './demoPblReports'
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
  schemaVersion: 3,
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
    const empty: PblParticipation = {
      messages: [],
      currentPhase: 'problem_framing',
      phaseStartedRevision: 0,
      phaseStatus: 'active',
    }
    return copy(this.histories.get(`${actor().openid}:${id}`) ?? empty)
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
        cycle_number: number
        target_type: string
        target_code: string
        variant_code: string
      }> = [
        {
          task_type: 'discussion',
          prompt: item.prompt,
          cycle_number: 1,
          target_type: 'discussion',
          target_code: 'discussion',
          variant_code: `demo:${item.id}:discussion:v1`,
        },
        {
          task_type: 'discussion',
          prompt: '第二轮反思：重新说明证据链与不确定性。',
          cycle_number: 2,
          target_type: 'discussion',
          target_code: 'discussion',
          variant_code: `demo:${item.id}:discussion:v2`,
        },
        ...diagnostic.knowledgeGaps.flatMap((gap) => [
          {
            task_type: 'knowledge_review' as const,
            point_code: gap.point_code,
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
                cycle_number: 1,
                target_type: 'reasoning_issue',
                target_code: 'evidence_reasoning',
                variant_code: 'demo.evidence_reasoning.v1',
              },
              {
                task_type: 'micro_drill' as const,
                prompt: 'Demo 第二轮病例回顾：先写反例，再修订观察、假设与证据限制。',
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
        return demoReportDetail(
          session,
          this.histories.get(`${keyPrefix}${session.id}`),
          plans.filter((plan) => plan.source_context.session_id === numeric),
          studentId,
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
    return demoReportDetail(
      session,
      this.histories.get(`${actor().openid}:${session.id}`),
      this.learning.filter((plan) => plan.student_id === studentId && plan.source_context.session_id === numeric),
      studentId,
    )
  }
}
