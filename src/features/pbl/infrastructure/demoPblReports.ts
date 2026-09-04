import type {
  PblCycleCheck,
  PblLearningReport,
  PblParticipation,
  PblPlan,
  PblReportPage,
  PblReportSession,
  PblReportStatus,
  PblSession,
} from '../domain/ports'

const phaseOrder = ['problem_framing', 'hypothesis', 'evidence', 'synthesis'] as const
const phaseLabels = {
  problem_framing: '明确问题',
  hypothesis: '提出假设',
  evidence: '讨论证据',
  synthesis: '总结解释',
}
const statusKeys: PblReportStatus[] = [
  'discussing',
  'awaiting_learning',
  'learning_cycle_1',
  'learning_cycle_2',
  'improved',
  'support_needed',
]
const reportSession = (session: PblSession): PblReportSession => ({
  id: session.id,
  topicCode: session.topicCode,
  topicLabel: session.topicCode === 'pathology.inflammation' ? '炎症' : session.topicCode,
  caseTitle: session.caseContext?.title ?? 'PBL 课堂病例',
  status: session.status,
  createdAt: session.createdAt ?? new Date().toISOString(),
  closedAt: session.closedAt,
})
const statusOf = (participation: PblParticipation | undefined, plans: PblPlan[]): PblReportStatus => {
  const active = plans.filter((plan) => plan.status === 'active')
  if (active.length) return active.some((plan) => plan.current_cycle >= 2) ? 'learning_cycle_2' : 'learning_cycle_1'
  if (plans.some((plan) => plan.verification_status === 'needs_reinforcement')) return 'support_needed'
  if (plans.length && plans.every((plan) => plan.verification_status === 'improved')) return 'improved'
  return participation?.phaseStatus === 'completed' ? 'awaiting_learning' : 'discussing'
}
const actionOf = (status: PblReportStatus) =>
  status === 'discussing'
    ? ({ kind: 'discussion', label: '继续四阶段讨论' } as const)
    : status.startsWith('learning_')
      ? ({ kind: 'tasks', label: '继续课后学习任务' } as const)
      : status === 'awaiting_learning'
        ? ({ kind: 'none', label: '学习任务待教师审阅发布' } as const)
        : status === 'support_needed'
          ? ({ kind: 'none', label: '回看未达标目标并结合线下支持' } as const)
          : ({ kind: 'none', label: '本次必需目标已达标' } as const)
const summaryOf = (status: PblReportStatus) =>
  ({
    discussing: '当前正在形成四阶段讨论证据，完成本阶段后系统会自动推进。',
    awaiting_learning: '四阶段讨论已完成，个人学习线索已经形成，后续任务待教师审阅发布。',
    learning_cycle_1: '第一轮针对性学习正在进行，完成任务后系统会逐项目标判定。',
    learning_cycle_2: '第一轮仍有目标未达标，系统已只激活对应的第二轮等价变式。',
    improved: '本次所有必需知识与推理目标均已达到系统规则要求。',
    support_needed: '两轮自动巩固已结束，仍有目标需要结合线下支持继续学习。',
  })[status]
const targetLabel = (type: string, code: string) => {
  if (type === 'knowledge_gap') return code.includes('vascular') ? '炎症的血管反应' : code
  if (type === 'reasoning_issue' || type === 'case_dimension') return code === 'evidence_reasoning' ? '证据推理' : code
  return type === 'discussion' ? '正式讨论' : '完整病例重练'
}

