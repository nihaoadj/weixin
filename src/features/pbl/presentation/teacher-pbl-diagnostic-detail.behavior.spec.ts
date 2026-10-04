import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import TeacherPblWorkItemDetail from './TeacherPblWorkItemDetail.vue'
import type { PblDiagnostic, PblSuggestion, PblWorkItem } from '@/features/pbl/public'

const suggestion = (overrides: Partial<PblSuggestion>): PblSuggestion => ({
  id: 's1',
  title: '说明炎症中血管反应与渗出的关系',
  prompt: '请分别说明血流变化和血管通透性增加如何共同造成局部红肿与渗出。',
  linkedFindings: ['f1'],
  status: 'pending_review',
  version: 2,
  ...overrides,
})

const diagnostic: PblDiagnostic = {
  diagnosticStatus: 'completed',
  assistantReply: 'Demo 合成追问记录。',
  studentName: '演示学生·林晓',
  className: '病理学演示班',
  topicCode: 'pathology.inflammation',
  phaseEvidenceSummary: '学生已经完成综合解释，但血管反应与渗出机制的证据链仍需教师带教。',
  knowledgeGaps: [
    {
      id: 'g1',
      summary: '能描述局部红肿，但尚未把血管通透性增加与渗出形成明确连接。',
      evidence_message_ids: [],
      evidence_summary: '',
      point_code: 'pathology.inflammation.vascular',
      confidence: 'medium',
    },
    {
      id: 'g2',
      summary: '混淆血流增加与通透性增加的表现。',
      evidence_message_ids: [],
      evidence_summary: '',
      point_code: 'pathology.inflammation.vascular',
      confidence: 'low',
    },
  ],
  reasoningIssues: [
    {
      id: 'r1',
      summary: '观察到的表现与病理机制之间缺少逐项证据连接。',
      evidence_message_ids: [],
      evidence_summary: '',
      dimension_id: 'evidence_reasoning',
      issue_type: 'evidence_link',
      improvement: '先分别列出血流、通透性与渗出，再说明每一项如何支持解释。',
    },
  ],
  recommendedQuestions: [suggestion({}), suggestion({ id: 's2', title: '比较两种血管反应的解释' })],
}

const selected: PblWorkItem = {
  snapshotId: '90002',
  sessionId: 'demo-pbl-1',
  source: 'classroom_diagnostic',
  status: 'pending',
  student: { id: '3', name: '演示学生·林晓' },
  class: { id: '1', name: '病理学演示班' },
  topic: 'pathology.inflammation',
  knowledgeGapCount: 2,
  reasoningIssueCount: 1,
  nextAction: '审阅并反馈',
}

const props = { selected, loading: false, error: '' }

function mountDetail(overrides: Record<string, unknown> = {}) {
  return mount(TeacherPblWorkItemDetail, {
    props: { ...props, detail: { diagnostic, feedbacks: [] }, ...overrides },
    global: {
      stubs: {
        MedIcon: true,
        checkbox: true,
        picker: {
          template: `<div class="picker-stub" @click="$emit('change', { detail: { value: 1 } })"><slot /></div>`,
        },
      },
    },
  })
}

describe('teacher PBL diagnostic detail', () => {
  it('renders the student name as the object title with class, topic and a status tag', () => {
    const wrapper = mountDetail()
    expect(wrapper.get('.object-title').text()).toBe('演示学生·林晓')
    expect(wrapper.get('.object-meta').text()).toBe('病理学演示班 · 炎症')
    expect(wrapper.get('.tst').text()).toBe('研讨分析 · 只读')
    expect(wrapper.get('.tst').classes()).toContain('tst--neutral')
    expect(wrapper.get('.tst').text()).not.toContain('待处理')
    expect(wrapper.text()).not.toContain('pathology')
  })

  it('keeps student evidence neutral in one module', () => {
    const wrapper = mountDetail()
    const evidence = wrapper.findAll('.tms')[0]
    expect(evidence.get('.tms__title').text()).toBe('研讨证据摘要')
    expect(evidence.get('.evidence-trajectory').text()).toContain('研讨完成')
    expect(evidence.get('.evidence-summary').text()).toContain('证据链仍需教师带教')
    expect(evidence.classes()).not.toContain('tms--editor')
  })

  it('renders findings as numbered record rows with dividers and neutral empty states', async () => {
    const wrapper = mountDetail()
    const findingModules = wrapper
      .findAll('.tms')
      .filter((module) => ['知识薄弱点', '推理问题'].includes(module.get('.tms__title').text()))
    const gapRows = findingModules[0].findAll('.finding-row')
    expect(gapRows).toHaveLength(2)
    expect(gapRows[0].get('.finding-index').text()).toBe('01')
    expect(gapRows[1].get('.finding-index').text()).toBe('02')
    expect(findingModules[1].findAll('.finding-row')).toHaveLength(1)
    expect(findingModules[1].get('.finding-improvement').text()).toContain('建议：先分别列出血流、通透性与渗出')
    const empty = mountDetail({
      detail: { diagnostic: { ...diagnostic, knowledgeGaps: [], reasoningIssues: [] }, feedbacks: [] },
    })
    expect(empty.text()).toContain('未识别到知识薄弱点')
    expect(empty.text()).toContain('不代表学生已掌握')
  })

  it('never exposes retired suggestion or feedback actions, including historical suggested questions', () => {
    const wrapper = mountDetail()
    expect(wrapper.find('textarea').exists()).toBe(false)
    expect(wrapper.find('input').exists()).toBe(false)
    expect(wrapper.find('.tms--editor').exists()).toBe(false)
    expect(wrapper.text()).not.toContain('反馈并发布任务')
    expect(wrapper.text()).not.toContain('AI 建议 · 待教师确认')
    expect(wrapper.text()).not.toContain(diagnostic.recommendedQuestions![0].title)
    expect(wrapper.text()).not.toContain('旧版诊断')
    expect(wrapper.text()).not.toContain('历史任务')
    expect(wrapper.get('.evidence-trajectory').text()).toContain('固定诊断 → 学习路线与最终测试')
  })

  it('preserves historical teacher feedback without enabling disposition for closed records', () => {
    const wrapper = mountDetail({
      selected: { ...selected, status: 'closed' },
      detail: {
        diagnostic,
        feedbacks: [{ id: 'f1', body: '历史形成性反馈', createdAt: '2026-09-20T02:00:00Z' }],
      },
    })
    expect(wrapper.get('.tst').text()).toBe('研讨分析 · 只读')
    expect(wrapper.get('.feedback-body').text()).toBe('历史形成性反馈')
    expect(wrapper.find('textarea').exists()).toBe(false)
    expect(wrapper.find('.feedback-time').exists()).toBe(true)
  })

  it('retains retry and loading states for failed diagnostic reads', async () => {
    const wrapper = mountDetail({ error: '诊断读取失败' })
    expect(wrapper.text()).toContain('诊断读取失败')
    const retry = wrapper.findAll('button').find((button) => button.text() === '重新加载')!
    await retry.trigger('click')
    expect(wrapper.emitted('retry')).toEqual([[]])
    await wrapper.setProps({ error: '', loading: true })
    expect(wrapper.text()).toContain('正在加载诊断详情')
    expect(wrapper.find('.object-title').exists()).toBe(false)
  })
})
