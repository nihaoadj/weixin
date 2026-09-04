import type { Conversation, Report, StudentQuestion } from '@/types/domain'

const demoStudentId = 'demo_student'
const demoConversationId = 'pathology-demo-conversation-v2'
const demoCreatedAt = '2026-08-28T10:00:00.000Z'

export function createDemoConversations(): Conversation[] {
  return [
    {
      conversationId: demoConversationId,
      createdAt: demoCreatedAt,
      updatedAt: demoCreatedAt,
      messages: [
        {
          id: 'demo-msg-1',
          role: 'user',
          content: '组织切片中出现细胞肿胀，怎样区分可逆损伤与坏死？',
          timestamp: '10:00',
        },
        {
          id: 'demo-msg-2',
          role: 'assistant',
          content: '先描述细胞形态与核的改变，再比较可逆损伤与坏死的证据。',
          timestamp: '10:01',
        },
        {
          id: 'demo-msg-3',
          role: 'user',
          content: '还需要观察哪些核变化才能支持坏死？',
          timestamp: '10:02',
        },
      ],
    },
  ]
}

export function createDemoReports(): Report[] {
  const [conversation] = createDemoConversations()
  return [
    {
      id: 'pathology-demo-report-v2',
      conversationId: conversation.conversationId,
      messages: conversation.messages,
      analysis: {
        score: 78,
        summary: '已描述细胞损伤的形态，仍需区分可逆变化与细胞死亡。',
        errors: [
          {
            content: '核变化的证据不完整。',
            suggestion: '补充核固缩、核碎裂与核溶解的观察。',
          },
        ],
        strengths: ['能够结合形态观察建立初步解释。'],
        generalSuggestions: ['按观察、假设、证据比较和机制解释的顺序讨论。'],
      },
      createdAt: demoCreatedAt,
      studentId: demoStudentId,
      studentName: '示例学生',
      status: '待批阅',
    },
  ]
}

export const builtInQuestions: StudentQuestion[] = []
