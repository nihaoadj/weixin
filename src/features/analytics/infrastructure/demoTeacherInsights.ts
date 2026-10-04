import { getSessionContext } from '@/platform/session/context'
import { AppError } from '@/types/errors'
import type {
  TeacherInsightsCohortProgress,
  TeacherInsightsDiscussion,
  TeacherInsightsDiagnosis,
  TeacherInsightsDiagnosisPage,
  TeacherInsightsFindingGroup,
  TeacherInsightsFilters,
  TeacherInsightsKnowledgePage,
  TeacherInsightsKnowledgeRow,
  TeacherInsightsOverview,
  TeacherInsightsPeriodResults,
  TeacherInsightsResultSummary,
  TeacherInsightsRouteProgress,
  TeacherInsightsScope,
  TeacherInsightsSessionId,
  TeacherInsightsStudent,
  TeacherInsightsStudentDetail,
  TeacherInsightsStudentPage,
  TeacherInsightsStudentFilters,
} from '../domain/teacherInsights'

const SHANGHAI_OFFSET_MS = 8 * 60 * 60 * 1000
const DAY_MS = 24 * 60 * 60 * 1000

export interface DemoTeacherInsightsScope {
  classes: Array<{ id: number; name: string; code: string; status?: string }>
  students: Array<{ id: number; name: string; classIds: number[] }>
}

export interface DemoTeacherInsightsQuestionFact {
  questionType?: 'single_choice' | 'multiple_choice' | 'short_answer'
  pointCode: string
  selectedOption?: number
  correctOption?: number
  selectedOptions?: number[]
  correctOptions?: number[]
  pointsAwarded?: number
  pointsPossible?: number
}

export interface DemoTeacherInsightsRouteFact {
  routeId: string
  title: string
  classId: number
  className: string
  sessionId: TeacherInsightsSessionId
  studentId: number
  studentName: string
  publishedAt: string | null
  updatedAt: string
  stepProgress: { completedSteps: number; totalSteps: number }
  steps: Array<{
    id: string
    position: number
    kind: string
    status: string
    completedAt?: string
  }>
  accumulatedReadingSeconds: number
  test: {
    id: string
    generationState: string
    reviewState: string
    attemptStatus: string | null
    resultId: string | null
  }
  result?: {
    id: string
    score: number
    correctCount: number
    questionCount: number
    submittedAt: string
    formatVersion: 'single_choice_v1' | 'mixed_v2'
    questions: DemoTeacherInsightsQuestionFact[]
  }
}

export interface DemoTeacherInsightsDiagnosisFact {
  participationId: TeacherInsightsSessionId
  sessionId: TeacherInsightsSessionId
  classId: number
  className: string
  studentId: number
  studentName: string
  completedAt: string
  knowledgeGapCodes: string[]
  reasoningIssueCodes: string[]
  knowledgeGaps: Array<{ code: string; summary: string }>
  reasoningIssues: Array<{ code: string; summary: string }>
}

export type DemoTeacherInsightsDiscussionFact = TeacherInsightsDiscussion & { studentName: string }

type MaybePromise<T> = T | Promise<T>

/**
 * All three readers must return only the current Demo teacher's scope. Route facts
 * are read-only Learning projections; diagnoses are effective classroom completion
 * snapshots with codes and approved short summaries only.
 */
export interface DemoTeacherInsightsFactsPort {
  readScope(): MaybePromise<DemoTeacherInsightsScope>
  readRoutes(): MaybePromise<DemoTeacherInsightsRouteFact[]>
  readDiagnoses(): MaybePromise<DemoTeacherInsightsDiagnosisFact[]>
  readDiscussions(): MaybePromise<DemoTeacherInsightsDiscussionFact[]>
}

const emptyPort: DemoTeacherInsightsFactsPort = {
  readScope: () => ({ classes: [], students: [] }),
  readRoutes: () => [],
  readDiagnoses: () => [],
  readDiscussions: () => [],
}

let factsPort = emptyPort

export function configureDemoTeacherInsightsFacts(port: DemoTeacherInsightsFactsPort): void {
  factsPort = port
}

function requireTeacher(): void {
  const actor = getSessionContext()
  if (!actor || actor.role !== 'teacher') throw new AppError('仅教师可查看课堂学情', { code: 'FORBIDDEN' })
  if (actor.openid !== 'demo_teacher') throw new AppError('班级不存在', { code: 'RESOURCE_NOT_FOUND' })
}

