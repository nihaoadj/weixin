import type { PblMessage, PblParticipation } from '@/features/pbl/public'

export type PblConversationState = {
  canSend: boolean
  isPrivate: boolean
  integrityError: boolean
  privateBoundaryIndex: number
}

export function resolvePblConversationState(
  sessionStatus: string | undefined,
  participation: PblParticipation | undefined,
  messages: PblMessage[],
): PblConversationState {
  const completed = participation?.phaseStatus === 'completed'
  const isPrivate = participation?.conversationMode === 'private_follow_up'
  const hasCompletionLocator = Boolean(
    participation?.completionSnapshotId && participation.evidenceCompletedRevision != null,
  )
  const integrityError = Boolean(completed && (!participation?.evidenceLocked || !isPrivate || !hasCompletionLocator))
  return {
    canSend: Boolean(
      !integrityError &&
      (participation
        ? (completed && isPrivate) || (!completed && sessionStatus === 'active' && !participation.evidenceLocked)
        : sessionStatus === 'active'),
    ),
    isPrivate,
    integrityError,
    privateBoundaryIndex: messages.findIndex((message) => message.turnScope === 'private_follow_up'),
  }
}