export function demoReportDetail(
  session: PblSession,
  participation: PblParticipation | undefined,
  plans: PblPlan[],
  _studentId: number,
): PblLearningReport {
  const status = statusOf(participation, plans)
  const diagnostic = participation?.diagnostic?.diagnosticStatus === 'ready' ? participation.diagnostic : undefined
  const phaseIndex =
    participation?.phaseStatus === 'completed' ? 4 : phaseOrder.indexOf(participation?.currentPhase as never)
  const safePlans = plans.map((plan) => ({
    id: plan.id,
    assignmentBasis:
      Number(diagnostic?.id) === plan.source_context.snapshot_id ? ('personal' as const) : ('classroom' as const),
    status: plan.status,
    verificationStatus: plan.verification_status,
    currentCycle: plan.current_cycle,
    maxCycles: plan.max_cycles,
    automationExhausted: plan.automation_exhausted,
    decisionPolicyVersion: plan.decision_policy_version,
    dueAt: plan.due_at,
    createdAt: new Date(new Date(plan.due_at).getTime() - 7 * 86400000).toISOString(),
    tasks: plan.tasks.map((task) => ({
      id: task.id,
      taskType: task.task_type,
      status: task.status,
      cycleNumber: task.cycle_number,
      targetType: task.target_type,
      targetCode: task.target_code,
      targetLabel: targetLabel(task.target_type, task.target_code),
      prompt: task.public_definition.prompt,
      score: task.result?.score ?? null,
      feedback: task.result?.feedback ?? '',
      evidencePresent: Boolean(task.result?.evidence.length),
      submittedAt: task.result?.submitted_at ?? undefined,
    })),
    evaluations: (plan.evaluations ?? []).map((evaluation) => ({
      ...evaluation,
      checks: evaluation.checks.map((check) => ({
        ...check,
        label: targetLabel(check.target_type, check.target_code),
      })),
      failed_targets: evaluation.failed_targets.map((target) => ({
        ...target,
        label: targetLabel(target.target_type, target.target_code),
      })),
    })),
  }))
  const targetProgress: PblLearningReport['targetProgress'] = []
  for (const plan of safePlans) {
    const groups = new Map<string, PblLearningReport['targetProgress'][number]>()
    for (const evaluation of plan.evaluations) {
      for (const check of evaluation.checks) {
        if (check.target_type === 'discussion') continue
        const key = `${check.target_type}:${check.target_code}`
        const item = groups.get(key) ?? {
          planId: plan.id,
          targetType: check.target_type,
          targetCode: check.target_code,
          label: check.label ?? check.target_code,
          cycles: [],
        }
        item.cycles.push({ cycleNumber: evaluation.cycle_number, ...check })
        groups.set(key, item)
      }
    }
    targetProgress.push(...groups.values())
  }
  const createdAt = session.createdAt ?? new Date().toISOString()
  const timeline: PblLearningReport['timeline'] = [
    { type: 'discussion_started', label: '开始 PBL 讨论', occurredAt: createdAt },
  ]
  if (participation?.phaseCompletedAt)
    timeline.push({ type: 'discussion_completed', label: '完成四阶段讨论', occurredAt: participation.phaseCompletedAt })
  for (const plan of safePlans) {
    timeline.push({ type: 'tasks_published', label: '课后学习任务已发布', occurredAt: plan.createdAt })
    for (const evaluation of plan.evaluations)
      timeline.push({
        type: 'cycle_evaluated',
        label:
          evaluation.result === 'improved'
            ? '本轮目标全部达标'
            : evaluation.result === 'next_cycle_activated'
              ? '第二轮差异化巩固已开启'
              : '自动轮次结束，仍需线下支持',
        cycleNumber: evaluation.cycle_number,
        occurredAt: evaluation.evaluated_at,
      })
  }
  timeline.sort((a, b) => Date.parse(a.occurredAt) - Date.parse(b.occurredAt))
  const tasks = safePlans.flatMap((plan) => plan.tasks)
  return {
    session: reportSession(session),
    status,
    currentPhase: participation?.currentPhase,
    phaseStatus: participation?.phaseStatus,
    phaseProgress: participation
      ? phaseOrder.map((phase, index) => ({
          phase,
          label: phaseLabels[phase],
          state: index < phaseIndex ? 'completed' : index === phaseIndex ? 'current' : 'pending',
          evidenceSummary:
            participation.diagnostic?.phase === phase ? (participation.diagnostic.phaseEvidenceSummary ?? '') : '',
          missingElements:
            participation.diagnostic?.phase === phase ? (participation.diagnostic.phaseMissingElements ?? []) : [],
          evidencedAt: participation.diagnostic?.phase === phase ? participation.diagnostic.createdAt : undefined,
        }))
      : [],
    diagnosis: {
      createdAt: diagnostic?.createdAt,
      knowledgeGaps: (diagnostic?.knowledgeGaps ?? []).map((item) => ({
        id: item.id,
        pointCode: item.point_code,
        label: targetLabel('knowledge_gap', item.point_code),
        summary: item.summary,
        confidence: item.confidence,
        evidenceSummary: item.evidence_summary,
      })),
      reasoningIssues: (diagnostic?.reasoningIssues ?? []).map((item) => ({
        id: item.id,
        dimensionId: item.dimension_id,
        label: targetLabel('reasoning_issue', item.dimension_id),
        summary: item.summary,
        issueType: item.issue_type,
        improvement: item.improvement,
        evidenceSummary: item.evidence_summary,
      })),
    },
    plans: safePlans,
    targetProgress,
    taskProgress: {
      completed: tasks.filter((task) => task.status === 'completed').length,
      total: tasks.filter((task) => !['inactive', 'skipped'].includes(task.status)).length,
    },
    summaryText: summaryOf(status),
    nextAction: actionOf(status),
    timeline,
    updatedAt: timeline.at(-1)?.occurredAt ?? createdAt,
  }
}

export function demoReportPage(reports: PblLearningReport[], limit: number, offset: number): PblReportPage {
  const ordered = [...reports].sort((a, b) => Date.parse(b.updatedAt) - Date.parse(a.updatedAt))
  const statusCounts = Object.fromEntries(statusKeys.map((status) => [status, 0])) as Record<PblReportStatus, number>
  const recurring = new Map<string, { targetType: string; targetCode: string; label: string; occurrences: number }>()
  for (const report of ordered) {
    statusCounts[report.status]++
    for (const item of report.diagnosis.knowledgeGaps) {
      const value = recurring.get(item.pointCode) ?? {
        targetType: 'knowledge_gap',
        targetCode: item.pointCode,
        label: item.label,
        occurrences: 0,
      }
      value.occurrences++
      recurring.set(item.pointCode, value)
    }
  }
  const next = ordered.find((item) => ['learning_cycle_2', 'learning_cycle_1', 'discussing'].includes(item.status))
  return {
    summary: {
      totalReports: ordered.length,
      statusCounts,
      recurringTargets: [...recurring.values()].sort((a, b) => b.occurrences - a.occurrences).slice(0, 6),
      nextAction: next
        ? { ...next.nextAction, sessionId: next.session.id, caseTitle: next.session.caseTitle }
        : undefined,
    },
    items: ordered.slice(offset, offset + limit).map((item) => ({
      session: item.session,
      status: item.status,
      currentPhase: item.currentPhase,
      phaseStatus: item.phaseStatus,
      knowledgeGapCount: item.diagnosis.knowledgeGaps.length,
      reasoningIssueCount: item.diagnosis.reasoningIssues.length,
      taskProgress: item.taskProgress,
      summaryText: item.summaryText,
      nextAction: item.nextAction,
      updatedAt: item.updatedAt,
    })),
    total: ordered.length,
    limit,
    offset,
  }
}

export function checksWithLabels(checks: PblCycleCheck[]): PblCycleCheck[] {
  return checks.map((check) => ({ ...check, label: targetLabel(check.target_type, check.target_code) }))
}
