export type UserRole = 'student' | 'teacher'
export type MessageRole = 'user' | 'assistant'
export type ReportStatus = '草稿' | '待批阅' | '已批阅'
export type ProblemStatus = '待审核' | '已发布' | '已拒绝'
export type ProblemType = '医学常识' | '模拟诊疗' | '病例分析'
export type ProblemTarget = 'all' | 'class' | 'individual'

export interface SessionUser {
  openid: string
  role: UserRole
  nickName: string
  avatarUrl: string
  classIds?: string[]
  permissions?: string[]
  createdAt: string
}

export interface ChatMessage {
  id: string
  role: MessageRole
  content: string
  timestamp: string
}

export interface Conversation {
  conversationId: string
  messages: ChatMessage[]
  createdAt: string
  updatedAt: string
}

export interface AnalysisIssue {
  content: string
  suggestion: string
}

export interface ConversationAnalysis {
  errors: AnalysisIssue[]
  strengths?: string[]
  generalSuggestions?: string[]
  score: number
  summary: string
}

export interface Report {
  id?: string
  conversationId: string
  messages: ChatMessage[]
  analysis: ConversationAnalysis
  createdAt: string
  studentId: string
  studentName: string
  status: ReportStatus
  teacherScore?: number
  teacherFeedback?: string
}

export interface Problem {
  id: string
  type: ProblemType
  title: string
  description: string
  target: ProblemTarget
  status: ProblemStatus
  time: string
  publishTime?: string
  targetIds?: string[]
  targetLabel?: string
  className?: string
  studentCount?: number
  answerCount?: number
  contentType?: import('./case').CaseContentType
  slug?: string
  specialty?: string
  difficulty?: import('./case').CaseDifficulty
  estimatedMinutes?: number
  version?: number
  authorId?: number
  parentProblemId?: number
  medicalReviewStatus?: 'not_submitted' | 'pending' | 'approved' | 'rejected'
  opening?: import('./case').CaseOpening
  capabilityTags?: string[]
}

export interface StudentQuestion {
  id: string
  type: ProblemType
  title: string
  description?: string
  time: string
  status: '未回答' | '已回答'
}

export interface QuestionThread {
  questionId: string
  messages: ChatMessage[]
  updatedAt: string
}
