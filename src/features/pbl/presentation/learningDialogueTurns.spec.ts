import { describe, expect, it } from 'vitest'
import type { PblMessage } from '@/features/pbl/public'
import { groupLearningDialogueTurns } from './learningDialogueTurns'

const message = (value: Partial<PblMessage> & Pick<PblMessage, 'id' | 'sequence' | 'role'>): PblMessage => ({
  content: value.id,
  interactionStyle: 'guided',
  turnScope: 'evidence',
  ...value,
})

describe('groupLearningDialogueTurns', () => {
  it('groups replies by locator and keeps evidence/private scope from the student message', () => {
    const result = groupLearningDialogueTurns([
      message({ id: 'a2', sequence: 4, role: 'assistant', replyToMessageId: 's2', turnScope: 'private_follow_up' }),
      message({ id: 's1', sequence: 1, role: 'student' }),
      message({ id: 's2', sequence: 3, role: 'student', turnScope: 'private_follow_up' }),
      message({ id: 'a1', sequence: 2, role: 'assistant', replyToMessageId: 's1' }),
    ])

    expect(result.map((turn) => [turn.student.id, turn.assistant?.id, turn.scope])).toEqual([
      ['s1', 'a1', 'evidence'],
      ['s2', 'a2', 'private_follow_up'],
    ])
  })

  it('compatibly pairs an adjacent historical assistant reply without a locator', () => {
    const result = groupLearningDialogueTurns([
      message({ id: 's1', sequence: 1, role: 'student' }),
      message({ id: 'a1', sequence: 2, role: 'assistant' }),
    ])

    expect(result[0]?.assistant?.id).toBe('a1')
  })
})
