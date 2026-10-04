import type { InteractionStyle } from '@/features/pbl/public'

export interface PendingPblMessage {
  id: string
  content: string
  sessionId: string
  interactionStyle: InteractionStyle
}

export function resolvePendingPblMessage(
  current: PendingPblMessage | undefined,
  next: Omit<PendingPblMessage, 'id'>,
  createId: () => string,
): PendingPblMessage {
  if (
    current?.content === next.content &&
    current.sessionId === next.sessionId &&
    current.interactionStyle === next.interactionStyle
  )
    return current
  return { ...next, id: createId() }
}

export function invalidatePendingPblMessage(
  current: PendingPblMessage | undefined,
  interactionStyle: InteractionStyle,
): PendingPblMessage | undefined {
  return current?.interactionStyle === interactionStyle ? current : undefined
}