function requirePositiveId(value: number | undefined, label: string): void {
  if (value !== undefined && (!Number.isInteger(value) || value <= 0))
    throw new AppError(`${label}无效`, { code: 'VALIDATION_ERROR' })
}

function dateEpoch(value: string): number {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) throw new AppError('日期范围无效', { code: 'INVALID_DATE_RANGE' })
  const timestamp = Date.parse(`${value}T00:00:00Z`)
  if (!Number.isFinite(timestamp) || new Date(timestamp).toISOString().slice(0, 10) !== value)
    throw new AppError('日期范围无效', { code: 'INVALID_DATE_RANGE' })
  return timestamp
}

function shanghaiDay(timestamp: number): string {
  return new Date(timestamp + SHANGHAI_OFFSET_MS).toISOString().slice(0, 10)
}

interface DateWindow {
  dateFrom: string
  dateTo: string
  start: number
  end: number
}

function dateWindow(dateFrom?: string, dateTo?: string): DateWindow {
  const dateToValue = dateTo ?? shanghaiDay(Date.now())
  const dateToEpoch = dateEpoch(dateToValue)
  const dateFromValue = dateFrom ?? new Date(dateToEpoch - 29 * DAY_MS).toISOString().slice(0, 10)
  const dateFromEpoch = dateEpoch(dateFromValue)
  if (dateFromEpoch > dateToEpoch || dateToEpoch - dateFromEpoch > 366 * DAY_MS)
    throw new AppError('日期范围无效', { code: 'INVALID_DATE_RANGE' })
  return {
    dateFrom: dateFromValue,
    dateTo: dateToValue,
    start: dateFromEpoch - SHANGHAI_OFFSET_MS,
    end: dateToEpoch + DAY_MS - SHANGHAI_OFFSET_MS,
  }
}

function inVisibleWindow(value: string | null | undefined, range: DateWindow, asOf: number): boolean {
  if (!value) return false
  const timestamp = Date.parse(value)
  return Number.isFinite(timestamp) && timestamp >= range.start && timestamp < range.end && timestamp <= asOf
}

function sameSession(value: TeacherInsightsSessionId, filter: TeacherInsightsSessionId | undefined): boolean {
  return filter === undefined || String(value) === String(filter)
}

function validatePagination(limit: number, offset: number): void {
  if (!Number.isInteger(limit) || limit < 1 || limit > 100 || !Number.isInteger(offset) || offset < 0)
    throw new AppError('分页参数无效', { code: 'VALIDATION_ERROR' })
}

function roundOne(value: number): number {
  return Math.round((value + Number.EPSILON) * 10) / 10
}

function completedResult(fact: DemoTeacherInsightsRouteFact) {
  const result = fact.result
  return result && fact.test.resultId === result.id ? result : undefined
}

function inPointRange(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value) && Number.isInteger(value) && value >= 0 && value <= 3
}

function validOptions(value: unknown, allowEmpty: boolean): value is number[] {
  return (
    Array.isArray(value) &&
    (allowEmpty || value.length > 0) &&
    value.every(inPointRange) &&
    new Set(value).size === value.length
  )
}

function isFiniteNumber(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value)
}

