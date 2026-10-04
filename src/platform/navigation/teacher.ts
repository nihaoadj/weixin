import { backOrRoute, goReplace, relaunchTo, ROUTES } from '@/platform/navigation'
import { getRuntimeMode } from '@/platform/runtime'

type PblWorkStatus = 'pending' | 'responded' | 'task_published' | 'closed'

export type TeacherWorkspace = 'overview' | 'insights' | 'content' | 'pbl'

export type TeacherInsightsPanel = 'overview' | 'progress' | 'knowledge' | 'students'
export type TeacherContentResource = 'cases' | 'question-bank'
export type TeacherSessionId = number | string
export type TeacherContentStatus =
  'all' | 'draft' | 'pending' | 'published' | 'approved' | 'rejected' | 'disabled' | 'active' | 'archived'
export type TeacherPblSection = 'classrooms' | 'diagnostics'
export type TeacherReviewKind = 'pending_review' | 'needs_changes' | 'generation_failed'

export type TeacherWorkspaceTarget =
  | { workspace: 'overview' }
  | {
      workspace: 'insights'
      panel?: TeacherInsightsPanel
      classId?: number
      sessionId?: TeacherSessionId
      dateFrom?: string
      dateTo?: string
    }
  | {
      workspace: 'content'
      resource?: TeacherContentResource
      classId?: number
      keyword?: string
      status?: TeacherContentStatus
    }
  | {
      workspace: 'pbl'
      section?: TeacherPblSection
      reviewKind?: TeacherReviewKind
      classId?: number
      sessionId?: TeacherSessionId
      workStatus?: PblWorkStatus
      snapshotId?: number
    }

export type TeacherDetailFallback =
  | Extract<TeacherWorkspaceTarget, { workspace: 'insights' }>
  | Extract<TeacherWorkspaceTarget, { workspace: 'content' }>
  | Extract<TeacherWorkspaceTarget, { workspace: 'pbl' }>

export type TeacherWorkspaceQuery = Record<string, string | undefined>
type NavigationParams = Record<string, string | number | undefined>

const INSIGHTS_PANELS: readonly TeacherInsightsPanel[] = ['overview', 'progress', 'knowledge', 'students']
const CONTENT_RESOURCES: readonly TeacherContentResource[] = ['cases', 'question-bank']
const PBL_SECTIONS: readonly TeacherPblSection[] = ['classrooms', 'diagnostics']
const REVIEW_KINDS: readonly TeacherReviewKind[] = ['pending_review', 'needs_changes', 'generation_failed']
const PBL_WORK_STATUSES: readonly PblWorkStatus[] = ['pending', 'responded', 'task_published', 'closed']

function positiveId(value: string | number | undefined): number | undefined {
  if (typeof value === 'number') return Number.isSafeInteger(value) && value > 0 ? value : undefined
  if (!value || !/^\d+$/.test(value)) return undefined
  const parsed = Number(value)
  return Number.isSafeInteger(parsed) && parsed > 0 ? parsed : undefined
}

function sessionId(value: string | number | undefined): TeacherSessionId | undefined {
  if (typeof value === 'number') return positiveId(value)
  if (!value) return undefined
  if (getRuntimeMode() === 'demo' && /^demo-(?:pbl-[1-9]\d*|[1-9]\d*)$/.test(value)) return value
  return positiveId(value)
}

function member<T extends string>(value: string | undefined, allowed: readonly T[]): T | undefined {
  return allowed.includes(value as T) ? (value as T) : undefined
}

