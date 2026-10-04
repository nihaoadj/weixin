import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import LearningRecordSectionHeading from '../../../components/student/LearningRecordSectionHeading.vue'
import PblTargetComparison from './PblTargetComparison.vue'

describe('PBL report visualizations', () => {
  it('renders the learning-record section hierarchy with the blue-cyan accent', () => {
    const wrapper = mount(LearningRecordSectionHeading, {
      props: { title: '目标改善轨迹', note: '逐项目标对照分数、要求和证据。' },
    })

    expect(wrapper.find('.section-title').text()).toBe('目标改善轨迹')
    expect(wrapper.find('.section-note').text()).toContain('逐项目标')
    expect(wrapper.find('.title-accent').exists()).toBe(true)
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
