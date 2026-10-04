import type { Conversation, Report, StudentQuestion } from '@/types/domain'

const demoStudentId = 'demo_student'
const demoConversationId = 'pathology-demo-conversation-v2'
const demoCreatedAt = '2026-08-28T10:00:00.000Z'
// T29 submit-flow fixture: a deterministic draft QA learning report the demo
// student can submit to the demo class through the real picker/confirm flow.
const demoDraftConversationId = 'pathology-demo-draft-conversation'
const demoDraftCreatedAt = '2026-09-13T09:00:00.000Z'

export function createDemoConversations(): Conversation[] {
  return [
    {
      conversationId: demoDraftConversationId,
      createdAt: demoDraftCreatedAt,
      updatedAt: demoDraftCreatedAt,
      messages: [
        {
          id: 'demo-draft-msg-1',
          role: 'user',
          content: '血栓形成的条件有哪些？怎样和死后凝血块区分？',
          timestamp: '09:00',
        },
        {
          id: 'demo-draft-msg-2',
          role: 'assistant',
          content: '可以从内皮损伤、血流状态与血液凝固性三方面整理，再比较附着度与镜下结构。',
          timestamp: '09:01',
        },
      ],
    },
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
  const [draftConversation, conversation] = createDemoConversations()
  return [
    {
      id: 'pathology-demo-report-draft',
      conversationId: draftConversation.conversationId,
      messages: draftConversation.messages,
      analysis: {
        score: 64,
        summary: '已列出 thrombosis 形成条件，但区分可逆变化的依据还不完整。',
        errors: [
          {
            content: '死后凝血块的鉴别要点未展开。',
            suggestion: '补充附着度、光泽、镜下纤丝结构等对照观察。',
          },
        ],
        strengths: ['能够按条件逐项列举。'],
        generalSuggestions: ['按假设、证据、机制解释的顺序重组答案。'],
      },
      createdAt: demoDraftCreatedAt,
      studentId: demoStudentId,
      studentName: '示例学生',
      status: '草稿',
      kind: 'qa_learning_report',
    },
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
      kind: 'qa_learning_report',
      classId: '1',
      className: '病理学演示班',
    },
  ]
}

export const builtInQuestions: StudentQuestion[] = []
