import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import PblRecurringTargets from './PblRecurringTargets.vue'
import PblStatusDistribution from './PblStatusDistribution.vue'
import PblTargetComparison from './PblTargetComparison.vue'

describe('PBL report visualizations', () => {
  it('exposes every status count as text and as a chart description', () => {
    const wrapper = mount(PblStatusDistribution, {
      props: {
        counts: {
          discussing: 1,
          awaiting_learning: 2,
          learning_cycle_1: 3,
          learning_cycle_2: 4,
          improved: 5,
          support_needed: 6,
        },
      },
    })
    expect(wrapper.find('[role="img"]').attributes('aria-label')).toContain('已改善 5 次')
    expect(wrapper.text()).toContain('需支持6')
  })

  it('keeps recurring frequency readable without relying on bar color', () => {
    const wrapper = mount(PblRecurringTargets, {
      props: {
        items: [
          {
            targetType: 'knowledge_gap',
            targetCode: 'vascular_response',
            label: '炎症的血管反应',
            occurrences: 3,
          },
        ],
        completedDiscussions: 4,
      },
    })
    expect(wrapper.find('[role="listitem"]').attributes('aria-label')).toBe(
      '炎症的血管反应，在 4 次完成讨论中出现 3 次',
    )
    expect(wrapper.text()).toContain('3 / 4 次完成讨论')
    expect(wrapper.find('.track-fill').attributes('style')).toContain('75%')
  })

  it('states score, threshold and pass result for each target cycle', () => {
    const wrapper = mount(PblTargetComparison, {
      props: {
        targets: [
          {
            planId: 3,
            targetType: 'reasoning_issue',
            targetCode: 'evidence_reasoning',
            label: '证据推理',
            cycles: [
              {
                cycleNumber: 1,
                target_type: 'reasoning_issue',
                target_code: 'evidence_reasoning',
                label: '证据推理',
                threshold: 70,
                score: 62,
                evidence_present: true,
                passed: false,
              },
            ],
          },
        ],
      },
    })
    expect(wrapper.find('.cycle').attributes('aria-label')).toBe('第 1 轮，成绩 62，要求 70，未达标')
    expect(wrapper.text()).toContain('要求 70')
    expect(wrapper.text()).toContain('未达标')
  })
})
