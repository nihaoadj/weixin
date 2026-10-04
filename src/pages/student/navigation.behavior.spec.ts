import { readFile } from 'node:fs/promises'
import { describe, expect, it } from 'vitest'

const pageSource = (relativePath: string) => readFile(new URL(relativePath, import.meta.url), 'utf8')

describe('student page navigation contracts', () => {
  it('registers native-back fallbacks for every student secondary page', async () => {
    const expectedFallbacks = [
      ['./question/question.vue', 'studentLearning'],
      ['./case-training/case-training.vue', 'studentCases'],
      ['./case-report/case-report.vue', 'studentCases'],
      ['./learning/knowledge-node.vue', 'studentCases'],
      ['./learning/source-view.vue', 'studentKnowledgeNode'],
      ['./learning/plans.vue', 'studentLearning'],
      ['./learning/plan-detail.vue', 'studentLearningPlans'],
      ['./learning/route-reading.vue', 'studentLearningPlanDetail'],
      ['./learning/route-case.vue', 'studentLearningPlanDetail'],
      ['./learning/final-test.vue', 'studentLearningPlanDetail'],
      ['./learning/learning-result.vue', 'studentLearningPlanDetail'],
    ]

    for (const [relativePath, fallback] of expectedFallbacks) {
      const source = await pageSource(relativePath)
      expect(source).toContain('onBackPress')
      expect(source).toContain('handleBackPress')
      expect(source).toContain(fallback)
    }

    const reportSource = await pageSource('../report/report.vue')
    expect(reportSource).toContain('onBackPress')
    expect(reportSource).toContain('handleBackPress')
    expect(reportSource).toContain('ROUTES.studentChat')
  })

  it('treats training resources as a learning detail with two current URL-addressable views', async () => {
    const [learning, resources] = await Promise.all([
      pageSource('./learning/index.vue'),
      pageSource('./question/question.vue'),
    ])

    expect(learning).toContain('goDetail(ROUTES.studentCases')
    expect(resources).toContain("type ResourceView = 'cases' | 'knowledge'")
    expect(resources).toContain('<StudentPrimaryNav active="learning" />')
    expect(resources).toContain('handleBackPress(from, ROUTES.studentLearning)')
  })

  it('keeps case report return actions and T44 route steps tied to their route identity', async () => {
    const [caseTraining, caseReport, planDetail] = await Promise.all([
      pageSource('./case-training/case-training.vue'),
      pageSource('./case-report/case-report.vue'),
      pageSource('./learning/plan-detail.vue'),
    ])

    expect(caseTraining).toContain('goReplace(ROUTES.studentCaseReport')
    expect(caseReport).toContain('goReplace(ROUTES.studentCaseTraining')
    expect(planDetail).toContain("step.kind === 'reading' ? ROUTES.studentRouteReading : ROUTES.studentRouteCase")
    expect(planDetail).toContain("step.kind === 'reading' ? { routeId, stepId: step.id }")
    expect(planDetail).toContain('goDetail(ROUTES.studentFinalTest, { routeId, testId: detail.value.testSummary.id })')
    expect(planDetail).toContain('goDetail(ROUTES.studentLearningResult, { routeId })')
  })

  it('keeps old chat as read-only history and routes continuation into the unified dialogue', async () => {
    const [chat, history] = await Promise.all([pageSource('./chat/chat.vue'), pageSource('./history/history.vue')])

    expect(chat).toContain('ROUTES.studentPbl')
    expect(chat).not.toContain('ROUTES.studentReport')
    expect(history).toContain('ROUTES.studentReport')
    expect(chat).not.toContain("'/pages/report/report'")
    expect(history).not.toContain("'/pages/report/report'")
  })

  it('opens current learning plans by route identity from the learning home', async () => {
    const learning = await pageSource('./learning/index.vue')
    expect(learning).toContain("getLearningRoutes('active', 4, 0)")
    expect(learning).toContain('goDetail(ROUTES.studentLearningPlans)')
    expect(learning).toContain('goDetail(ROUTES.studentLearningPlanDetail, { routeId: id })')
    expect(learning).not.toContain('studentClassroomPackage')
    expect(learning).not.toContain('legacy-plan:')
  })
})
