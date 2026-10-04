import { afterEach, describe, expect, it, vi } from 'vitest'
import { clearApiCache } from '@/platform/http/apiClient'
import { ApiPblRepository } from './apiPblRepository'

const response = {
  response_kind: 'evidence_assessment',
  turn_scope: 'evidence',
  diagnostic: {
    id: 31,
    diagnostic_status: 'ready',
    assistant_reply: '回应\n解释。\n\n关键要点\n1. 要点。\n\n下一步\n请说明依据。',
    follow_up_question: '请说明依据。',
    knowledge_gaps: [],
    reasoning_issues: [],
    schema_version: 6,
    revision: 1,
    safety_notice: '仅用于学习。',
    created_at: '2026-09-14T00:00:00Z',
    phase_evidence_summary: '',
    phase_missing_elements: [],
    interaction_style: 'direct',
  },
  messages: [
    {
      id: '31',
      sequence: 1,
      role: 'student',
      content: '请先直接讲解炎症渗出。',
      processing_status: 'completed',
      client_message_id: 'client-31',
      interaction_style: 'direct',
      turn_scope: 'evidence',
      reply_to_message_id: null,
    },
    {
      id: '32',
      sequence: 2,
      role: 'assistant',
      content: '回应\n解释。\n\n关键要点\n1. 要点。\n\n下一步\n请说明依据。',
      processing_status: 'completed',
      client_message_id: null,
      interaction_style: 'direct',
      turn_scope: 'evidence',
      reply_to_message_id: 31,
    },
  ],
  current_phase: 'problem_framing',
  phase_started_revision: 0,
  phase_status: 'active',
  phase_completed_at: null,
  interaction_style: 'direct',
  style_selected_at: '2026-09-14T00:00:00Z',
  evidence_locked: false,
  conversation_mode: 'evidence',
  completion_snapshot_id: null,
  evidence_completed_revision: null,
  private_follow_up: null,
} as const

const dialogueSession = {
  id: 41,
  class_id: null,
  topic_code: 'pathology.inflammation',
  status: 'active',
  created_at: '2026-09-14T00:00:00Z',
  closed_at: null,
  case_id: 6,
  case_version: 2,
  case_context: { title: '急性炎症', opening: { setting: '门诊', patient_intro: '患者', chief_complaint: '发热' } },
  goal_point_codes: ['pathology.inflammation'],
  phase: 'problem_framing',
  version: 1,
}

