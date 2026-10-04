import { describe, expect, it } from 'vitest'
import type { PblParticipation } from '@/features/pbl/public'
import { resolvePblConversationState } from './conversationState'

const participation = (overrides: Partial<PblParticipation> = {}): PblParticipation => ({
  messages: [],
  currentPhase: 'problem_framing',
  phaseStartedRevision: 0,
  phaseStatus: 'active',
  interactionStyle: 'guided',
  evidenceLocked: false,
  conversationMode: 'evidence',
  ...overrides,
})

describe('T32 PBL conversation state', () => {
  it('allows an active classroom to start from the first message, and blocks closed active participation', () => {
    expect(resolvePblConversationState('active', undefined, []).canSend).toBe(true)
    expect(resolvePblConversationState('active', participation(), []).canSend).toBe(true)
    expect(resolvePblConversationState('closed', participation(), []).canSend).toBe(false)
  })

  it('allows completed private follow-up even after the classroom closes', () => {
    const completed = participation({
      currentPhase: 'completed',
      phaseStatus: 'completed',
      phaseStartedRevision: 4,
      evidenceLocked: true,
      conversationMode: 'private_follow_up',
      completionSnapshotId: '9',
      evidenceCompletedRevision: 4,
    })
    expect(resolvePblConversationState('closed', completed, [])).toMatchObject({
      canSend: true,
      isPrivate: true,
      integrityError: false,
      privateBoundaryIndex: -1,
    })
  })

  it('blocks a completed record whose server completion locator is incomplete', () => {
    const broken = participation({
      currentPhase: 'completed',
      phaseStatus: 'completed',
      evidenceLocked: true,
      conversationMode: 'private_follow_up',
    })
    expect(resolvePblConversationState('active', broken, [])).toMatchObject({ canSend: false, integrityError: true })
  })
})
