import { describe, expect, it } from 'vitest'
import type { ChatMessage } from '@/types/domain'
import { analyzeConversation } from './report'

function userMessage(content: string): ChatMessage {
  return {
    id: `msg_${content}`,
    role: 'user',
    content,
    timestamp: '10:00',
  }
}

describe('analyzeConversation', () => {
  it('returns strengths when no structural issue is detected', () => {
    const analysis = analyzeConversation([
      userMessage('肺炎需要结合病原体证据、影像学依据、危险因素、鉴别诊断和治疗副作用进行分析。'),
    ])

    expect(analysis.errors).toHaveLength(0)
    expect(analysis.strengths?.length).toBeGreaterThan(0)
    expect(analysis.score).toBeGreaterThanOrEqual(80)
  })

  it('deducts score for missing pathogen and treatment safety details', () => {
    const analysis = analyzeConversation([userMessage('肺炎的症状包括发热。'), userMessage('治疗可以使用抗菌药物。')])

    expect(analysis.errors.length).toBeGreaterThanOrEqual(2)
    expect(analysis.score).toBeLessThan(90)
  })
})
