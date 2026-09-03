import { readFile } from 'node:fs/promises'
import { describe, expect, it } from 'vitest'

const pageSource = (relativePath: string) => readFile(new URL(relativePath, import.meta.url), 'utf8')

const secondaryPages = [
  '../../pages/report/report.vue',
  '../../pages/student/case-report/case-report.vue',
  '../../pages/student/case-training/case-training.vue',
  '../../pages/student/question-detail/question-detail.vue',
  '../../pages/student/learning/plan.vue',
  '../../pages/student/learning/drill.vue',
  '../../pages/student/learning/review.vue',
  '../../pages/teacher/detail/detail.vue',
  '../../pages/teacher/problem-edit/problem-edit.vue',
  '../../pages/teacher/case-edit/case-edit.vue',
  '../../pages/teacher/problem-detail/problem-detail.vue',
  '../../pages/teacher/problem-stats/problem-stats.vue',
  '../../pages/teacher/analytics/index.vue',
  '../../pages/teacher/analytics/case-detail.vue',
  '../../pages/teacher/analytics/student-detail.vue',
  '../../pages/teacher/medical-review/review-list.vue',
  '../../pages/teacher/medical-review/review-detail.vue',
  '../../pages/teacher/classes/classes.vue',
]

describe('page navigation boundaries', () => {
  it('gives every secondary page an explicit native-back fallback', async () => {
    for (const relativePath of secondaryPages) {
      const source = await pageSource(relativePath)
      expect(source, relativePath).toContain('onBackPress')
      expect(source, relativePath).toContain('handleBackPress')
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
})
