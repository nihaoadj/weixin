import { describe, expect, it } from 'vitest'

import { mapLearningReport, mapReportPage, reportDetailSchema, reportPageSchema } from './reportContract'

const session = {
  id: 7,
  topic_code: 'pathology.inflammation',
  topic_label: '炎症',
  case_title: '急性炎症病例',
  status: 'closed',
  created_at: '2026-09-04T08:00:00Z',
  closed_at: '2026-09-04T09:00:00Z',
}

describe('PBL learning report contract', () => {
  it('maps snake-case overview data and fills missing status buckets with zero', () => {
    const parsed = reportPageSchema.parse({
      summary: {
        total_reports: 1,
        status_counts: { improved: 1 },
        recurring_targets: [
          {
            target_type: 'knowledge_gap',
            target_code: 'vascular_response',
            label: '炎症的血管反应',
            occurrences: 2,
          },
        ],
        next_action: null,
      },
      items: [
        {
          session,
          status: 'improved',
          current_phase: 'synthesis',
          phase_status: 'completed',
          knowledge_gap_count: 1,
          reasoning_issue_count: 1,
          task_progress: { completed: 3, total: 3 },
          summary_text: '本次必需目标已达标。',
          next_action: { kind: 'none', label: '本次学习已完成' },
          updated_at: '2026-09-04T10:00:00Z',
        },
      ],
      total: 1,
      limit: 20,
      offset: 0,
    })

    const page = mapReportPage(parsed)
    expect(page.items[0].session.id).toBe('7')
    expect(page.summary.statusCounts.improved).toBe(1)
    expect(page.summary.statusCounts.discussing).toBe(0)
  })

  it('maps an append-only two-cycle target trail without introducing a composite score', () => {
    const check = {
      target_type: 'knowledge_gap',
      target_code: 'vascular_response',
      label: '炎症的血管反应',
      threshold: 100,
      score: 100,
      evidence_present: true,
      passed: true,
    }
    const parsed = reportDetailSchema.parse({
      session,
      status: 'improved',
      current_phase: 'synthesis',
      phase_status: 'completed',
      phase_progress: [
        {
          phase: 'problem_framing',
          label: '明确问题',
          state: 'completed',
          evidence_summary: '已形成问题表征',
          missing_elements: [],
          evidenced_at: '2026-09-04T08:10:00Z',
        },
      ],
      diagnosis: { created_at: null, knowledge_gaps: [], reasoning_issues: [] },
      plans: [
        {
          id: 12,
          assignment_basis: 'personal',
          status: 'completed',
          verification_status: 'improved',
          current_cycle: 2,
          max_cycles: 2,
          automation_exhausted: false,
          decision_policy_version: 'pbl-mastery-v1',
          due_at: '2026-09-11T08:00:00Z',
          created_at: '2026-09-04T09:10:00Z',
          tasks: [],
          evaluations: [
            {
              cycle_number: 1,
              policy_version: 'pbl-mastery-v1',
              result: 'next_cycle_activated',
              checks: [{ ...check, score: 0, passed: false }],
              failed_targets: [{ target_type: check.target_type, target_code: check.target_code, label: check.label }],
              automation_exhausted: false,
              record_source: 'runtime',
              evaluated_at: '2026-09-04T10:00:00Z',
            },
            {
              cycle_number: 2,
              policy_version: 'pbl-mastery-v1',
              result: 'improved',
              checks: [check],
              failed_targets: [],
              automation_exhausted: false,
              record_source: 'runtime',
              evaluated_at: '2026-09-04T11:00:00Z',
            },
          ],
        },
      ],
      target_progress: [
        {
          plan_id: 12,
          target_type: check.target_type,
          target_code: check.target_code,
          label: check.label,
          cycles: [
            { cycle_number: 1, ...check, score: 0, passed: false },
            { cycle_number: 2, ...check },
          ],
        },
      ],
      task_progress: { completed: 4, total: 4 },
      summary_text: '两轮证据可追溯。',
      next_action: { kind: 'none', label: '本次学习已完成' },
      timeline: [
        {
          type: 'cycle_evaluated',
          label: '第二轮达标',
          cycle_number: 2,
          occurred_at: '2026-09-04T11:00:00Z',
        },
      ],
      updated_at: '2026-09-04T11:00:00Z',
    })

    const report = mapLearningReport(parsed)
    expect(report.plans[0].evaluations.map((item) => item.cycle_number)).toEqual([1, 2])
    expect(report.targetProgress[0].cycles.map((item) => item.score)).toEqual([0, 100])
    expect(report).not.toHaveProperty('score')
    expect(report).not.toHaveProperty('compositeScore')
  })
})
