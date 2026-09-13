import type { TeacherContentSection } from './TeacherContentWorkspace.vue'
import type { TeacherFollowUpContext, TeacherInsightsSection } from './TeacherInsightsWorkspace.vue'
import type { TeacherWorkspace } from './TeacherWorkspaceNav.vue'

export type TeacherWorkspaceTarget = {
  workspace: TeacherWorkspace
  classId?: number
  contentSection?: TeacherContentSection
  insightsSection?: TeacherInsightsSection
  snapshotId?: string
  followUpContext?: TeacherFollowUpContext
}

type Query = Record<string, string | undefined>

function positiveInteger(value?: string): string | undefined {
  return /^\d+$/.test(value || '') && Number(value) > 0 ? value : undefined
}

export function ownedTeacherClassId(
  requestedClassId: number | undefined,
  classes: Array<{ id: number }>,
): number | undefined {
  return requestedClassId && classes.some((item) => item.id === requestedClassId) ? requestedClassId : undefined
}

export function normalizeTeacherWorkspaceQuery(query: Query = {}): TeacherWorkspaceTarget {
  const section = query.section
  const classValue = positiveInteger(query.classId)
  const classId = classValue ? Number(classValue) : undefined
  if (query.tab === 'pbl') {
    if (section === 'work-items' || section === 'diagnostics') {
      return {
        workspace: 'problems',
        classId,
        contentSection: 'pbl-diagnostics',
        snapshotId: positiveInteger(query.snapshotId),
      }
    }
    if (section === 'follow-ups' || section === 'results') {
      return {
        workspace: 'reports',
        classId,
        insightsSection: 'pbl-follow-ups',
        followUpContext: {
          sessionId: positiveInteger(query.sessionId),
          studentId: positiveInteger(query.studentId),
          planId: positiveInteger(query.planId) ? Number(query.planId) : undefined,
        },
      }
    }
    return { workspace: 'pbl', classId }
  }
  if (query.tab === 'problems') {
    return {
      workspace: 'problems',
      classId,
      contentSection: section === 'resources' ? 'resources' : 'pbl-diagnostics',
      snapshotId: positiveInteger(query.snapshotId),
    }
  }
  if (query.tab === 'reports') {
    const insightsSection: TeacherInsightsSection =
      section === 'analytics' || section === 'records' ? section : 'pbl-follow-ups'
    return {
      workspace: 'reports',
      classId,
      insightsSection,
      followUpContext:
        insightsSection === 'pbl-follow-ups'
          ? {
              sessionId: positiveInteger(query.sessionId),
              studentId: positiveInteger(query.studentId),
              planId: positiveInteger(query.planId) ? Number(query.planId) : undefined,
            }
          : undefined,
    }
  }
  return { workspace: 'overview', classId }
}
