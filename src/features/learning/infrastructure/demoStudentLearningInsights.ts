import type { StudentLearningInsightsPort, StudentLearningInsightsPage } from '../domain/studentLearningInsights'

type DemoDiagnosis = {
  knowledgeGapCodes: string[]
  reasoningIssueCodes: string[]
}
type DemoDialogue = {
  sessionId: string
  topicCode: string
  caseTitle: string
  createdAt: string
  updatedAt: string
  learningRouteId?: string
  diagnosisCreatedAt?: string
  diagnosis?: DemoDiagnosis
}
type DemoQuestion = {
  pointCode: string
  earned: number
  possible: number
}
type DemoRoute = {
  id: string
  sessionLocator: string
  title: string
  goalPointCodes: string[]
  status: string
  progressLabel: string
  completedSteps: number
  totalSteps: number
  updatedAt: string
  accumulatedReadingSeconds: number
  result?: {
    score: number
    submittedAt: string
    goalPointCodes: string[]
    questions: DemoQuestion[]
  }
}
type DemoStudentLearningInsightsReader = {
  readDialogues(): Promise<DemoDialogue[]>
  readRoutes(): Promise<DemoRoute[]>
  readKnowledgeCatalog(): Promise<Array<{ code: string; title: string; systemCode: string; systemLabel: string }>>
  now?: () => Date
}

const round = (value: number) => Math.round(value * 10) / 10
const reasoningLabels: Record<string, string> = {
  information_gathering: '信息搜集',
  problem_representation: '问题表征',
  differential_diagnosis: '鉴别诊断',
  evidence_reasoning: '证据推理',
  test_selection: '检查选择',
  management_safety: '处置安全',
}
const unique = (values: string[]) => [...new Set(values.filter(Boolean))]
const validDate = (value: string) => {
  const timestamp = Date.parse(value)
  return Number.isFinite(timestamp) ? timestamp : undefined
}
const dateLabel = (date: Date) => date.toISOString().slice(0, 10)
const addDays = (date: Date, count: number) => {
  const next = new Date(date)
  next.setUTCDate(next.getUTCDate() + count)
  return next
}

function shanghaiWeekStart(value: Date): Date {
  const shanghai = new Date(value.getTime() + 8 * 60 * 60 * 1000)
  const localDate = new Date(Date.UTC(shanghai.getUTCFullYear(), shanghai.getUTCMonth(), shanghai.getUTCDate()))
  const mondayOffset = (localDate.getUTCDay() + 6) % 7
  localDate.setUTCDate(localDate.getUTCDate() - mondayOffset)
  return localDate
}

function weekStartForTimestamp(value: string): string | undefined {
  const timestamp = validDate(value)
  return timestamp === undefined ? undefined : dateLabel(shanghaiWeekStart(new Date(timestamp)))
}

function scoreForTarget(route: DemoRoute, targetCode: string): number | null {
  const measures = route.result?.questions
    .filter((question) => question.pointCode === targetCode)
    .filter((value) => Number.isFinite(value.earned) && Number.isFinite(value.possible) && value.possible > 0)
  if (measures?.length) {
    const earned = measures.reduce((total, value) => total + value.earned, 0)
    const possible = measures.reduce((total, value) => total + value.possible, 0)
    return possible > 0 ? round((earned / possible) * 100) : null
  }
  if (route.result?.goalPointCodes.length === 1 && route.result.goalPointCodes[0] === targetCode)
    return route.result.score
  return null
}

function sortedByUpdatedAt<T extends { updatedAt: string }>(values: T[]): T[] {
  return [...values].sort((left, right) => (validDate(right.updatedAt) ?? 0) - (validDate(left.updatedAt) ?? 0))
}

function routeActivityAt(route: DemoRoute): string {
  const resultAt = route.result?.submittedAt
  return resultAt && (validDate(resultAt) ?? 0) > (validDate(route.updatedAt) ?? 0) ? resultAt : route.updatedAt
}

export class DemoStudentLearningInsightsRepository implements StudentLearningInsightsPort {
  constructor(private readonly reader: DemoStudentLearningInsightsReader) {}

