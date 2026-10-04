import type { PblMessage, PblTurnScope } from '@/features/pbl/public'

export type LearningDialogueTurn = {
  id: string
  student: PblMessage
  assistant?: PblMessage
  scope: PblTurnScope
}

export function groupLearningDialogueTurns(messages: PblMessage[]): LearningDialogueTurn[] {
  const turns: LearningDialogueTurn[] = []
  const turnByStudentId = new Map<string, LearningDialogueTurn>()

  for (const message of [...messages].sort((left, right) => left.sequence - right.sequence)) {
    if (message.role === 'student') {
      const turn: LearningDialogueTurn = { id: message.id, student: message, scope: message.turnScope }
      turns.push(turn)
      turnByStudentId.set(message.id, turn)
      continue
    }
    if (message.role !== 'assistant') continue

    const target =
      (message.replyToMessageId ? turnByStudentId.get(message.replyToMessageId) : undefined) ??
      [...turns].reverse().find((turn) => !turn.assistant && turn.student.sequence < message.sequence)
    if (target) target.assistant = message
  }

  return turns
}