function knowledgeStatistics(results: DemoTeacherInsightsRouteFact[]): TeacherInsightsKnowledgeRow[] {
  const points = new Map<string, Omit<TeacherInsightsKnowledgeRow, 'accuracyRate' | 'shortAnswerScoreRate'>>()
  for (const route of results) {
    const result = completedResult(route)
    if (!result) continue
    for (const question of result.questions) {
      const pointCode = typeof question.pointCode === 'string' ? question.pointCode.trim() : ''
      if (!pointCode) continue
      let item = points.get(pointCode)
      if (!item) {
        item = {
          pointCode,
          correctCount: 0,
          objectiveCount: 0,
          invalidObjectiveCount: 0,
          shortAnswerCount: 0,
          invalidShortAnswerCount: 0,
          pointsAwarded: 0,
          pointsPossible: 0,
        }
        points.set(pointCode, item)
      }
      const kind = question.questionType ?? 'single_choice'
      if (kind === 'short_answer') {
        const earned = question.pointsAwarded
        const possible = question.pointsPossible
        if (isFiniteNumber(earned) && isFiniteNumber(possible) && earned >= 0 && earned <= possible && possible > 0) {
          item.shortAnswerCount += 1
          item.pointsAwarded += earned
          item.pointsPossible += possible
        } else {
          item.invalidShortAnswerCount += 1
        }
      } else if (kind === 'single_choice') {
        const selected = question.selectedOption
        const correct = question.correctOption
        if (inPointRange(selected) && inPointRange(correct)) {
          item.objectiveCount += 1
          item.correctCount += Number(selected === correct)
        } else {
          item.invalidObjectiveCount += 1
        }
      } else if (kind === 'multiple_choice') {
        const selected = question.selectedOptions
        const correct = question.correctOptions
        if (validOptions(selected, true) && validOptions(correct, false)) {
          item.objectiveCount += 1
          const selectedSorted = [...selected].sort((a, b) => a - b)
          const correctSorted = [...correct].sort((a, b) => a - b)
          item.correctCount += Number(
            selectedSorted.length === correctSorted.length &&
              selectedSorted.every((option, index) => option === correctSorted[index]),
          )
        } else {
          item.invalidObjectiveCount += 1
        }
      }
    }
  }
  return [...points.values()]
    .sort((a, b) => a.pointCode.localeCompare(b.pointCode))
    .map((item) => ({
      ...item,
      accuracyRate: item.objectiveCount ? roundOne((item.correctCount * 100) / item.objectiveCount) : null,
      shortAnswerScoreRate: item.pointsPossible ? roundOne((item.pointsAwarded * 100) / item.pointsPossible) : null,
    }))
}

function resultSummary(fact: DemoTeacherInsightsRouteFact): TeacherInsightsResultSummary | undefined {
  const result = completedResult(fact)
  if (!result) return undefined
  return {
    resultId: result.id,
    routeId: fact.routeId,
    classId: fact.classId,
    sessionId: fact.sessionId,
    studentId: fact.studentId,
    score: result.score,
    completedAt: result.submittedAt,
    formatVersion: result.formatVersion,
  }
}

function diagnosisRow(
  fact: DemoTeacherInsightsDiagnosisFact,
  className: string,
  studentName: string,
): TeacherInsightsDiagnosis {
  const mapFindings = (values: DemoTeacherInsightsDiagnosisFact['knowledgeGaps']) =>
    values.map(({ code, summary }) => ({ code, summary: summary.slice(0, 160) }))
  return {
    participationId: fact.participationId,
    sessionId: fact.sessionId,
    classId: fact.classId,
    className,
    studentId: fact.studentId,
    studentName,
    completedAt: fact.completedAt,
    knowledgeGapCodes: [...fact.knowledgeGapCodes],
    reasoningIssueCodes: [...fact.reasoningIssueCodes],
    knowledgeGaps: mapFindings(fact.knowledgeGaps),
    reasoningIssues: mapFindings(fact.reasoningIssues),
  }
}

function findingGroups(
  records: DemoTeacherInsightsDiagnosisFact[],
  type: 'knowledge' | 'reasoning',
): TeacherInsightsFindingGroup[] {
  const groups = new Map<string, { students: Set<number>; diagnosisCount: number; lastCompletedAt: string }>()
  for (const record of records) {
    const codes = type === 'knowledge' ? record.knowledgeGapCodes : record.reasoningIssueCodes
    for (const code of new Set(codes)) {
      const group = groups.get(code) ?? {
        students: new Set<number>(),
        diagnosisCount: 0,
        lastCompletedAt: record.completedAt,
      }
      group.students.add(record.studentId)
      group.diagnosisCount += 1
      if (Date.parse(record.completedAt) > Date.parse(group.lastCompletedAt)) group.lastCompletedAt = record.completedAt
      groups.set(code, group)
    }
  }
  return [...groups.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([code, value]) => ({
      code,
      studentCount: value.students.size,
      diagnosisCount: value.diagnosisCount,
      lastCompletedAt: value.lastCompletedAt,
    }))
}

interface LoadedFacts {
  scope: TeacherInsightsScope
  classes: DemoTeacherInsightsScope['classes']
  roster: DemoTeacherInsightsScope['students']
  allRoutes: DemoTeacherInsightsRouteFact[]
  allDiagnoses: DemoTeacherInsightsDiagnosisFact[]
  published: DemoTeacherInsightsRouteFact[]
  results: DemoTeacherInsightsRouteFact[]
  diagnoses: DemoTeacherInsightsDiagnosisFact[]
  names: Map<number, string>
  allDiscussions: DemoTeacherInsightsDiscussionFact[]
  discussions: DemoTeacherInsightsDiscussionFact[]
}