  async getStudentLearningInsights(limit = 20, offset = 0): Promise<StudentLearningInsightsPage> {
    const [dialogues, routes, catalog] = await Promise.all([
      this.reader.readDialogues(),
      this.reader.readRoutes(),
      this.reader.readKnowledgeCatalog(),
    ])
    const routesById = new Map(routes.map((route) => [route.id, route]))
    const routesBySession = new Map<string, DemoRoute[]>()
    for (const route of routes) {
      const matching = routesBySession.get(route.sessionLocator) ?? []
      matching.push(route)
      routesBySession.set(route.sessionLocator, matching)
    }

    const catalogLabels = new Map(catalog.map((point) => [point.code, point.title]))
    const catalogByCode = new Map(catalog.map((point) => [point.code, point]))
    const moduleLabels = new Map(catalog.map((point) => [point.systemCode, point.systemLabel]))
    const labelOf = (code: string) => catalogLabels.get(code) || reasoningLabels[code] || code
    const linkedRouteIds = new Set<string>()
    const dialogueRecords = dialogues.map((dialogue) => {
      const linked = (dialogue.learningRouteId && routesById.get(dialogue.learningRouteId)) || undefined
      const sessionRoutes = sortedByUpdatedAt(routesBySession.get(dialogue.sessionId) ?? [])
      const bySession = sessionRoutes[0]
      const route = linked || bySession
      if (route) {
        linkedRouteIds.add(route.id)
        sessionRoutes.forEach((item) => linkedRouteIds.add(item.id))
      }
      const routeActivity = route && routeActivityAt(route)
      const updatedAt =
        routeActivity && (validDate(routeActivity) ?? 0) > (validDate(dialogue.updatedAt) ?? 0)
          ? routeActivity
          : dialogue.updatedAt
      const action = route
        ? route.result
          ? { kind: 'result' as const, sessionId: route.sessionLocator, routeId: route.id, label: '查看结果解析' }
          : { kind: 'route' as const, sessionId: route.sessionLocator, routeId: route.id, label: '继续学习路线' }
        : { kind: 'discussion' as const, sessionId: dialogue.sessionId, label: '继续研讨' }
      let summaryText = '研讨仍在进行，完成诊断后会形成针对性学习路线。'
      if (dialogue.diagnosis) {
        summaryText = `研讨诊断已完成，记录了 ${dialogue.diagnosis.knowledgeGapCodes.length} 个知识目标和 ${dialogue.diagnosis.reasoningIssueCodes.length} 个推理目标。`
      }
      if (route && !route.result) {
        summaryText = `学习路线已完成 ${route.completedSteps}/${route.totalSteps} 步；${route.progressLabel}。`
      }
      if (route?.result) summaryText = `最终测试得分 ${round(route.result.score)} 分，可查看本次结果解析。`
      return {
        id: dialogue.sessionId,
        session: {
          id: dialogue.sessionId,
          topicLabel: moduleLabels.get(dialogue.topicCode) || labelOf(dialogue.topicCode),
          caseTitle: dialogue.caseTitle,
        },
        summaryText,
        updatedAt,
        action,
        route,
        diagnosis: dialogue.diagnosis,
        diagnosisCreatedAt: dialogue.diagnosisCreatedAt,
      }
    })
    const topicLabelForRoute = (route: DemoRoute) => {
      const pointCode = route.goalPointCodes[0]
      if (!pointCode) return '自主学习'
      const point = catalogByCode.get(pointCode)
      return (point && moduleLabels.get(point.systemCode)) || labelOf(pointCode)
    }
    const routeOnlyRecords = routes
      .filter((route) => !linkedRouteIds.has(route.id))
      .map((route) => ({
        id: `route:${route.id}`,
        session: {
          id: route.sessionLocator,
          topicLabel: topicLabelForRoute(route),
          caseTitle: route.title,
        },
        summaryText: route.result
          ? `最终测试得分 ${round(route.result.score)} 分，可查看本次结果解析。`
          : `学习路线已完成 ${route.completedSteps}/${route.totalSteps} 步；${route.progressLabel}。`,
        updatedAt: routeActivityAt(route),
        action: route.result
          ? { kind: 'result' as const, sessionId: route.sessionLocator, routeId: route.id, label: '查看结果解析' }
          : { kind: 'route' as const, sessionId: route.sessionLocator, routeId: route.id, label: '继续学习路线' },
        route,
        diagnosis: undefined,
        diagnosisCreatedAt: undefined,
      }))
    const records = sortedByUpdatedAt([...dialogueRecords, ...routeOnlyRecords])

    const resultRoutes = routes.filter((route) => route.result)
    const testedTargets = new Set<string>()
    for (const route of resultRoutes) {
      for (const code of unique([
        ...route.result!.goalPointCodes,
        ...route.result!.questions.map((item) => item.pointCode),
      ]))
        testedTargets.add(code)
    }
    const totalRoutes = routes.length
    const planCompletionRate = totalRoutes ? round((resultRoutes.length / totalRoutes) * 100) : null
    const totalReadingSeconds = routes.reduce((total, route) => total + route.accumulatedReadingSeconds, 0)

    const now = this.reader.now?.() || new Date()
    const currentWeekStart = shanghaiWeekStart(now)
    const starts = [-3, -2, -1, 0].map((weeksAgo) => addDays(currentWeekStart, weeksAgo * 7))
    const trend = starts.map((start) => {
      const startLabel = dateLabel(start)
      const scores = resultRoutes
        .filter((route) => {
          const week = weekStartForTimestamp(route.result!.submittedAt)
          return week === startLabel
        })
        .map((route) => route.result!.score)
      return {
        periodStart: startLabel,
        periodEnd: dateLabel(addDays(start, 6)),
        score: scores.length ? round(scores.reduce((total, score) => total + score, 0) / scores.length) : null,
        sampleCount: scores.length,
      }
    })
    const current = trend.at(-1)!
    const previous = trend.at(-2)!
    const masteryDelta =
      current.score !== null && previous.score !== null ? round(current.score - previous.score) : null
    const statusLabel =
      current.sampleCount === 0
        ? '待积累'
        : masteryDelta === null
          ? '本周已有测试'
          : masteryDelta > 0
            ? '较上周提升'
            : masteryDelta < 0
              ? '较上周回落'
              : '与上周持平'

    const occurrences = new Map<
      string,
      { targetType: 'knowledge' | 'reasoning'; targetCode: string; occurrences: number }
    >()
    const latestDiagnosisAt = new Map<string, string>()
    for (const record of records) {
      if (!record.diagnosis) continue
      for (const [targetType, codes] of [
        ['knowledge', record.diagnosis.knowledgeGapCodes],
        ['reasoning', record.diagnosis.reasoningIssueCodes],
      ] as const) {
        for (const targetCode of unique(codes)) {
          const key = `${targetType}:${targetCode}`
          const item = occurrences.get(key) ?? { targetType, targetCode, occurrences: 0 }
          item.occurrences += 1
          occurrences.set(key, item)
          if (targetType === 'knowledge') {
            const timestamp = record.diagnosisCreatedAt || record.updatedAt
            const prior = latestDiagnosisAt.get(targetCode)
            if (!prior || (validDate(timestamp) ?? 0) > (validDate(prior) ?? 0))
              latestDiagnosisAt.set(targetCode, timestamp)
          }
        }
      }
    }
    const latestEvidence = new Map<string, { score: number; submittedAt: string }>()
    for (const route of resultRoutes) {
      for (const targetCode of unique([
        ...route.result!.goalPointCodes,
        ...route.result!.questions.map((item) => item.pointCode),
      ])) {
        const score = scoreForTarget(route, targetCode)
        if (score === null) continue
        const previousEvidence = latestEvidence.get(targetCode)
        if (
          !previousEvidence ||
          (validDate(route.result!.submittedAt) ?? 0) > (validDate(previousEvidence.submittedAt) ?? 0)
        )
          latestEvidence.set(targetCode, { score, submittedAt: route.result!.submittedAt })
      }
    }
    const knowledgeCodes = new Set([
      ...[...occurrences.values()].filter((item) => item.targetType === 'knowledge').map((item) => item.targetCode),
      ...[...latestEvidence.entries()]
        .filter(([code, evidence]) => {
          const diagnosisAt = latestDiagnosisAt.get(code)
          return (
            evidence.score < 100 &&
            (!diagnosisAt || (validDate(evidence.submittedAt) ?? 0) > (validDate(diagnosisAt) ?? 0))
          )
        })
        .map(([code]) => code),
    ])
    const knowledgeWeaknesses = [...knowledgeCodes].flatMap((targetCode) => {
      const evidence = latestEvidence.get(targetCode)
      const diagnosisAt = latestDiagnosisAt.get(targetCode)
      const evidenceIsNewer = Boolean(
        evidence && (!diagnosisAt || (validDate(evidence.submittedAt) ?? 0) > (validDate(diagnosisAt) ?? 0)),
      )
      if (evidenceIsNewer && evidence?.score === 100) return []
      const occurrence = occurrences.get(`knowledge:${targetCode}`)
      return [
        {
          targetType: 'knowledge' as const,
          targetCode,
          label: labelOf(targetCode),
          occurrences: occurrence?.occurrences ?? 1,
          masteryPercentage: evidenceIsNewer ? evidence!.score : null,
        },
      ]
    })
    const reasoningWeaknesses = [...occurrences.values()]
      .filter((item) => item.targetType === 'reasoning')
      .map((item) => ({
        ...item,
        label: labelOf(item.targetCode),
        masteryPercentage: null,
      }))
    const weaknesses = [...knowledgeWeaknesses, ...reasoningWeaknesses].sort(
      (left, right) => right.occurrences - left.occurrences || left.targetCode.localeCompare(right.targetCode),
    )

    const diagnostics = records
      .filter((record) => record.diagnosis)
      .sort(
        (left, right) =>
          (validDate(right.diagnosisCreatedAt || right.updatedAt) ?? 0) -
          (validDate(left.diagnosisCreatedAt || left.updatedAt) ?? 0),
      )
    const latestDiagnosisRecord = diagnostics[0]
    const latestDiagnosis = latestDiagnosisRecord?.diagnosis
    const firstGap = latestDiagnosis?.knowledgeGapCodes[0]
    const latestRoute = latestDiagnosisRecord?.route
    const routeContext = latestRoute
      ? latestRoute.result
        ? `关联学习路线最终测试得分 ${round(latestRoute.result.score)} 分`
        : `关联学习路线已完成 ${latestRoute.completedSteps}/${latestRoute.totalSteps} 步`
      : '该研讨尚未关联学习路线'
    const aiSummary = latestDiagnosis
      ? `最近完成的研讨记录了 ${latestDiagnosis.knowledgeGapCodes.length} 个知识薄弱目标和 ${latestDiagnosis.reasoningIssueCodes.length} 个推理问题${firstGap ? `，包括${labelOf(firstGap)}` : ''}；${routeContext}。`
      : routes.length
        ? (() => {
            const latestRoute = sortedByUpdatedAt(
              routes.map((route) => ({ ...route, updatedAt: routeActivityAt(route) })),
            )[0]
            const latestResultRoute = sortedByUpdatedAt(
              resultRoutes.map((route) => ({ ...route, updatedAt: routeActivityAt(route) })),
            )[0]
            const recentContext = latestRoute.result
              ? `最近路线最终测试得分 ${round(latestRoute.result.score)} 分`
              : `最近路线已完成 ${latestRoute.completedSteps}/${latestRoute.totalSteps} 步，${latestRoute.progressLabel}`
            const resultContext = latestResultRoute
              ? `最近一次最终测试得分 ${round(latestResultRoute.result!.score)} 分`
              : '尚无最终测试结果'
            return `当前有 ${routes.length} 条学习路线，其中 ${resultRoutes.length} 条已有最终测试结果、${routes.length - resultRoutes.length} 条仍在学习；${recentContext}；${resultContext}。`
          })()
        : '完成研讨诊断和学习路线测试后，这里会显示对应的学习总结。'

    const pageLimit = Math.min(100, Math.max(1, Math.floor(limit)))
    const pageOffset = Math.max(0, Math.floor(offset))
    const pageItems = records.slice(pageOffset, pageOffset + pageLimit).map((record) => ({
      id: record.id,
      session: record.session,
      summaryText: record.summaryText,
      updatedAt: record.updatedAt,
      action: record.action,
    }))
    const routesByActivity = sortedByUpdatedAt(routes.map((route) => ({ ...route, updatedAt: routeActivityAt(route) })))
    const activeRoute =
      routesByActivity.find((route) => route.status !== 'completed') || routesByActivity.find((route) => !route.result)
    const latestResultRoute = routesByActivity.find((route) => route.result)
    const actionForRoute = (route: DemoRoute) =>
      route.result
        ? { kind: 'result' as const, sessionId: route.sessionLocator, routeId: route.id, label: '查看结果解析' }
        : { kind: 'route' as const, sessionId: route.sessionLocator, routeId: route.id, label: '继续学习路线' }
    const nextAction =
      (activeRoute && actionForRoute(activeRoute)) ||
      (latestResultRoute && actionForRoute(latestResultRoute)) ||
      records[0]?.action ||
      null
    return {
      summary: {
        dashboard: {
          dataBasis: 'synthetic_demo',
          periodStart: current.periodStart,
          periodEnd: current.periodEnd,
          masteryScore: current.score,
          masteryDelta,
          masterySampleCount: current.sampleCount,
          studyMinutes: Math.floor(totalReadingSeconds / 60),
          studyDurationBasis: 'recorded_reading',
          planCompletionRate,
          testedKnowledgeCount: testedTargets.size,
          aiDiagnosticCount: diagnostics.length,
          statusLabel,
          trend,
          weaknesses,
          aiSummary,
        },
        nextAction,
      },
      items: pageItems,
      total: records.length,
      limit: pageLimit,
      offset: pageOffset,
    }
  }
}
