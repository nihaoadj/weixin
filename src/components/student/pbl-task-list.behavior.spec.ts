import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const dependencies = vi.hoisted(() => ({
  createPblMessageId: vi.fn(() => 'submission-1'),
  getPblLearningPlans: vi.fn(),
  startLearningTask: vi.fn(),
  submitPblTask: vi.fn(),
}))

vi.mock('@/features/pbl/public', () => ({
  createPblMessageId: dependencies.createPblMessageId,
  getPblLearningPlans: dependencies.getPblLearningPlans,
  submitPblTask: dependencies.submitPblTask,
}))
vi.mock('@/features/learning/public', () => ({ startLearningTask: dependencies.startLearningTask }))
vi.mock('@/platform/navigation', () => ({
  ROUTES: { studentCaseTraining: '/student/case-training' },
  goDetail: vi.fn(),
}))

import PblTaskList from './PblTaskList.vue'

describe('PblTaskList', () => {
  beforeEach(() => {
    dependencies.getPblLearningPlans.mockResolvedValue([
      {
        id: 1,
        source_context: { class_name: '病理学一班', session_id: 2 },
        verification_status: 'not_ready',
        current_cycle: 1,
        max_cycles: 2,
        automation_exhausted: false,
        decision_policy_version: 'pbl-mastery-v1',
        due_at: '2026-09-14T00:00:00Z',
        tasks: [
          {
            id: 11,
            position: 1,
            task_type: 'knowledge_review',
            status: 'pending',
            problem_id: null,
            cycle_number: 1,
            target_type: 'knowledge_gap',
            target_code: 'pathology.inflammation.vascular',
            variant_code: 'vascular.practice.v1',
            public_definition: {
              prompt: '比较血流增加与渗出。',
              target_label: '炎症的血管反应',
              reference: '校内教研组审核材料',
              options: ['比较证据', '只记结论'],
            },
            result: null,
          },
          {
            id: 12,
            position: 2,
            task_type: 'micro_drill',
            status: 'pending',
            problem_id: null,
            cycle_number: 1,
            target_type: 'reasoning_issue',
            target_code: 'evidence_reasoning',
            variant_code: 'evidence.v1',
            public_definition: { prompt: '补充反对证据。' },
            result: null,
          },
        ],
      },
    ])
  })

  it('shows public learning targets and makes absent sources explicit without exposing private task data', async () => {
    const wrapper = mount(PblTaskList, { global: { stubs: { radio: true, 'radio-group': true } } })
    await flushPromises()

    expect(wrapper.text()).toContain('学习目标：炎症的血管反应')
    expect(wrapper.text()).toContain('资料来源：校内教研组审核材料')
    expect(wrapper.text()).toContain('资料来源：教师采用的 PBL 训练，未提供单独资料来源。')
    expect(wrapper.text()).not.toContain('private_rubric')
  })
})
