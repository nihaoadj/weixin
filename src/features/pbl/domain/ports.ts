export type PblSession = { id: string; classId: string; topicCode: string; status: string }
export type PblDiagnostic = {
  diagnosticStatus: string
  assistantReply: string
  followUpQuestion?: string
  knowledgeGaps: unknown[]
  reasoningIssues: unknown[]
  recommendedQuestions?: PblSuggestion[]
}
export type PblSuggestion = {
  id: string
  title: string
  prompt: string
  linkedFindings: string[]
  status: string
  version: number
  problemId?: string
}
export interface PblRepository {
  active(): Promise<PblSession[]>
  participation(id: string): Promise<{ messages: { role: string; content: string }[]; diagnostic?: PblDiagnostic }>
  message(id: string, content: string, clientMessageId: string): Promise<PblDiagnostic>
  diagnostics(): Promise<PblDiagnostic[]>
  editSuggestion(item: PblSuggestion, reject?: boolean): Promise<PblSuggestion>
  adopt(id: string): Promise<PblSuggestion>
}
