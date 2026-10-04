import { beforeEach, describe, expect, it, vi } from 'vitest'
import { apiLearningRoutes } from './apiLearningRoutes'

const http = vi.hoisted(() => ({ request: vi.fn(), response: undefined as unknown }))
vi.mock('@/platform/http/apiClient', () => ({
  apiRequest: http.request,
  encodePathSegment: (id: string) => encodeURIComponent(id),
}))
const routeId = '11111111-1111-4111-8111-111111111111'
const testId = '22222222-2222-4222-8222-222222222222'
const questionId = '33333333-3333-4333-8333-333333333333'
const stepId = '44444444-4444-4444-8444-444444444444'
const resultId = '55555555-5555-4555-8555-555555555555'
const timestamp = '2026-09-27T00:00:00Z'
const question = {
  id: questionId,
  position: 1,
  point_code: 'pathology.inflammation',
  prompt: '判断机制',
  options: ['甲', '乙', '丙', '丁'],
}
const attempt = {
  id: routeId,
  status: 'in_progress',
  version: 3,
  answers: { [questionId]: 0 },
  saved_at: timestamp,
  submitted_at: null,
}
const studentTest = {
  id: testId,
  title: '最终测试',
  review_kind: 'ai_direct',
  released_version: 2,
  released_digest: 'frozen',
  questions: [question],
  attempt,
}
const result = {
  id: testId,
  route_id: routeId,
  source_kind: 'autonomous',
  goal_point_codes: ['pathology.inflammation'],
  route_summary: { title: '冻结路线' },
  correct_count: 0,
  question_count: 1,
  score: 0,
  submitted_at: timestamp,
  questions: [{ ...question, selected_option: 0, correct_option: 1, explanation: '机制依据' }],
  review_kind: 'ai_direct',
}
const routeSummary = {
  id: routeId,
  title: '个人学习路线',
  source_kind: 'autonomous',
  scope_status: 'active',
  session_locator: 'session:8',
  goal_point_codes: ['pathology.inflammation'],
  status: 'active',
  next_action: 'complete_reading',
  progress: { completed_steps: 0, total_steps: 1 },
  updated_at: timestamp,
  test_summary: {
    id: testId,
    title: '最终测试',
    question_count: 1,
    generation_state: 'ready',
    review_state: 'released',
    review_kind: 'ai_direct',
    can_start: false,
    lock_reason: 'complete_route',
    claim_expires_at: null,
    retry_allowed: false,
  },
  result_id: resultId,
  generation_state: 'ready',
  claim_expires_at: null,
  retry_allowed: false,
}
const routeDetail = {
  summary: routeSummary,
  diagnosis_summary: { diagnosis_outcome: '炎症反应' },
  steps: [
    {
      id: stepId,
      position: 1,
      kind: 'reading',
      title: '炎症机制',
      goal_point_codes: ['pathology.inflammation'],
      status: 'completed',
      case_id: null,
      completed_at: timestamp,
    },
  ],
  test_summary: routeSummary.test_summary,
  can_start_test: true,
  lock_reasons: [],
  route_version: 4,
}
const teacherQuestion = {
  id: questionId,
  position: 1,
  primary_point_code: 'pathology.inflammation',
  prompt: '判断机制',
  options: ['甲', '乙', '丙', '丁'],
  correct_option: 1,
  explanation: '机制依据',
  source_digest: 'a'.repeat(64),
}
const teacherTest = {
  id: testId,
  route_id: routeId,
  title: '课堂最终测试',
  source_kind: 'classroom',
  class_id: 7,
  session_id: 8,
  student_id: 9,
  diagnosis_summary: { diagnosis_outcome: '炎症反应' },
  goal_point_codes: ['pathology.inflammation'],
  generation_state: 'ready',
  review_state: 'pending_teacher',
  review_kind: 'teacher',
  current_scope_active: true,
  version: 3,
  draft_digest: 'draft-v3',
  questions: [teacherQuestion],
  released_at: null,
  feedback_draft: '请补充依据',
}
const teacherResult = {
  ...result,
  id: resultId,
  student_id: 9,
  class_id: 7,
  session_id: 8,
}
beforeEach(() => {
  http.request.mockReset()
  http.request.mockImplementation(async (options: { schema: { parse(value: unknown): unknown } }) =>
    options.schema.parse(http.response),
  )
})
describe('T44 learning route API adapter', () => {
  it('requires the server scope projection before exposing a TeacherTest', async () => {
    const { current_scope_active, ...legacyResponse } = teacherTest
    expect(current_scope_active).toBe(true)
    http.response = legacyResponse
    await expect(apiLearningRoutes.getTeacherFinalTest(testId)).rejects.toThrow()
  })

  it('maps released tests and recoverable attempts without exposing answer keys', async () => {
    http.response = studentTest
    const view = await apiLearningRoutes.startFinalTest(testId, 'original-start')
    expect(view).toMatchObject({
      id: testId,
      reviewKind: 'ai_direct',
      releasedVersion: 2,
      releasedDigest: 'frozen',
      attempt: { version: 3, answers: { [questionId]: 0 }, savedAt: timestamp },
    })
    expect(view.questions[0]).not.toHaveProperty('correctOption')
    expect(http.request).toHaveBeenCalledWith(
      expect.objectContaining({
        method: 'POST',
        path: `/learning/final-tests/${testId}/start`,
        body: { client_request_id: 'original-start' },
      }),
    )
  })
  it('rejects answer-bearing or non-four-option student question responses', async () => {
    http.response = { ...studentTest, questions: [{ ...question, correct_option: 1, explanation: 'hidden' }] }
    await expect(apiLearningRoutes.getFinalTest(routeId)).rejects.toThrow()
    http.response = { ...studentTest, questions: [{ ...question, options: ['甲', '乙'] }] }
    await expect(apiLearningRoutes.getFinalTest(routeId)).rejects.toThrow()
  })
  it('carries original draft identity, expected version and frozen digest and invalidates caches', async () => {
    http.response = attempt
    const view = await apiLearningRoutes.saveFinalTestDraft(testId, 'original-draft', 3, 'frozen', { [questionId]: 0 })
    expect(view).toMatchObject({ version: 3, answers: { [questionId]: 0 } })
    expect(http.request).toHaveBeenCalledWith(
      expect.objectContaining({
        method: 'PUT',
        body: {
          client_request_id: 'original-draft',
          expected_version: 3,
          released_digest: 'frozen',
          answers: { [questionId]: 0 },
        },
        invalidateCache: expect.arrayContaining(['/learning/routes/', `/learning/final-tests/${testId}`]),
      }),
    )
  })
  it('preserves missing mixed grading points rather than inventing a zero, while retaining a real zero', async () => {
    http.response = {
      ...result,
      format_version: 'mixed_v2',
      question_count: 5,
      questions: [
        ...[1, 2, 3].map((position) => ({ ...result.questions[0], position, question_type: 'single_choice' })),
        {
          ...result.questions[0],
          position: 4,
          question_type: 'multiple_choice',
          selected_option: null,
          correct_option: null,
          selected_options: [0, 1],
          correct_options: [1, 2],
        },
        {
          ...result.questions[0],
          question_type: 'short_answer',
          position: 5,
          options: [],
          selected_option: null,
          correct_option: null,
          selected_text: '学生作答',
          reference_answer: '参考答案',
        },
      ],
    }
    const missing = await apiLearningRoutes.getLearningRouteResult(routeId)
    expect(missing.questions[4].pointsAwarded).toBeUndefined()
    expect(missing.questions[4].pointsPossible).toBeUndefined()
    http.response = {
      ...(http.response as object),
      questions: (http.response as typeof result).questions.map((item, index) =>
        index === 4 ? { ...item, points_awarded: 0, points_possible: 30 } : item,
      ),
    }
    const zero = await apiLearningRoutes.getLearningRouteResult(routeId)
    expect(zero.questions[4]).toMatchObject({ pointsAwarded: 0, pointsPossible: 30 })
  })

  it('maps zero score and fixed explanation only from the submitted result response', async () => {
    http.response = result
    const view = await apiLearningRoutes.submitFinalTest(testId, 'whole-submit', 3, 'frozen', { [questionId]: 0 })
    expect(view).toMatchObject({
      routeId,
      correctCount: 0,
      questionCount: 1,
      score: 0,
      questions: [{ selectedOption: 0, correctOption: 1, explanation: '机制依据' }],
    })
    expect(http.request).toHaveBeenCalledWith(
      expect.objectContaining({
        method: 'POST',
        body: {
          client_submission_id: 'whole-submit',
          expected_version: 3,
          released_digest: 'frozen',
          answers: { [questionId]: 0 },
        },
        invalidateCache: expect.arrayContaining(['/learning/routes']),
      }),
    )
  })
  it('preserves case recovery identity, revision and failure state without resending', async () => {
    http.response = {
      id: testId,
      route_id: routeId,
      step_id: questionId,
      synthetic_case: { title: '合成病例', public_scenario: '教学情境', case_facts: [], target_point_codes: [] },
      phase: 'mechanism_explanation',
      revision: 1,
      status: 'in_progress',
      goals: [],
      stages: [
        {
          phase: 'pathology_recognition',
          goals: [{ goal_id: 'recognition', objective: '识别局部血管变化' }],
          prompt: '哪些事实提示血管变化？',
        },
        {
          phase: 'mechanism_explanation',
          goals: [{ goal_id: 'mechanism', objective: '解释局部充血机制' }],
          prompt: '请解释充血机制。',
        },
        {
          phase: 'evidence_judgment',
          goals: [{ goal_id: 'evidence', objective: '引用局部证据' }],
          prompt: '哪些事实支持判断？',
        },
        {
          phase: 'summary_reflection',
          goals: [{ goal_id: 'reflection', objective: '总结并改进推理' }],
          prompt: '请反思仍不确定之处。',
        },
      ],
      messages: [{ id: 'message', role: 'student', content: '原始依据', revision: 1, phase: 'pathology_recognition' }],
      next_prompt: '解释机制',
      safety_notice: '教学',
      pending_message: {
        client_message_id: 'original-case-message',
        request_revision: 1,
        processing_state: 'failed',
        retry_allowed: true,
        claim_expires_at: null,
      },
    }
    const view = await apiLearningRoutes.getRouteCase(testId)
    expect(view).toMatchObject({
      routeId,
      revision: 1,
      stages: expect.arrayContaining([
        expect.objectContaining({ goals: [{ goalId: 'recognition', objective: '识别局部血管变化' }] }),
        expect.objectContaining({ prompt: '请解释充血机制。' }),
      ]),
      pendingMessage: { clientMessageId: 'original-case-message', requestRevision: 1, retryAllowed: true },
    })
    expect(http.request).toHaveBeenCalledTimes(1)
    expect(http.request).toHaveBeenCalledWith(expect.objectContaining({ path: `/learning/route-cases/${testId}` }))
    const invalid = http.response as { stages: Array<{ goals: Array<Record<string, unknown>> }> }
    invalid.stages[0].goals[0].completion_requirements = ['内部规则']
    await expect(apiLearningRoutes.getRouteCase(testId)).rejects.toThrow()
  })
  it('completes a reading step with its original request identity and returns the frozen route locators', async () => {
    http.response = {
      ...routeDetail,
      summary: {
        ...routeSummary,
        progress: { completed_steps: 1, total_steps: 1 },
        next_action: 'start_final_test',
        test_summary: { ...routeSummary.test_summary, can_start: true, lock_reason: null },
      },
    }

    const view = await apiLearningRoutes.completeRouteReading(stepId, 'original-completion')

    expect(view).toMatchObject({
      summary: {
        id: routeId,
        sessionLocator: 'session:8',
        resultId,
        progress: { completedSteps: 1, totalSteps: 1 },
        testSummary: { id: testId, canStart: true },
      },
      steps: [{ id: stepId, status: 'completed', completedAt: timestamp }],
      routeVersion: 4,
    })
    expect(http.request).toHaveBeenCalledWith(
      expect.objectContaining({
        method: 'POST',
        path: `/learning/route-steps/${stepId}/complete-reading`,
        body: { client_request_id: 'original-completion' },
        invalidateCache: ['/learning/routes', `/learning/route-steps/${stepId}`],
      }),
    )
  })
  it('maps route case message retry state and sends the original revision-bound identity', async () => {
    http.response = {
      client_message_id: 'case-message-1',
      request_revision: 2,
      processing_state: 'failed',
      retry_allowed: true,
      reply: null,
      phase: 'mechanism_explanation',
      revision: 2,
      decision: null,
      missing_elements: ['机制依据'],
      status: 'in_progress',
    }

    await expect(apiLearningRoutes.sendRouteCaseMessage(testId, '原始回答', 'case-message-1', 2)).resolves.toEqual({
      clientMessageId: 'case-message-1',
      requestRevision: 2,
      processingState: 'failed',
      retryAllowed: true,
      reply: undefined,
      phase: 'mechanism_explanation',
      revision: 2,
      decision: undefined,
      missingElements: ['机制依据'],
      status: 'in_progress',
    })
    expect(http.request).toHaveBeenCalledWith(
      expect.objectContaining({
        method: 'POST',
        path: `/learning/route-cases/${testId}/messages`,
        body: { content: '原始回答', client_message_id: 'case-message-1', expected_revision: 2 },
        invalidateCache: [`/learning/route-cases/${testId}`, '/learning/routes'],
      }),
    )
  })
  it('restores reading content and lease state for the selected route step', async () => {
    http.response = {
      id: stepId,
      position: 2,
      kind: 'reading',
      title: '急性炎症的血管反应',
      goal_point_codes: ['pathology.inflammation'],
      status: 'in_progress',
      case_id: null,
      completed_at: null,
      route_id: routeId,
      sources: [
        {
          source_id: 'knowledge-card-14',
          title: '急性炎症机制',
          publisher: '病理学课程资料',
          url: 'https://example.edu/pathology/acute-inflammation',
          version: '2026.2',
          source_type: 'knowledge_card',
        },
      ],
      ai_guide: '按顺序理解血管变化和细胞反应。',
      sections: [{ title: '血管变化', text: '血管通透性增加。' }],
      learning_points: ['解释血管通透性变化'],
      reading_progress: { lease_token: 'reading-lease', accumulated_seconds: 0, last_seen_at: timestamp },
    }

    await expect(apiLearningRoutes.getLearningRouteStep(stepId)).resolves.toMatchObject({
      routeId,
      step: { id: stepId, status: 'in_progress', kind: 'reading' },
      sources: [
        {
          id: 'knowledge-card-14',
          title: '急性炎症机制',
          institution: '病理学课程资料',
          sourceType: 'knowledge_card',
        },
      ],
      sections: [{ title: '血管变化', text: '血管通透性增加。' }],
      readingProgress: { leaseToken: 'reading-lease', accumulatedSeconds: 0, lastSeenAt: timestamp },
    })
    expect(http.request).toHaveBeenCalledWith(
      expect.objectContaining({ path: `/learning/route-steps/${stepId}`, cacheTtlMs: expect.any(Number) }),
    )
  })
  it('loads the persisted result when reopening a completed student route', async () => {
    http.response = result

    await expect(apiLearningRoutes.getLearningRouteResult(routeId)).resolves.toMatchObject({
      id: testId,
      routeId,
      score: 0,
      correctCount: 0,
      questions: [{ selectedOption: 0, correctOption: 1, explanation: '机制依据' }],
    })
    expect(http.request).toHaveBeenCalledWith(
      expect.objectContaining({ path: `/learning/routes/${routeId}/result`, cacheTtlMs: expect.any(Number) }),
    )
  })
  it('reads the authorized test detail and saves edits against its current draft version', async () => {
    http.response = teacherTest
    const detail = await apiLearningRoutes.getTeacherFinalTest(testId)

    expect(detail).toMatchObject({
      id: testId,
      classId: 7,
      sessionId: 8,
      reviewState: 'pending_teacher',
      currentScopeActive: true,
    })
    expect(http.request).toHaveBeenCalledWith(
      expect.objectContaining({
        path: `/learning/teacher/final-tests/${testId}`,
      }),
    )

    const revisedQuestion = {
      id: questionId,
      position: 1,
      primaryPointCode: 'pathology.inflammation',
      prompt: '补充依据后，哪项最能解释血管通透性改变？',
      questionType: 'single_choice' as const,
      options: ['甲', '乙', '丙', '丁'] as [string, string, string, string],
      correctOption: 1,
      explanation: '答案应能对应血管反应的机制。',
    }
    http.response = {
      ...teacherTest,
      version: 4,
      draft_digest: 'draft-v4',
      questions: [{ ...teacherQuestion, prompt: revisedQuestion.prompt, source_digest: 'b'.repeat(64) }],
      feedback_draft: '请把题干和答案依据对应清楚。',
    }
    await expect(
      apiLearningRoutes.saveTeacherFinalTest(
        testId,
        'teacher-edit-4',
        3,
        [revisedQuestion],
        '请把题干和答案依据对应清楚。',
      ),
    ).resolves.toMatchObject({
      id: testId,
      version: 4,
      draftDigest: 'draft-v4',
      currentScopeActive: true,
      questions: [{ prompt: revisedQuestion.prompt, correctOption: 1 }],
    })
    expect(http.request).toHaveBeenLastCalledWith(
      expect.objectContaining({
        method: 'PUT',
        path: `/learning/teacher/final-tests/${testId}`,
        body: {
          client_request_id: 'teacher-edit-4',
          expected_version: 3,
          feedback_draft: '请把题干和答案依据对应清楚。',
          questions: [
            {
              id: questionId,
              position: 1,
              primary_point_code: 'pathology.inflammation',
              prompt: revisedQuestion.prompt,
              question_type: 'single_choice',
              options: revisedQuestion.options,
              correct_option: 1,
              correct_options: null,
              reference_answer: null,
              rubric: null,
              explanation: revisedQuestion.explanation,
            },
          ],
        },
        invalidateCache: ['/learning/teacher/final-tests', '/learning/teacher/final-test-review-queue'],
      }),
    )
  })
  it('requests teacher changes with the reviewed version and retries failed test generation by identity', async () => {
    http.response = { ...teacherTest, review_state: 'needs_changes' }
    await expect(
      apiLearningRoutes.requestTeacherTestChanges(testId, 'request-revision', 3, '请补充推理依据'),
    ).resolves.toMatchObject({
      id: testId,
      reviewState: 'needs_changes',
      currentScopeActive: true,
    })
    expect(http.request).toHaveBeenLastCalledWith(
      expect.objectContaining({
        method: 'POST',
        path: `/learning/teacher/final-tests/${testId}/request-changes`,
        body: { client_request_id: 'request-revision', expected_version: 3, note: '请补充推理依据' },
        invalidateCache: ['/learning/teacher/final-tests', '/learning/teacher/final-test-review-queue'],
      }),
    )

    http.response = {
      route_id: routeId,
      component: 'test',
      generation_state: 'pending',
      claim_expires_at: null,
    }
    await expect(apiLearningRoutes.retryTeacherTestGeneration(testId, 'retry-test-generation')).resolves.toEqual({
      routeId,
      component: 'test',
      generationState: 'pending',
      claimExpiresAt: undefined,
    })
    expect(http.request).toHaveBeenLastCalledWith(
      expect.objectContaining({
        method: 'POST',
        path: `/learning/teacher/final-tests/${testId}/retry-generation`,
        body: { client_request_id: 'retry-test-generation' },
        invalidateCache: ['/learning/teacher/final-tests', '/learning/teacher/final-test-review-queue'],
      }),
    )
  })
  it('maps teacher release receipts and scoped result reads while preserving release identity', async () => {
    http.response = {
      test_id: testId,
      released_version: 4,
      released_digest: 'released-v4',
      released_at: timestamp,
    }
    await expect(
      apiLearningRoutes.releaseTeacherFinalTest(testId, 'original-release', 3, 'draft-v3', '发布说明'),
    ).resolves.toEqual({
      testId,
      releasedVersion: 4,
      releasedDigest: 'released-v4',
      releasedAt: timestamp,
    })
    expect(http.request).toHaveBeenLastCalledWith(
      expect.objectContaining({
        method: 'POST',
        path: `/learning/teacher/final-tests/${testId}/release`,
        body: {
          client_request_id: 'original-release',
          expected_version: 3,
          draft_digest: 'draft-v3',
          feedback: '发布说明',
        },
        invalidateCache: [
          '/learning/teacher/final-tests',
          '/learning/teacher/final-test-review-queue',
          '/learning/teacher/route-results',
        ],
      }),
    )

    http.request.mockClear()
    http.response = teacherResult
    await expect(apiLearningRoutes.getTeacherRouteResult(resultId)).resolves.toMatchObject({
      id: resultId,
      routeId,
      studentId: 9,
      classId: 7,
      sessionId: 8,
      questions: [{ correctOption: 1, explanation: '机制依据' }],
    })

    http.response = teacherTest
    await expect(apiLearningRoutes.getTeacherFinalTest(testId)).resolves.toMatchObject({
      id: testId,
      routeId,
      classId: 7,
      sessionId: 8,
      studentId: 9,
      questions: [{ id: questionId, primaryPointCode: 'pathology.inflammation', correctOption: 1 }],
    })
  })
  it('does not include provider private completion requirements in a student case', async () => {
    const validCase = {
      id: testId,
      route_id: routeId,
      step_id: questionId,
      synthetic_case: { title: '合成病例', public_scenario: '教学情境', case_facts: [], target_point_codes: [] },
      phase: 'pathology_recognition',
      revision: 0,
      status: 'in_progress',
      goals: [],
      stages: [
        {
          phase: 'pathology_recognition',
          goals: [{ goal_id: 'recognition', objective: '识别病理变化' }],
          prompt: '哪些事实支持识别？',
        },
        {
          phase: 'mechanism_explanation',
          goals: [{ goal_id: 'mechanism', objective: '解释病理机制' }],
          prompt: '请解释机制。',
        },
        {
          phase: 'evidence_judgment',
          goals: [{ goal_id: 'evidence', objective: '引用病例证据' }],
          prompt: '哪些证据支持判断？',
        },
        {
          phase: 'summary_reflection',
          goals: [{ goal_id: 'reflection', objective: '总结并反思' }],
          prompt: '请反思推理过程。',
        },
      ],
      messages: [],
      next_prompt: '解释机制',
      safety_notice: '教学',
      pending_message: null,
    }
    http.response = validCase
    await expect(apiLearningRoutes.getRouteCase(testId)).resolves.toMatchObject({ id: testId })
    http.response = { ...validCase, completion_requirements: ['private rule'] }
    await expect(apiLearningRoutes.getRouteCase(testId)).rejects.toThrow()
  })
  it('keeps heartbeat lease identity and maps zero accumulated seconds', async () => {
    http.response = { lease_token: 'original-lease', accumulated_seconds: 0, last_seen_at: timestamp }
    expect(
      await apiLearningRoutes.saveRouteReadingProgress(questionId, 'heartbeat', 'original-heartbeat', 'original-lease'),
    ).toEqual({ leaseToken: 'original-lease', accumulatedSeconds: 0, lastSeenAt: timestamp })
    expect(http.request).toHaveBeenCalledWith(
      expect.objectContaining({
        method: 'POST',
        body: { action: 'heartbeat', lease_token: 'original-lease', client_request_id: 'original-heartbeat' },
      }),
    )
  })
  it('propagates API failures without creating local Demo data', async () => {
    const error = Object.assign(new Error('server scope denied'), { code: 'FORBIDDEN', statusCode: 403 })
    http.request.mockRejectedValueOnce(error)
    await expect(apiLearningRoutes.getLearningRoute(routeId)).rejects.toBe(error)
    expect(http.request).toHaveBeenCalledTimes(1)
  })
})
