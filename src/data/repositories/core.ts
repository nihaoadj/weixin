import type {
  Conversation,
  ConversationSummary,
  Page,
  Problem,
  QuestionThread,
  Report,
  ReportSummaryPage,
  StudentQuestion,
} from '@/types/records'

export type ReportDraftInput = Omit<Report, 'studentId' | 'studentName' | 'status'>

export interface ConversationRepository {
  getConversations(): Promise<Conversation[]>
  getConversationSummaries(limit: number, offset: number): Promise<Page<ConversationSummary>>
  findConversation(conversationId: string): Promise<Conversation | undefined>
  upsertConversation(conversation: Conversation): Promise<void>
}

export interface ReportRepository {
  getReports(): Promise<Report[]>
  getReportSummaries(limit: number, offset: number): Promise<ReportSummaryPage>
  findReport(conversationIdOrReportId: string): Promise<Report | undefined>
  findReportByConversation(conversationId: string): Promise<Report | undefined>
  saveDraftReport(input: ReportDraftInput): Promise<Report>
  submitReportForReview(conversationId: string): Promise<Report | null>
  reviewReport(conversationIdOrReportId: string, score: number, feedback: string): Promise<Report | null>
}

export interface QuestionRepository {
  getProblems(): Promise<Problem[]>
  findProblem(id: string): Promise<Problem | undefined>
  saveProblems(problems: Problem[]): Promise<void>
  upsertProblem(problem: Problem): Promise<Problem>
  publishProblem(id: string): Promise<Problem | null>
  rejectProblem(id: string): Promise<Problem | null>
  resetProblems(): Promise<Problem[]>
  getStudentQuestions(): Promise<StudentQuestion[]>
  findStudentQuestion(id: string): Promise<StudentQuestion | undefined>
  getQuestionThread(questionId: string): Promise<QuestionThread | undefined>
  saveQuestionThread(thread: QuestionThread): Promise<void>
}

/** Compatibility aggregate; new use cases depend on the narrower resource ports. */
export interface CoreRepository extends ConversationRepository, ReportRepository, QuestionRepository {}
