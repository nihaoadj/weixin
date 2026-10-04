import { describe, expect, it } from 'vitest'
import { DemoStudentLearningInsightsRepository } from './demoStudentLearningInsights'

const gap = (knowledgeGapCodes: string[], reasoningIssueCodes: string[] = []) => ({
  knowledgeGapCodes,
  reasoningIssueCodes,
})
const dialogue = (
  sessionId: string,
  updatedAt: string,
  diagnosis?: ReturnType<typeof gap>,
  diagnosisCreatedAt?: string,
) => ({
  sessionId,
  topicCode: 'pathology.inflammation',
  caseTitle: '合成病例',
  createdAt: '2026-09-20T00:00:00Z',
  updatedAt,
  diagnosisCreatedAt,
  diagnosis,
})
const route = (
  id: string,
  sessionLocator: string,
  accumulatedReadingSeconds: number,
  result?: {
    score: number
    submittedAt: string
    goalPointCodes: string[]
    questions: Array<{ pointCode: string; earned: number; possible: number }>
  },
) => ({
  id,
  sessionLocator,
  title: `${id} 学习路线`,
  goalPointCodes: result?.goalPointCodes || ['pathology.inflammation.acute'],
  status: result ? 'completed' : 'learning',
  progressLabel: result ? '最终测试已完成' : '正在阅读',
  completedSteps: result ? 2 : 0,
  totalSteps: 2,
  updatedAt: result?.submittedAt || '2026-09-28T00:00:00Z',
  accumulatedReadingSeconds,
  result,
})