async function loadFacts(filters: TeacherInsightsFilters = {}): Promise<LoadedFacts> {
  requireTeacher()
  requirePositiveId(filters.classId, '班级编号')
  if (typeof filters.sessionId === 'number') requirePositiveId(filters.sessionId, '课堂编号')
  else if (typeof filters.sessionId === 'string' && !filters.sessionId.trim())
    throw new AppError('课堂编号无效', { code: 'VALIDATION_ERROR' })
  const range = dateWindow(filters.dateFrom, filters.dateTo)
  const asOf = Date.now()
  const scopeData = await factsPort.readScope()
  const allClasses = scopeData.classes.slice().sort((a, b) => a.id - b.id)
  const allowedClassIds = new Set(allClasses.map((item) => item.id))
  if (filters.classId !== undefined && !allowedClassIds.has(filters.classId))
    throw new AppError('班级不存在', { code: 'RESOURCE_NOT_FOUND' })
  const classes = filters.classId === undefined ? allClasses : allClasses.filter((item) => item.id === filters.classId)
  const classIds = new Set(classes.map((item) => item.id))
  const [allRouteFacts, allDiagnosisFacts, allDiscussionFacts] = await Promise.all([
    factsPort.readRoutes(),
    factsPort.readDiagnoses(),
    factsPort.readDiscussions(),
  ])
  const allRoutes = allRouteFacts.filter((item) => allowedClassIds.has(item.classId) && classIds.has(item.classId))
  const allDiagnoses = allDiagnosisFacts.filter(
    (item) => allowedClassIds.has(item.classId) && classIds.has(item.classId),
  )
  const allDiscussions = allDiscussionFacts.filter(
    (item) => allowedClassIds.has(item.classId) && classIds.has(item.classId),
  )
  const discussions = allDiscussions.filter(
    (item) =>
      sameSession(item.sessionId, filters.sessionId) &&
      (item.startedAt === null || inVisibleWindow(item.startedAt, range, asOf)),
  )
  const sessionRoutes = allRoutes.filter((item) => sameSession(item.sessionId, filters.sessionId))
  const sessionDiagnoses = allDiagnoses.filter((item) => sameSession(item.sessionId, filters.sessionId))
  const published = allRoutes.filter(
    (item) =>
      sameSession(item.sessionId, filters.sessionId) &&
      item.publishedAt &&
      inVisibleWindow(item.publishedAt, range, asOf),
  )
  const results = sessionRoutes.filter(
    (item) => completedResult(item) && inVisibleWindow(item.result?.submittedAt, range, asOf),
  )
  const diagnoses = sessionDiagnoses.filter((item) => inVisibleWindow(item.completedAt, range, asOf))
  const selectedIds = new Set(classes.map((item) => item.id))
  const roster = scopeData.students.filter((student) => student.classIds.some((id) => selectedIds.has(id)))
  const names = new Map<number, string>()
  for (const item of roster) names.set(item.id, item.name)
  for (const item of [...allRoutes, ...allDiagnoses, ...allDiscussions]) {
    if (!names.has(item.studentId)) names.set(item.studentId, item.studentName)
  }
  const timestamp = new Date(asOf).toISOString()
  const scope: TeacherInsightsScope = {
    classId: filters.classId ?? null,
    className: filters.classId === undefined ? null : (classes[0]?.name ?? null),
    classIds: classes.map((item) => item.id),
    sessionId: filters.sessionId ?? null,
    dateFrom: range.dateFrom,
    dateTo: range.dateTo,
    timezone: 'Asia/Shanghai',
    asOf: timestamp,
    metricBasis: {
      progress: 'published_route_cohort',
      results: 'completed_test_window',
      diagnoses: 'completed_diagnosis_window',
    },
  }
  return {
    scope,
    classes,
    roster,
    allRoutes,
    allDiagnoses,
    allDiscussions,
    discussions,
    published,
    results,
    diagnoses,
    names,
  }
}

function cohortProgress(routes: DemoTeacherInsightsRouteFact[], asOf: string): TeacherInsightsCohortProgress {
  const completed = routes.filter((item) => {
    const result = completedResult(item)
    return result && Date.parse(result.submittedAt) <= Date.parse(asOf)
  }).length
  return {
    publishedRoutes: routes.length,
    completedTests: completed,
    completionRate: routes.length ? roundOne((completed * 100) / routes.length) : null,
    gradingTests: routes.filter((item) => item.test.attemptStatus === 'grading' && !completedResult(item)).length,
  }
}

