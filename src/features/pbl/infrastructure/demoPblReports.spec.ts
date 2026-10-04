import { describe, expect, it } from 'vitest'

import type { PblLearningReport } from '../domain/ports'
import { demoReportPage } from './demoPblReports'

const report = (
  id: string,
  createdAt: string | undefined,
  knowledgeGaps: PblLearningReport['diagnosis']['knowledgeGaps'],
  reasoningIssues: PblLearningReport['diagnosis']['reasoningIssues'],
): PblLearningReport => ({
  session: {
    id,
    topicCode: 'pathology.inflammation',
    topicLabel: '炎症',
    caseTitle: `研讨 ${id}`,
    status: 'active',
    createdAt: '2026-09-07T08:00:00Z',
  },
  status: 'improved',
  visibility: 'private',
  phaseProgress: [],
  diagnosis: { createdAt, knowledgeGaps, reasoningIssues },
  plans: [],
  targetProgress: [],
  taskProgress: { completed: 0, total: 0 },
  summaryText: '已完成。',
  nextAction: { kind: 'none', label: '已完成' },
  teacherFeedbacks: [],
  timeline: [],
  updatedAt: `2026-09-07T08:0${id}:00Z`,
})

describe('demo PBL report aggregation', () => {
  it('matches API semantics for v4-style personal findings, denominator, and per-report target de-duplication', () => {
    const knowledge = {
      id: 'gap',
      pointCode: 'pathology.inflammation.vascular',
      label: '炎症的血管反应',
      summary: '需要巩固',
      confidence: 'high',
      evidenceSummary: '讨论证据',
    }
    const reasoning = {
      id: 'reason',
      dimensionId: 'evidence_reasoning',
      label: '证据推理',
      summary: '需要补充反证',
      issueType: 'missing_evidence',
      improvement: '说明反对证据',
      evidenceSummary: '讨论证据',
    }
    const page = demoReportPage(
      [
        report('1', '2026-09-07T09:00:00Z', [knowledge, { ...knowledge, id: 'gap-duplicate' }], [reasoning]),
        report('2', '2026-09-07T10:00:00Z', [knowledge], [reasoning]),
        report('3', undefined, [], []),
      ],
      20,
      0,
    )

    expect(page.summary.totalReports).toBe(3)
    expect(page.summary.completedPersonalDiscussions).toBe(2)
    expect(page.summary.dashboard).toMatchObject({
      dataBasis: 'synthetic_demo',
      masteryScore: 78,
      studyMinutes: 750,
      planCompletionRate: 87,
      masteredKnowledgeCount: 56,
      aiDiagnosticCount: 8,
    })
    expect(page.summary.dashboard.trend.at(-1)?.score).toBe(78)
    expect(page.summary.dashboard.trend).toHaveLength(4)
    expect(page.summary.dashboard.weaknesses.map((item) => item.label)).toEqual(['呼吸系统', '药理学', '诊断学'])
    expect(page.summary.recurringTargets).toEqual([
      {
        targetType: 'knowledge_gap',
        targetCode: 'pathology.inflammation.vascular',
        label: '炎症的血管反应',
        occurrences: 2,
      },
      {
        targetType: 'reasoning_issue',
        targetCode: 'evidence_reasoning',
        label: '证据推理',
        occurrences: 2,
      },
    ])
  })
})
