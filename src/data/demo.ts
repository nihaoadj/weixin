import type { Conversation, Problem, Report, StudentQuestion } from '@/types/domain'

const demoStudentId = 'demo_student'
const demoConversationId = 'demo-conversation-001'
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
          content: '患者发热、咳嗽和黄痰，为什么首先考虑社区获得性肺炎？',
          timestamp: '10:00',
        },
        {
          id: 'demo-msg-2',
          role: 'assistant',
          content: '可从病程、痰液性质、肺部体征和影像学证据进行结构化分析。',
          timestamp: '10:01',
        },
        {
          id: 'demo-msg-3',
          role: 'user',
          content: '还需要补充哪些危险因素和安全信息？',
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
      id: 'demo-report-001',
      conversationId: conversation.conversationId,
      messages: conversation.messages,
      analysis: {
        score: 78,
        summary: '已识别主要诊断方向，但危险因素和安全边界仍需补充。',
        errors: [
          {
            content: '危险因素追问不完整。',
            suggestion: '补充既往史、过敏史和近期住院用药史。',
          },
        ],
        strengths: ['能够结合症状和影像建立初步问题表征。'],
        generalSuggestions: ['使用起病、伴随症状、危险因素和安全信息的固定提问顺序。'],
      },
      createdAt: demoCreatedAt,
      studentId: demoStudentId,
      studentName: '示例学生',
      status: '待批阅',
    },
  ]
}

export const builtInQuestions: StudentQuestion[] = [
  { id: '1', title: '肺炎的典型症状有哪些？', type: '医学常识', time: '2026-03-08', status: '未回答' },
  { id: '2', title: '高血压的诊断标准是什么？', type: '医学常识', time: '2026-03-07', status: '未回答' },
  { id: '3', title: '糖尿病的并发症有哪些？', type: '医学常识', time: '2026-03-06', status: '未回答' },
  {
    id: '4',
    title: '医生您好，我今年65岁，从2小时前开始胸口持续压榨样疼痛，我应该如何判断？',
    type: '模拟诊疗',
    time: '2026-03-05',
    status: '未回答',
  },
  { id: '5', title: '分析急性阑尾炎的诊断思路和治疗方案', type: '病例分析', time: '2026-03-04', status: '未回答' },
  {
    id: '6',
    title: '患者近期明显口渴、多尿并伴随体重下降，请进行模拟问诊。',
    type: '模拟诊疗',
    time: '2026-03-02',
    status: '未回答',
  },
]

export function createDemoProblems(): Problem[] {
  const today = new Date().toISOString().slice(0, 10)
  return [
    {
      id: 'prob_001',
      type: '医学常识',
      title: '抗菌药物合理使用的基本原则有哪些？',
      description: '请从适应证、病原学依据、疗程和不良反应监测等方面说明。',
      target: 'all',
      status: '待审核',
      time: today,
    },
    {
      id: 'prob_002',
      type: '病例分析',
      title: '高血压病例分析',
      description: '患者男性，55岁，血压160/100mmHg，并有头痛、头晕症状。请分析诊断和治疗思路。',
      target: 'all',
      status: '待审核',
      time: today,
    },
    {
      id: 'prob_003',
      type: '模拟诊疗',
      title: '发热咳嗽病例模拟诊疗',
      description: '患者发热3天，体温持续在38℃以上，咳嗽时胸痛并伴黄色痰。',
      target: 'all',
      status: '待审核',
      time: today,
    },
  ]
}