function periodResults(routes: DemoTeacherInsightsRouteFact[]): TeacherInsightsPeriodResults {
  const summaries = routes.map(resultSummary).filter((item): item is TeacherInsightsResultSummary => Boolean(item))
  const formatCounts: Record<string, number> = {}
  for (const item of summaries) formatCounts[item.formatVersion] = (formatCounts[item.formatVersion] ?? 0) + 1
  return {
    completedTests: summaries.length,
    averageScore: summaries.length
      ? roundOne(summaries.reduce((total, item) => total + item.score, 0) / summaries.length)
      : null,
    formatCounts,
  }
}

function studentRows(facts: LoadedFacts): TeacherInsightsStudent[] {
  const identities = new Set<number>(facts.roster.map((item) => item.id))
  for (const item of [...facts.published, ...facts.results, ...facts.diagnoses, ...facts.discussions])
    identities.add(item.studentId)
  const classIdsByStudent = new Map<number, Set<number>>()
  const addClass = (studentId: number, classId: number) => {
    const ids = classIdsByStudent.get(studentId) ?? new Set<number>()
    ids.add(classId)
    classIdsByStudent.set(studentId, ids)
  }
  for (const student of facts.roster) {
    for (const classId of student.classIds) if (facts.scope.classIds.includes(classId)) addClass(student.id, classId)
  }
  for (const item of [...facts.published, ...facts.results, ...facts.diagnoses, ...facts.discussions])
    addClass(item.studentId, item.classId)
  return [...identities]
    .sort((a, b) => a - b)
    .map((studentId) => {
      const ownPublished = facts.published.filter((item) => item.studentId === studentId)
      const ownResults = facts.results.filter((item) => item.studentId === studentId)
      const ownDiagnoses = facts.diagnoses.filter((item) => item.studentId === studentId)
      const ownDiscussions = facts.discussions.filter((item) => item.studentId === studentId)
      const discussionProgress = ownDiscussions.some((item) => item.startedAt === null)
        ? undefined
        : {
            participated: ownDiscussions.length,
            active: ownDiscussions.filter((item) => item.status === 'active').length,
            completed: ownDiscussions.filter((item) => item.status === 'completed').length,
          }
      const lastCompletedAt = ownResults
        .map((item) => completedResult(item)?.submittedAt)
        .filter((item): item is string => Boolean(item))
        .sort((a, b) => Date.parse(b) - Date.parse(a))[0]
      return {
        studentId,
        studentName: facts.names.get(studentId) ?? '历史学生',
        classIds: [...(classIdsByStudent.get(studentId) ?? [])].sort((a, b) => a - b),
        cohort: cohortProgress(ownPublished, facts.scope.asOf),
        periodResults: periodResults(ownResults),
        diagnosisCount: ownDiagnoses.length,
        discussionProgress,
        lastCompletedAt: lastCompletedAt ?? null,
      }
    })
}

function rowForDiagnosis(fact: DemoTeacherInsightsDiagnosisFact, loaded: LoadedFacts): TeacherInsightsDiagnosis {
  const className = loaded.classes.find((item) => item.id === fact.classId)?.name ?? fact.className
  const studentName = loaded.names.get(fact.studentId) ?? fact.studentName
  return diagnosisRow(fact, className, studentName)
}

function routeProgress(fact: DemoTeacherInsightsRouteFact): TeacherInsightsRouteProgress | undefined {
  if (!fact.publishedAt) return undefined
  return {
    routeId: fact.routeId,
    studentId: fact.studentId,
    classId: fact.classId,
    sessionId: fact.sessionId,
    publishedAt: fact.publishedAt,
    resultId: completedResult(fact)?.id ?? null,
    testGenerationState: fact.test.generationState,
    testReviewState: fact.test.reviewState,
    attemptStatus: fact.test.attemptStatus,
    completedSteps: fact.stepProgress.completedSteps,
    totalSteps: fact.stepProgress.totalSteps,
    readingSeconds: fact.accumulatedReadingSeconds,
  }
}

function compareResultsDescending(a: TeacherInsightsResultSummary, b: TeacherInsightsResultSummary): number {
  return Date.parse(b.completedAt) - Date.parse(a.completedAt) || b.resultId.localeCompare(a.resultId)
}

function validateStudentDetail(studentId: number, classId: number): void {
  requirePositiveId(studentId, '学生编号')
  requirePositiveId(classId, '班级编号')
}

