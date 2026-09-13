import { readFile } from 'node:fs/promises'
import { describe, expect, it } from 'vitest'

const pageSource = (relativePath: string) => readFile(new URL(relativePath, import.meta.url), 'utf8')

describe('student page navigation contracts', () => {
  it('registers native-back fallbacks for every student secondary page', async () => {
    const expectedFallbacks = [
      ['./question-detail/question-detail.vue', 'studentCases'],
      ['./question/question.vue', 'studentLearning'],
      ['./case-training/case-training.vue', 'studentCases'],
      ['./case-report/case-report.vue', 'studentCases'],
      ['./learning/plan.vue', 'studentLearning'],
      ['./learning/drill.vue', 'backTarget'],
      ['./learning/review.vue', 'studentLearning'],
      ['./learning/knowledge-node.vue', 'studentCases'],
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

  it('treats training resources as a learning detail with three URL-addressable views', async () => {
    const [learning, resources] = await Promise.all([
      pageSource('./learning/index.vue'),
      pageSource('./question/question.vue'),
    ])

    expect(learning).toContain('goDetail(ROUTES.studentCases')
    expect(resources).toContain("type ResourceView = 'cases' | 'knowledge' | 'questions'")
    expect(resources).toContain('<StudentPrimaryNav active="learning" />')
    expect(resources).toContain('handleBackPress(from, ROUTES.studentLearning)')
  })

  it('keeps completed-case replacements while preserving the micro-drill return route', async () => {
    const [caseTraining, caseReport, plan] = await Promise.all([
      pageSource('./case-training/case-training.vue'),
      pageSource('./case-report/case-report.vue'),
      pageSource('./learning/plan.vue'),
    ])

    expect(caseTraining).toContain('goReplace(ROUTES.studentCaseReport')
    expect(caseReport).toContain('goReplace(ROUTES.studentCaseTraining')
    expect(plan).toContain('goReplace(ROUTES.studentCaseTraining')
    expect(plan).toContain('goDetail(ROUTES.studentLearningDrill')
    expect(plan).toContain('planId,')
  })

  it('keeps old chat as read-only history and routes continuation into the unified dialogue', async () => {
    const [chat, history] = await Promise.all([pageSource('./chat/chat.vue'), pageSource('./history/history.vue')])

    expect(chat).toContain('ROUTES.studentPbl')
    expect(chat).not.toContain('ROUTES.studentReport')
    expect(history).toContain('ROUTES.studentReport')
    expect(chat).not.toContain("'/pages/report/report'")
    expect(history).not.toContain("'/pages/report/report'")
  })

  it('opens a teacher PBL-feedback notification at its submitted dialogue', async () => {
    const learning = await pageSource('./learning/index.vue')
    expect(learning).toContain("item.entityType === 'pbl_session'")
    expect(learning).toContain('relaunchTo(ROUTES.studentPbl, { dialogueId: item.entityId })')
  })
})
