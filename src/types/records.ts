// Repository domain records. No generated DTOs or localized state labels.
export type UserRole = 'student' | 'teacher'
export type MessageRole = 'user' | 'assistant'
export type ReportStatus = 'draft' | 'pending_review' | 'reviewed'
export type ProblemStatus = 'draft' | 'published' | 'rejected'
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

export interface Page<T> {
  items: T[]
  total: number
  limit: number
  offset: number
}

export interface ConversationSummary {
  id: string
  conversationId: string
  messagePreview: string
  messageCount: number
  reportId?: string
  reportStatus?: ReportStatus
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
  updatedAt?: string
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

export interface ReportSummary {
  id: string
  conversationId: string
  studentId: string
  studentName: string
  status: ReportStatus
  aiScore: number
  teacherScore?: number
  messagePreview: string
  messageCount: number
  createdAt: string
  updatedAt: string
}

export interface ReportSummaryPage extends Page<ReportSummary> {
  pendingCount: number
  reviewedCount: number
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
  status: 'unanswered' | 'answered'
}

export interface QuestionThread {
  questionId: string
  messages: ChatMessage[]
  updatedAt: string
}