export const demoTeacherInsights = {
  async overview(filters: TeacherInsightsFilters = {}): Promise<TeacherInsightsOverview> {
    const facts = await loadFacts(filters)
    const studentIds = new Set<number>([
      ...facts.published.map((item) => item.studentId),
      ...facts.results.map((item) => item.studentId),
      ...facts.diagnoses.map((item) => item.studentId),
      ...facts.discussions.filter((item) => item.startedAt !== null).map((item) => item.studentId),
    ])
    return {
      scope: facts.scope,
      cohort: cohortProgress(facts.published, facts.scope.asOf),
      periodResults: periodResults(facts.results),
      diagnosisCount: facts.diagnoses.length,
      studentCount: studentIds.size,
    }
  },

  async students(filters: TeacherInsightsFilters = {}, limit = 20, offset = 0): Promise<TeacherInsightsStudentPage> {
    validatePagination(limit, offset)
    const facts = await loadFacts(filters)
    const rows = studentRows(facts)
    return { scope: facts.scope, items: rows.slice(offset, offset + limit), total: rows.length, limit, offset }
  },

  async student(studentId: number, filters: TeacherInsightsStudentFilters): Promise<TeacherInsightsStudentDetail> {
    validateStudentDetail(studentId, filters.classId)
    const facts = await loadFacts(filters)
    const currentlyMember = facts.roster.some(
      (item) => item.id === studentId && item.classIds.includes(filters.classId),
    )
    const hasHistory =
      facts.allRoutes.some(
        (item) => item.studentId === studentId && item.publishedAt && item.classId === filters.classId,
      ) || facts.allDiagnoses.some((item) => item.studentId === studentId && item.classId === filters.classId)
    if (
      !currentlyMember &&
      !hasHistory &&
      !facts.allDiscussions.some((item) => item.studentId === studentId && item.classId === filters.classId)
    )
      throw new AppError('学生不存在', { code: 'RESOURCE_NOT_FOUND' })

    const summary = studentRows(facts).find((item) => item.studentId === studentId) ?? {
      studentId,
      studentName: facts.names.get(studentId) ?? '历史学生',
      classIds: [filters.classId],
      cohort: cohortProgress([], facts.scope.asOf),
      periodResults: periodResults([]),
      diagnosisCount: 0,
      discussionProgress: { participated: 0, active: 0, completed: 0 },
      lastCompletedAt: null,
    }
    const routes = facts.published
      .filter((item) => item.studentId === studentId)
      .map(routeProgress)
      .filter((item): item is TeacherInsightsRouteProgress => Boolean(item))
    const results = facts.results
      .filter((item) => item.studentId === studentId)
      .map(resultSummary)
      .filter((item): item is TeacherInsightsResultSummary => Boolean(item))
      .sort(compareResultsDescending)
    const diagnoses = facts.diagnoses
      .filter((item) => item.studentId === studentId)
      .map((item) => rowForDiagnosis(item, facts))
    return {
      scope: facts.scope,
      summary,
      discussions: facts.discussions
        .filter((item) => item.studentId === studentId)
        .map(({ studentName: _studentName, ...item }) => item),
      routes,
      results,
      diagnoses,
      knowledge: knowledgeStatistics(facts.results.filter((item) => item.studentId === studentId)),
    }
  },

  async knowledge(filters: TeacherInsightsFilters = {}): Promise<TeacherInsightsKnowledgePage> {
    const facts = await loadFacts(filters)
    return {
      scope: facts.scope,
      items: knowledgeStatistics(facts.results),
      resultCount: facts.results.length,
    }
  },

  async diagnostics(
    filters: TeacherInsightsFilters = {},
    limit = 20,
    offset = 0,
  ): Promise<TeacherInsightsDiagnosisPage> {
    validatePagination(limit, offset)
    const facts = await loadFacts(filters)
    const rows = facts.diagnoses
      .map((item) => rowForDiagnosis(item, facts))
      .sort(
        (a, b) =>
          Date.parse(b.completedAt) - Date.parse(a.completedAt) ||
          String(b.participationId).localeCompare(String(a.participationId)),
      )
    return {
      scope: facts.scope,
      items: rows.slice(offset, offset + limit),
      total: rows.length,
      limit,
      offset,
      knowledgeGaps: findingGroups(facts.diagnoses, 'knowledge'),
      reasoningIssues: findingGroups(facts.diagnoses, 'reasoning'),
    }
  },
}
