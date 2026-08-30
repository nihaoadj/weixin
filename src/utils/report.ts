import type { ChatMessage, ConversationAnalysis } from '@/types/domain'

export function analyzeConversation(messages: ChatMessage[]): ConversationAnalysis {
  const studentMessages = messages.filter((message) => message.role === 'user')
  const errors: ConversationAnalysis['errors'] = []

  if (studentMessages.some((message) => message.content.includes('肺炎') && !message.content.includes('病原体'))) {
    errors.push({
      content: '描述肺炎时尚未区分病原体和临床场景。',
      suggestion: '描述疾病时补充病原学、危险因素和鉴别诊断依据。',
    })
  }
  if (studentMessages.some((message) => message.content.includes('治疗') && !message.content.includes('副作用'))) {
    errors.push({
      content: '治疗方案没有覆盖不良反应或注意事项。',
      suggestion: '同时说明适应证、禁忌证、不良反应和随访要点。',
    })
  }
  if (
    studentMessages.some((message) => message.content.includes('症状') && message.content.split(/[，,]/).length < 3)
  ) {
    errors.push({
      content: '临床表现描述维度较少。',
      suggestion: '从主诉、伴随症状、体征、病程和危险因素多个维度补充。',
    })
  }
  const issuePenalty = errors.length * 5
  const score = Math.max(0, Math.min(100, 88 - issuePenalty + Math.min(studentMessages.length * 2, 10)))
  const summary =
    score >= 90
      ? '表现优秀，知识结构清晰，可继续加强循证依据和临床推理。'
      : score >= 70
        ? '表现良好，主要知识点基本到位，建议补足关键细节。'
        : score >= 60
          ? '基础概念尚可，但推理链条需要进一步训练。'
          : '目前存在较多知识缺口，建议先复习相关基础章节。'

  const strengths = errors.length === 0 ? ['回答结构完整，未检测到明显的结构性问题。'] : []
  const generalSuggestions = ['继续补充诊断依据、鉴别诊断和证据来源。']

  return { errors, strengths, generalSuggestions, score, summary }
}