describe('Demo student learning insights', () => {
  it('renders every reasoning dimension with its readable label and no invented score', async () => {
    const labels = {
      information_gathering: '信息搜集',
      problem_representation: '问题表征',
      differential_diagnosis: '鉴别诊断',
      evidence_reasoning: '证据推理',
      test_selection: '检查选择',
      management_safety: '处置安全',
    }
    const repository = new DemoStudentLearningInsightsRepository({
      readDialogues: async () => [dialogue('reasoning', '2026-09-30T00:00:00Z', gap([], Object.keys(labels)))],
      readRoutes: async () => [],
      readKnowledgeCatalog: async () => [],
      now: () => new Date('2026-09-30T00:00:00Z'),
    })
    const page = await repository.getStudentLearningInsights()
    expect(page.summary.dashboard.weaknesses).toHaveLength(6)
    for (const item of page.summary.dashboard.weaknesses) {
      expect(item.label).toBe(labels[item.targetCode as keyof typeof labels])
      expect(item.masteryPercentage).toBeNull()
    }
  })
  it('aggregates current routes, Shanghai weeks, real zero scores and newer diagnosis evidence', async () => {
    const reader = {
      readDialogues: async () => [
        dialogue(
          'pbl-1',
          '2026-09-27T16:30:00Z',
          gap(['pathology.inflammation.acute', 'pathology.inflammation.vascular'], ['evidence_reasoning']),
          '2026-09-23T00:00:00Z',
        ),
        dialogue('pbl-2', '2026-09-29T15:00:00Z', gap(['pathology.inflammation.acute']), '2026-09-29T15:00:00Z'),
      ],
      readRoutes: async () => [
        route('route-full', 'pbl-1', 30, {
          score: 100,
          submittedAt: '2026-09-27T16:30:00Z',
          goalPointCodes: ['pathology.inflammation.acute'],
          questions: [{ pointCode: 'pathology.inflammation.acute', earned: 10, possible: 10 }],
        }),
        route('route-partial', 'pbl-1', 60, {
          score: 75,
          submittedAt: '2026-09-24T04:00:00Z',
          goalPointCodes: ['pathology.inflammation.vascular'],
          questions: [{ pointCode: 'pathology.inflammation.vascular', earned: 15, possible: 20 }],
        }),
        route('route-zero', 'pbl-1', 35, {
          score: 0,
          submittedAt: '2026-09-29T03:00:00Z',
          goalPointCodes: ['pathology.inflammation.unreported'],
          questions: [{ pointCode: 'pathology.inflammation.unreported', earned: 0, possible: 10 }],
        }),
        route('route-active', 'pbl-2', 0),
        { ...route('route-progressed', 'pbl-1', 0), updatedAt: '2026-09-30T00:00:00Z', completedSteps: 1 },
      ],
      readKnowledgeCatalog: async () => [
        {
          code: 'pathology.inflammation.acute',
          title: '急性炎症',
          systemCode: 'pathology.inflammation',
          systemLabel: '炎症',
        },
        {
          code: 'pathology.inflammation.vascular',
          title: '炎症的血管反应',
          systemCode: 'pathology.inflammation',
          systemLabel: '炎症',
        },
        {
          code: 'pathology.inflammation.unreported',
          title: '未诊断目标',
          systemCode: 'pathology.inflammation',
          systemLabel: '炎症',
        },
      ],
      now: () => new Date('2026-09-30T04:00:00Z'),
    }
    const repository = new DemoStudentLearningInsightsRepository(reader)

    const page = await repository.getStudentLearningInsights(1, 1)
    const dashboard = page.summary.dashboard
    expect(page).toMatchObject({ limit: 1, offset: 1, total: 2 })
    expect(page.items).toHaveLength(1)
    expect(dashboard).toMatchObject({
      dataBasis: 'synthetic_demo',
      periodStart: '2026-09-28',
      periodEnd: '2026-10-04',
      masteryScore: 50,
      masteryDelta: -25,
      masterySampleCount: 2,
      studyMinutes: 2,
      studyDurationBasis: 'recorded_reading',
      planCompletionRate: 60,
      testedKnowledgeCount: 3,
      aiDiagnosticCount: 2,
      statusLabel: '较上周回落',
    })
    expect(dashboard.trend.find((item) => item.periodStart === '2026-09-21')).toMatchObject({
      score: 75,
      sampleCount: 1,
    })
    expect(dashboard.weaknesses).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          targetType: 'knowledge',
          targetCode: 'pathology.inflammation.acute',
          occurrences: 2,
          masteryPercentage: null,
        }),
        expect.objectContaining({
          targetType: 'knowledge',
          targetCode: 'pathology.inflammation.vascular',
          masteryPercentage: 75,
        }),
        expect.objectContaining({
          targetType: 'knowledge',
          targetCode: 'pathology.inflammation.unreported',
          occurrences: 1,
          masteryPercentage: 0,
        }),
        expect.objectContaining({ targetType: 'reasoning', targetCode: 'evidence_reasoning', masteryPercentage: null }),
      ]),
    )
    expect(dashboard.aiSummary).toContain('关联学习路线已完成 0/2 步')
    expect(page.items[0].session.topicLabel).toBe('炎症')
  })

  it('re-reads sources on each page request and keeps summary independent of pagination', async () => {
    const dialogues = [dialogue('pbl-1', '2026-09-28T08:00:00Z', gap(['point-a']))]
    const reader = {
      readDialogues: async () => dialogues,
      readRoutes: async () => [route('route-1', 'pbl-1', 75)],
      readKnowledgeCatalog: async () => [],
      now: () => new Date('2026-09-30T04:00:00Z'),
    }
    const repository = new DemoStudentLearningInsightsRepository(reader)
    const first = await repository.getStudentLearningInsights(1, 0)
    dialogues.push(dialogue('pbl-2', '2026-09-29T08:00:00Z'))
    const second = await repository.getStudentLearningInsights(1, 0)

    expect(first.total).toBe(1)
    expect(second.total).toBe(2)
    expect(second.summary.dashboard.aiDiagnosticCount).toBe(1)
    expect(second.items).toHaveLength(1)
    expect(second.items[0].action.kind).toBe('discussion')
  })

  it('keeps unlinked routes as safe recent records without duplicating dialogue-linked routes', async () => {
    const reader = {
      readDialogues: async () => [
        dialogue('history-1', '2026-09-20T08:00:00Z'),
        dialogue('history-2', '2026-09-21T08:00:00Z'),
      ],
      readRoutes: async () => [
        route('linked-route', 'history-1', 60),
        { ...route('seeded-active-route', 'seeded-pbl-id', 120), updatedAt: '2026-09-30T01:00:00Z' },
        route('seeded-result-route', 'another-seeded-pbl-id', 240, {
          score: 75,
          submittedAt: '2026-09-29T12:00:00Z',
          goalPointCodes: ['pathology.inflammation.acute'],
          questions: [{ pointCode: 'pathology.inflammation.acute', earned: 3, possible: 4 }],
        }),
      ],
      readKnowledgeCatalog: async () => [
        {
          code: 'pathology.inflammation.acute',
          title: '急性炎症',
          systemCode: 'pathology.inflammation',
          systemLabel: '炎症',
        },
      ],
      now: () => new Date('2026-09-30T04:00:00Z'),
    }
    const page = await new DemoStudentLearningInsightsRepository(reader).getStudentLearningInsights()
    const itemById = new Map(page.items.map((item) => [item.id, item]))

    expect(page.total).toBe(4)
    expect(itemById.has('history-1')).toBe(true)
    expect(itemById.has('history-2')).toBe(true)
    expect(itemById.has('route:linked-route')).toBe(false)
    expect(itemById.get('route:seeded-active-route')).toMatchObject({
      summaryText: '学习路线已完成 0/2 步；正在阅读。',
      session: {
        id: 'seeded-pbl-id',
        topicLabel: '炎症',
        caseTitle: 'seeded-active-route 学习路线',
      },
      action: { kind: 'route', sessionId: 'seeded-pbl-id', routeId: 'seeded-active-route' },
    })
    expect(itemById.get('route:seeded-result-route')).toMatchObject({
      action: { kind: 'result', sessionId: 'another-seeded-pbl-id', routeId: 'seeded-result-route' },
    })
    expect(page.summary.nextAction).toMatchObject({
      kind: 'route',
      sessionId: 'seeded-pbl-id',
      routeId: 'seeded-active-route',
    })
    expect(page.summary.dashboard.aiSummary).toContain('最近路线已完成 0/2 步')
    expect(page.summary.dashboard.aiSummary).toContain('最近一次最终测试得分 75 分')
    expect(page.summary.dashboard.aiSummary).not.toContain('完成研讨后会纳入')
  })
})
