import { readFile } from 'node:fs/promises'
import { describe, expect, it } from 'vitest'

const pageSource = (relativePath: string) => readFile(new URL(relativePath, import.meta.url), 'utf8')

const secondaryPages = [
  '../../pages/report/report.vue',
  '../../pages/student/case-report/case-report.vue',
  '../../pages/student/case-training/case-training.vue',
  '../../pages/student/question/question.vue',
  '../../pages/student/learning/knowledge-node.vue',
  '../../pages/student/learning/source-view.vue',
  '../../pages/student/learning/plans.vue',
  '../../pages/student/learning/plan-detail.vue',
  '../../pages/student/learning/route-reading.vue',
  '../../pages/student/learning/route-case.vue',
  '../../pages/student/learning/final-test.vue',
  '../../pages/student/learning/learning-result.vue',
  '../../pages/teacher/case-edit/case-edit.vue',
  '../../pages/teacher/problem-detail/problem-detail.vue',
  '../../pages/teacher/analytics/index.vue',
  '../../pages/teacher/insights/student-detail.vue',
  '../../pages/teacher/medical-review/review-list.vue',
  '../../pages/teacher/medical-review/review-detail.vue',
  '../../pages/teacher/question-bank/index.vue',
  '../../pages/teacher/question-bank/detail.vue',
  '../../pages/teacher/classes/classes.vue',
  '../../pages/teacher/pbl-diagnostic-detail/pbl-diagnostic-detail.vue',
  '../../pages/teacher/pbl-progress/pbl-progress.vue',
  '../../pages/teacher/learning/final-test.vue',
  '../../pages/teacher/insights/result.vue',
  '../../pages/teacher/learning/result.vue',
  '../../pages/teacher/analytics/student-detail.vue',
]

describe('page navigation boundaries', () => {
  it('treats retired content addresses as role-guarded redirects', async () => {
    for (const path of [
      '../../pages/teacher/problem-edit/problem-edit.vue',
      '../../pages/teacher/knowledge-cards/knowledge-cards.vue',
    ]) {
      const source = await pageSource(path)
      expect(source).toContain("requireRole('teacher')")
      expect(source).toContain("relaunchToTeacherWorkspace({ workspace: 'content', resource: 'cases' })")
    }
    const source = await pageSource('../../pages/student/question-detail/question-detail.vue')
    expect(source).toContain("requireRole('student')")
    expect(source).toContain("goReplace(ROUTES.studentCases, { view: 'cases' })")
  })

  it('gives every secondary page an explicit native-back fallback', async () => {
    for (const relativePath of secondaryPages) {
      const source = await pageSource(relativePath)
      expect(source, relativePath).toContain('onBackPress')
      expect(source, relativePath).toMatch(/handleBackPress|backFromTeacherDetail/)
    }
  })

  it('keeps page-level transitions behind the shared navigation helpers', async () => {
    const sourceEntries = await Promise.all(
      secondaryPages.map(async (relativePath) => [relativePath, await pageSource(relativePath)]),
    )
    for (const [relativePath, source] of sourceEntries) {
      expect(source, relativePath).not.toMatch(/\buni\.(?:navigateTo|navigateBack|redirectTo|reLaunch|switchTab)\s*\(/)
      expect(source, relativePath).not.toMatch(/(?:goDetail|goReplace|relaunchTo)\(\s*['"]\/pages\//)
    }
  })

  it('keeps teacher detail fallbacks aligned with the owning workspaces', async () => {
    for (const relativePath of [
      '../../pages/teacher/insights/student-detail.vue',
      '../../pages/teacher/problem-detail/problem-detail.vue',
      '../../pages/teacher/case-edit/case-edit.vue',
    ]) {
      const source = await pageSource(relativePath)
      expect(source, relativePath).toContain(
        relativePath.includes('/insights/') ? "workspace: 'insights'" : 'ROUTES.teacherContent',
      )
    }
  })

  it('restores completed-classroom student learning under analytics', async () => {
    const legacyStudentPage = await pageSource('../../pages/teacher/insights/student-detail.vue')
    expect(legacyStudentPage).toContain("workspace: 'insights'")
    expect(legacyStudentPage).toContain("panel: 'students'")
    expect(legacyStudentPage).toContain('getTeacherInsightsStudent')
    expect(legacyStudentPage).not.toContain('学生档案')
  })

  it('keeps the legacy classroom progress address as a thin Insights redirect', async () => {
    const source = await pageSource('../../pages/teacher/pbl-progress/pbl-progress.vue')
    expect(source).toContain('relaunchToTeacherWorkspace')
    expect(source).toContain("tab: 'insights', panel: 'progress'")
    expect(source).not.toContain('getClassroomTaskProgressItems')
    expect(source).not.toContain('finalReportId')
    expect(source).not.toContain('teacherPblFollowUpDetail')
    expect(source).not.toContain('getClassroomReportStudent')
  })

  it('keeps historical student and result details as role-guarded redirects without data readers', async () => {
    for (const path of [
      '../../pages/teacher/learning/result.vue',
      '../../pages/teacher/analytics/student-detail.vue',
    ]) {
      const source = await pageSource(path)
      expect(source).toContain("requireRole('teacher')")
      expect(source).toContain('redirectLegacyTeacherInsightsDetail')
      expect(source).not.toContain('getTeacherRouteResult')
      expect(source).not.toContain('getTeacherInsightsStudent')
    }
  })
})