describe('ApiPblRepository T31 response style contract', () => {
  afterEach(() => {
    clearApiCache()
    vi.unstubAllEnvs()
  })

  it('sends the selected turn style and maps it on every returned message', async () => {
    vi.stubEnv('VITE_API_BASE_URL', 'https://api.example.com')
    vi.mocked(uni.request).mockImplementation((options) => {
      options.success?.({ statusCode: 200, data: response, header: {}, cookies: [], errMsg: 'request:ok' })
      return undefined as never
    })

    const result = await new ApiPblRepository().message('9', response.messages[0].content, 'client-31', 'direct')

    expect(vi.mocked(uni.request).mock.calls[0][0]).toMatchObject({
      method: 'POST',
      url: 'https://api.example.com/student/learning-dialogues/9/messages',
      data: {
        content: response.messages[0].content,
        client_message_id: 'client-31',
        interaction_style: 'direct',
      },
    })
    expect(result.interactionStyle).toBe('direct')
    expect(result.diagnostic?.interactionStyle).toBe('direct')
    expect(result.messages.map((message) => message.interactionStyle)).toEqual(['direct', 'direct'])
  })

  it('rejects a successful HTTP response that omits the canonical style field', async () => {
    vi.stubEnv('VITE_API_BASE_URL', 'https://api.example.com')
    vi.mocked(uni.request).mockImplementation((options) => {
      const { interaction_style: _omitted, ...malformedDiagnostic } = response.diagnostic
      options.success?.({
        statusCode: 200,
        data: { ...response, diagnostic: malformedDiagnostic },
        header: {},
        cookies: [],
        errMsg: 'request:ok',
      })
      return undefined as never
    })

    await expect(new ApiPblRepository().message('9', '内容', 'client-31', 'direct')).rejects.toMatchObject({
      code: 'CONTRACT_ERROR',
    })
  })

  it('maps a private follow-up while requiring the frozen completion locator', async () => {
    vi.stubEnv('VITE_API_BASE_URL', 'https://api.example.com')
    const privateResponse = {
      ...response,
      response_kind: 'private_follow_up',
      turn_scope: 'private_follow_up',
      current_phase: 'completed',
      phase_started_revision: 4,
      phase_status: 'completed',
      phase_completed_at: '2026-09-14T00:00:00Z',
      evidence_locked: true,
      conversation_mode: 'private_follow_up',
      completion_snapshot_id: 31,
      evidence_completed_revision: 4,
      learning_route_id: '11111111-1111-4111-8111-111111111111',
      final_test_id: '22222222-2222-4222-8222-222222222222',
      route_generation_state: 'ready',
      test_generation_state: 'pending',
      messages: response.messages.map((message) => ({ ...message, turn_scope: 'private_follow_up' as const })),
      private_follow_up: {
        student_message_id: 31,
        assistant_message_id: 32,
        processing_status: 'completed' as const,
        safety_status: 'standard',
        fallback_used: false,
      },
    } as const
    vi.mocked(uni.request).mockImplementation((options) => {
      options.success?.({ statusCode: 200, data: privateResponse, header: {}, cookies: [], errMsg: 'request:ok' })
      return undefined as never
    })

    const result = await new ApiPblRepository().message('9', '继续问', 'private-31', 'direct')
    expect(result).toMatchObject({
      responseKind: 'private_follow_up',
      turnScope: 'private_follow_up',
      completionSnapshotId: '31',
      evidenceCompletedRevision: 4,
      learningRouteId: '11111111-1111-4111-8111-111111111111',
      finalTestId: '22222222-2222-4222-8222-222222222222',
      routeGenerationState: 'ready',
      testGenerationState: 'pending',
      privateFollowUp: { assistantMessageId: '32' },
    })
  })

  it('hands a completed evidence turn to its frozen route and final-test locators', async () => {
    vi.stubEnv('VITE_API_BASE_URL', 'https://api.example.com')
    const completedEvidenceResponse = {
      ...response,
      current_phase: 'completed',
      phase_started_revision: 3,
      phase_status: 'completed',
      phase_completed_at: '2026-09-27T00:00:00Z',
      evidence_locked: true,
      conversation_mode: 'private_follow_up',
      completion_snapshot_id: 31,
      evidence_completed_revision: 4,
      learning_route_id: '11111111-1111-4111-8111-111111111111',
      final_test_id: '22222222-2222-4222-8222-222222222222',
      route_generation_state: 'ready',
      test_generation_state: 'pending',
    }
    vi.mocked(uni.request).mockImplementation((options) => {
      options.success?.({
        statusCode: 200,
        data: completedEvidenceResponse,
        header: {},
        cookies: [],
        errMsg: 'request:ok',
      })
      return undefined as never
    })

    const result = await new ApiPblRepository().message('41', '完成病例推理', 'completion-41', 'guided')

    expect(result).toMatchObject({
      responseKind: 'evidence_assessment',
      turnScope: 'evidence',
      phaseStatus: 'completed',
      evidenceLocked: true,
      completionSnapshotId: '31',
      evidenceCompletedRevision: 4,
      learningRouteId: '11111111-1111-4111-8111-111111111111',
      finalTestId: '22222222-2222-4222-8222-222222222222',
      routeGenerationState: 'ready',
      testGenerationState: 'pending',
    })
    expect(vi.mocked(uni.request).mock.calls[0][0]).toMatchObject({
      method: 'POST',
      url: 'https://api.example.com/student/learning-dialogues/41/messages',
      data: { client_message_id: 'completion-41' },
    })
  })

  it('rejects a private follow-up that changes the frozen diagnostic snapshot', async () => {
    vi.stubEnv('VITE_API_BASE_URL', 'https://api.example.com')
    const changedSnapshot = {
      ...response,
      response_kind: 'private_follow_up',
      turn_scope: 'private_follow_up',
      current_phase: 'completed',
      phase_started_revision: 4,
      phase_status: 'completed',
      phase_completed_at: '2026-09-14T00:00:00Z',
      evidence_locked: true,
      conversation_mode: 'private_follow_up',
      completion_snapshot_id: 99,
      evidence_completed_revision: 4,
      private_follow_up: {
        student_message_id: 33,
        assistant_message_id: 34,
        processing_status: 'completed',
        safety_status: 'standard',
        fallback_used: false,
      },
    }
    vi.mocked(uni.request).mockImplementation((options) => {
      options.success?.({ statusCode: 200, data: changedSnapshot, header: {}, cookies: [], errMsg: 'request:ok' })
      return undefined as never
    })

    await expect(new ApiPblRepository().message('41', '追问', 'follow-up-41', 'guided')).rejects.toMatchObject({
      code: 'CONTRACT_ERROR',
    })
  })

  it('creates a dialogue with the stable client locator and maps the canonical case locator', async () => {
    vi.stubEnv('VITE_API_BASE_URL', 'https://api.example.com')
    vi.mocked(uni.request).mockImplementation((options) => {
      options.success?.({
        statusCode: 201,
        data: { session: dialogueSession, participation: null },
        header: {},
        cookies: [],
        errMsg: 'request:ok',
      })
      return undefined as never
    })

    const created = await new ApiPblRepository().createDialogue({
      clientSessionId: 'stable-client-session',
      interactionStyle: 'guided',
      goalPointCodes: ['pathology.inflammation'],
    })

    expect(created).toMatchObject({
      session: {
        id: '41',
        caseId: '6',
        caseVersion: 2,
        sessionKind: 'classroom',
        evidenceLocked: false,
        conversationMode: 'evidence',
      },
      participation: undefined,
    })
    expect(vi.mocked(uni.request).mock.calls[0][0]).toMatchObject({
      method: 'POST',
      url: 'https://api.example.com/student/learning-dialogues',
      data: {
        client_session_id: 'stable-client-session',
        interaction_style: 'guided',
        goal_point_codes: ['pathology.inflammation'],
      },
    })
  })

  it('rejects an inconsistent completion locator instead of returning an apparently complete participation', async () => {
    vi.stubEnv('VITE_API_BASE_URL', 'https://api.example.com')
    const incompleteParticipation = {
      session_id: 41,
      messages: [],
      revision: 4,
      diagnostic: null,
      current_phase: 'completed',
      phase_started_revision: 0,
      phase_status: 'completed',
      phase_completed_at: '2026-09-14T00:00:00Z',
      interaction_style: 'guided',
      style_selected_at: null,
      evidence_locked: true,
      conversation_mode: 'private_follow_up',
      completion_snapshot_id: null,
      evidence_completed_revision: 4,
    }
    vi.mocked(uni.request).mockImplementation((options) => {
      options.success?.({
        statusCode: 200,
        data: incompleteParticipation,
        header: {},
        cookies: [],
        errMsg: 'request:ok',
      })
      return undefined as never
    })

    await expect(new ApiPblRepository().participation('41')).rejects.toMatchObject({ code: 'CONTRACT_ERROR' })
  })

  it('preserves the server permission boundary for a classroom dashboard', async () => {
    vi.stubEnv('VITE_API_BASE_URL', 'https://api.example.com')
    const repository = new ApiPblRepository()
    vi.mocked(uni.request).mockImplementationOnce((options) => {
      options.success?.({
        statusCode: 403,
        data: { detail: '无权查看该班级的病例数据' },
        header: {},
        cookies: [],
        errMsg: 'request:fail',
      } as never)
      return undefined as never
    })
    await expect(repository.dashboard('7', '8')).rejects.toMatchObject({
      code: 'FORBIDDEN',
      statusCode: 403,
      message: '无权查看该班级的病例数据',
    })
    expect(vi.mocked(uni.request)).toHaveBeenCalledTimes(1)
  })
})