function isoDate(value: string | undefined): string | undefined {
  if (!value || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return undefined
  const timestamp = Date.parse(`${value}T00:00:00.000Z`)
  return Number.isFinite(timestamp) && new Date(timestamp).toISOString().slice(0, 10) === value ? value : undefined
}

function dateRange(
  query: TeacherWorkspaceQuery,
): Pick<Extract<TeacherWorkspaceTarget, { workspace: 'insights' }>, 'dateFrom' | 'dateTo'> {
  const dateFrom = isoDate(query.dateFrom)
  const dateTo = isoDate(query.dateTo)
  if (dateFrom && dateTo && dateFrom > dateTo) return {}
  return { ...(dateFrom ? { dateFrom } : {}), ...(dateTo ? { dateTo } : {}) }
}

function insightsPanel(value: string | undefined): TeacherInsightsPanel | undefined {
  if (value === 'mastery') return 'knowledge'
  if (value === 'analytics') return 'overview'
  return member(value, INSIGHTS_PANELS)
}

function pblTarget(query: TeacherWorkspaceQuery): Extract<TeacherWorkspaceTarget, { workspace: 'pbl' }> {
  const section =
    query.section === 'work-items' || query.section === 'pbl-diagnostics'
      ? 'diagnostics'
      : member(query.section, PBL_SECTIONS)
  const classId = positiveId(query.classId)
  const selectedSessionId = sessionId(query.sessionId)
  const snapshotId = positiveId(query.snapshotId)
  const workStatus = member(query.workStatus, PBL_WORK_STATUSES)
  const reviewKind = member(query.reviewKind, REVIEW_KINDS)
  return {
    workspace: 'pbl',
    section: section || 'classrooms',
    ...(classId ? { classId } : {}),
    ...(selectedSessionId !== undefined ? { sessionId: selectedSessionId } : {}),
    ...(workStatus ? { workStatus } : {}),
    ...(reviewKind ? { reviewKind } : {}),
    ...(snapshotId ? { snapshotId } : {}),
  }
}

/** Keep resource detail returns limited to their owner and supported filters. */
export function teacherContentReturnParams(
  query: TeacherWorkspaceQuery = {},
  resource: TeacherContentResource = 'cases',
): { resource: TeacherContentResource; keyword?: string; status?: TeacherContentStatus } {
  if (['questions', 'knowledge-cards'].includes(query.resource || '')) return { resource: 'cases' }
  const keyword = query.keyword?.trim().slice(0, 100)
  return { resource, ...(keyword ? { keyword } : {}) }
}

/** Resolve canonical roots and legacy teacher query aliases into one typed target. */
export function parseTeacherWorkspaceTarget(query: TeacherWorkspaceQuery = {}): TeacherWorkspaceTarget {
  const key = query.tab || query.workspace
  const section = query.section

  if (key === 'work-items') return pblTarget({ ...query, section: 'diagnostics' })
  if (section === 'work-items' || section === 'diagnostics' || section === 'pbl-diagnostics') {
    return pblTarget(query)
  }

  // Results moved from the former PBL/results entry to the read-only insights workspace.
  if (key === 'results' || section === 'results') {
    const classId = positiveId(query.classId)
    const selectedSessionId = sessionId(query.sessionId)
    return {
      workspace: 'insights',
      panel: 'progress',
      ...(classId ? { classId } : {}),
      ...(selectedSessionId !== undefined ? { sessionId: selectedSessionId } : {}),
      ...dateRange(query),
    }
  }

  if (key === 'pbl') return pblTarget(query)
  if (key === 'reports' || key === 'insights') {
    const panel = insightsPanel(query.panel)
    const classId = positiveId(query.classId)
    const selectedSessionId = sessionId(query.sessionId)
    return {
      workspace: 'insights',
      ...(panel ? { panel } : {}),
      ...(classId ? { classId } : {}),
      ...(selectedSessionId !== undefined ? { sessionId: selectedSessionId } : {}),
      ...dateRange(query),
    }
  }
  if (key === 'problems' || key === 'content') {
    if (['questions', 'knowledge-cards'].includes(query.resource || section || '')) {
      return { workspace: 'content', resource: 'cases' }
    }
    const resource = member(query.resource || section, CONTENT_RESOURCES)
    const classId = positiveId(query.classId)
    const keyword = query.keyword?.trim().slice(0, 100)
    return {
      workspace: 'content',
      resource: resource || (section === 'question-bank' ? 'question-bank' : 'cases'),
      ...(classId ? { classId } : {}),
      ...(keyword ? { keyword } : {}),
    }
  }
  return pblTarget(query)
}

/** Map a workspace to its registered root route; callers never supply paths. */
export function teacherWorkspacePath(workspace: TeacherWorkspace): string {
  switch (workspace) {
    case 'overview':
      return ROUTES.teacherPbl
    case 'insights':
      return ROUTES.teacherInsights
    case 'content':
      return ROUTES.teacherContent
    case 'pbl':
      return ROUTES.teacherPbl
  }
}

function paramsFor(target: TeacherWorkspaceTarget): NavigationParams {
  switch (target.workspace) {
    case 'overview':
      return {}
    case 'insights': {
      const classId = positiveId(target.classId)
      const selectedSessionId = sessionId(target.sessionId)
      const panel = member(target.panel, INSIGHTS_PANELS)
      return {
        ...(panel ? { panel } : {}),
        ...(classId ? { classId } : {}),
        ...(selectedSessionId !== undefined ? { sessionId: selectedSessionId } : {}),
        ...dateRange({ dateFrom: target.dateFrom, dateTo: target.dateTo }),
      }
    }
    case 'content': {
      const resource = member(target.resource, CONTENT_RESOURCES)
      const classId = positiveId(target.classId)
      const keyword = target.keyword?.trim().slice(0, 100)
      return {
        ...(resource ? { resource } : {}),
        ...(classId ? { classId } : {}),
        ...(keyword ? { keyword } : {}),
      }
    }
    case 'pbl': {
      const section = member(target.section, PBL_SECTIONS)
      const reviewKind = member(target.reviewKind, REVIEW_KINDS)
      const classId = positiveId(target.classId)
      const selectedSessionId = sessionId(target.sessionId)
      const workStatus = member(target.workStatus, PBL_WORK_STATUSES)
      const snapshotId = positiveId(target.snapshotId)
      return {
        ...(section ? { section } : {}),
        ...(reviewKind ? { reviewKind } : {}),
        ...(classId ? { classId } : {}),
        ...(selectedSessionId !== undefined ? { sessionId: selectedSessionId } : {}),
        ...(workStatus ? { workStatus } : {}),
        ...(snapshotId ? { snapshotId } : {}),
      }
    }
  }
}

/** Main navigation is an atomic root switch, so teacher workspace stacks do not accumulate. */
export function relaunchToTeacherWorkspace(target: TeacherWorkspaceTarget): void {
  const path =
    target.workspace === 'pbl' && target.section === 'diagnostics'
      ? ROUTES.teacherTestQueue
      : teacherWorkspacePath(target.workspace)
  relaunchTo(path, paramsFor(target))
}

/** Historical detail links retain only validated IDs and the Insights filter context. */
export function redirectLegacyTeacherInsightsDetail(kind: 'student' | 'result', query: Record<string, unknown>): void {
  const target = parseTeacherWorkspaceTarget({ ...query, tab: 'insights' })
  if (target.workspace !== 'insights') return
  const params = paramsFor({ ...target, panel: target.panel || (kind === 'student' ? 'students' : 'progress') })
  if (kind === 'student') {
    const studentId =
      typeof query.studentId === 'string' || typeof query.studentId === 'number'
        ? positiveId(query.studentId)
        : undefined
    if (!target.classId || !studentId) {
      relaunchToTeacherWorkspace(target)
      return
    }
    goReplace(ROUTES.teacherInsightsStudentDetail, { ...params, studentId })
    return
  }
  const resultId = typeof query.resultId === 'string' ? query.resultId : ''
  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(resultId)) {
    relaunchToTeacherWorkspace(target)
    return
  }
  goReplace(ROUTES.teacherInsightsResult, { ...params, resultId })
}

function defaultTarget(workspace: TeacherWorkspace): TeacherWorkspaceTarget {
  switch (workspace) {
    case 'overview':
      return { workspace }
    case 'insights':
      return { workspace }
    case 'content':
      return { workspace }
    case 'pbl':
      return { workspace }
  }
}

/** Shared teacher navigation buttons use reLaunch so root workspaces never stack. */
export function switchTeacherWorkspace(workspace: TeacherWorkspace): void
export function switchTeacherWorkspace(target: TeacherWorkspaceTarget): void
export function switchTeacherWorkspace(value: TeacherWorkspace | TeacherWorkspaceTarget): void {
  relaunchToTeacherWorkspace(typeof value === 'string' ? defaultTarget(value) : value)
}

/**
 * Return through native history when possible; a directly opened detail falls
 * back to its owning root and the typed filters that led to it.
 */
export function backFromTeacherDetail(target: TeacherDetailFallback, delta = 1): void {
  const path =
    target.workspace === 'pbl' && target.section === 'diagnostics'
      ? ROUTES.teacherTestQueue
      : teacherWorkspacePath(target.workspace)
  backOrRoute(path, paramsFor(target), delta)
}
