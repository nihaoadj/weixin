import { describe, expect, it } from 'vitest'
import '@/platform/contracts/conformance'
import fixture from '@/test/fixtures/case-draft.json'
import {
  apiCaseDraftSchema,
  apiStageAnswerSchema,
  apiCaseAttemptSchema,
  apiCaseAssessmentSchema,
} from '@/platform/contracts/case'
import { toApiDefinition, toApiRubric, toCaseDraft, toAuthoring } from '@/features/content/infrastructure/mappers/case'
import {
  toApiAnswer,
  toCaseAssessment,
  toCaseAttempt,
  toStageAnswer,
} from '@/features/training/infrastructure/mappers/case'
import { toProblem } from '@/features/content/infrastructure/mappers/core'
import { toReport } from '@/features/reports/infrastructure/mappers/report'
import { toChatMessage } from '@/platform/mappers/messages'
import { apiReportSchema, apiProblemSchema } from '@/platform/contracts/core'
import {
  nullable,
  optional,
  toReportSummaryView,
  toConversationSummaryView,
  toQuestionView,
} from '@/shared/mappers/presentation'
import { now } from '@/test/http'

describe('explicit DTO mappings', () => {
  it('roundtrips a backend-generated case without recursively rewriting text or dictionary keys', () => {
    const input = apiCaseDraftSchema.parse(fixture)
    const draft = toCaseDraft(input)
    expect(toApiDefinition(draft.caseDefinition)).toEqual(input.case_definition)
    expect(toApiRubric(draft.rubric)).toEqual(input.rubric)
    expect(draft.caseDefinition.referenceReasoning.differentials?.[0].supportingFactIds).toEqual(
      input.case_definition.reference_reasoning.differentials[0].supporting_fact_ids,
    )
    expect(() =>
      apiCaseDraftSchema.parse({
        ...fixture,
        case_definition: { ...fixture.case_definition, reference_reasoning: {} },
      }),
    ).toThrow()
    const problem = apiProblemSchema.parse({
      id: 1,
      type: '病例分析',
      title: 'x',
      target: 'all',
      target_label: 'all',
      status: 'draft',
      created_at: now,
    })
    expect(() => toAuthoring(problem)).toThrow(expect.objectContaining({ code: 'CONTRACT_ERROR' }))
  })
  it.each([
    { stage_id: 'history', summary: 'literal_under_score', key_findings: ['a_b'] },
    { stage_id: 'problem_representation', summary: 'literal_under_score' },
    { stage_id: 'differential', items: [{ diagnosis: '肺炎', supporting_evidence: ['发热'], opposing_evidence: [] }] },
    { stage_id: 'tests', items: [{ test_name: '检查', rationale: '证据', priority: 'necessary' }] },
    { stage_id: 'management', items: [{ action: '处理', rationale: '原因' }], safety_considerations: ['安全'] },
  ])('maps each stage answer explicitly: $stage_id', (input) => {
    const dto = apiStageAnswerSchema.parse(input)
    expect(toApiAnswer(toStageAnswer(dto))).toEqual(dto)
  })
  it('maps detail IDs, inherited submissions and assessment comparisons', () => {
    const dto = apiCaseAttemptSchema.parse({
      id: 2,
      problem_id: 3,
      problem_version: 1,
      retry_of_id: 1,
      status: 'in_progress',
      current_stage: 'history',
      focus_stage: 'tests',
      started_at: now,
      opening: fixture.case_definition.opening,
      messages: [{ id: 4, role: 'assistant', content: 'hello', created_at: now }],
      submissions: [
        {
          id: 5,
          stage_id: 'history',
          answer: { stage_id: 'history', summary: 'hello' },
          feedback: 'ok',
          inherited_from_id: 6,
          created_at: now,
        },
      ],
    })
    expect(toCaseAttempt(dto)).toMatchObject({ id: '2', retryOfId: '1', submissions: [{ inheritedFromId: '6' }] })
    const assessment = apiCaseAssessmentSchema.parse({
      attempt_id: 2,
      total_score: 80,
      dimensions: [
        { dimension_id: 'tests', label: '检查', score: 80, weighted_score: 40, feedback: '反馈', next_step: '练习' },
      ],
      summary: '摘要',
      focus_stage: 'tests',
      model_name: 'fallback',
      prompt_version: 'v1',
      fallback_used: true,
      comparison: {
        total_delta: 10,
        dimensions: [{ dimension_id: 'tests', previous_score: 70, current_score: 80, delta: 10 }],
      },
    })
    expect(toCaseAssessment(assessment).comparison?.dimensions[0].currentScore).toBe(80)
  })
  it('maps report fields and legacy presentation without leaking DTOs', () => {
    const report = toReport(
      apiReportSchema.parse({
        id: 1,
        conversation_id: 2,
        student_id: 3,
        student_name: null,
        status: 'reviewed',
        report_kind: 'qa_learning_report',
        ai_score: 0,
        ai_summary: '',
        analysis: {
          errors: [{ content: '问题', suggestion: '改进' }],
          strengths: ['优势'],
          general_suggestions: ['建议'],
        },
        teacher_score: 0,
        teacher_feedback: '',
        created_at: now,
        updated_at: now,
      }),
    )
    expect(report).toMatchObject({
      conversationId: '2',
      status: 'reviewed',
      teacherScore: 0,
      analysis: { generalSuggestions: ['建议'] },
    })
    const summary = {
      id: '1',
      conversationId: '2',
      studentId: '3',
      studentName: '学生',
      status: 'reviewed' as const,
      kind: 'qa_learning_report' as const,
      aiScore: 0,
      messagePreview: '',
      messageCount: 0,
      createdAt: now,
      updatedAt: now,
    }
    expect(toReportSummaryView(summary).status).toBe('已批阅')
    expect(toConversationSummaryView({ ...summary, reportStatus: undefined }).reportStatus).toBeUndefined()
    expect(toQuestionView({ id: '1', title: '问题', type: '医学常识', status: 'answered', time: now }).status).toBe(
      '已回答',
    )
    expect(optional(undefined, toReportSummaryView)).toBeUndefined()
    expect(nullable(null, toReportSummaryView)).toBeNull()
    expect(
      toProblem(
        apiProblemSchema.parse({
          id: 1,
          type: '病例分析',
          title: 'x',
          target: 'class',
          target_label: '一班',
          status: 'published',
          opening: fixture.case_definition.opening,
          created_at: now,
        }),
      ).opening?.chiefComplaint,
    ).toBe(fixture.case_definition.opening.chief_complaint)
    expect(() => toChatMessage({ id: 1, role: 'invalid', content: '', created_at: now })).toThrow(
      expect.objectContaining({ code: 'CONTRACT_ERROR' }),
    )
  })
})
