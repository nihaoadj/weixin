export type PblPhase = 'problem_framing' | 'hypothesis' | 'evidence' | 'synthesis'
export type PblSession = {
  id: string
  classId: string
  topicCode: string
  status: string
  createdAt?: string
  closedAt?: string
  caseId?: string
  caseVersion?: number
  caseContext?: { title: string; opening?: { setting: string; patient_intro: string; chief_complaint: string } }
  goalPointCodes: string[]
  phase: PblPhase
  version: number
}
export type PblFinding = { id: string; summary: string; evidence_message_ids: string[]; evidence_summary: string }
export type KnowledgeGap = PblFinding & { point_code: string; confidence: 'low' | 'medium' | 'high' }
export type ReasoningIssue = PblFinding & { dimension_id: string; issue_type: string; improvement: string }
export type PblDiagnostic = {
  id?: string
  revision?: number
  diagnosticStatus: string
  assistantReply: string
  followUpQuestion?: string
  knowledgeGaps: KnowledgeGap[]
  reasoningIssues: ReasoningIssue[]
  recommendedQuestions?: PblSuggestion[]
  schemaVersion?: number
  safetyNotice?: string
  createdAt?: string
  studentId?: string
  studentName?: string
  classId?: string
  className?: string
  sessionId?: string
  topicCode?: string
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
export type PblMessage = {
  id: string
  sequence: number
  role: string
  content: string
  processing_status?: string
  client_message_id?: string | null
}
export type PblParticipation = { messages: PblMessage[]; diagnostic?: PblDiagnostic }
export type PblFilters = { classId?: string; sessionId?: string; studentId?: string; status?: string; offset?: number }
export type PblTargets = { studentIds?: number[]; wholeClass?: boolean; includeCaseRetry?: boolean }
export type PblTask = {
  id: number
  position: number
  task_type: 'discussion' | 'knowledge_review' | 'retest' | 'micro_drill' | 'focused_retry'
  status: string
  problem_id: number | null
  public_definition: { prompt: string; options?: string[]; point_code?: string; card_code?: string; reference?: string }
  result: {
    score: number | null
    feedback: string
    evidence: string[]
    answer: { text?: string; selected_option?: number }
    submitted_at: string | null
  } | null
}
export type PblPlan = {
  id: number
  student_id: number
  source_type: 'pbl_suggestion'
  source_id: number
  source_context: {
    teacher_id: number
    class_id: number
    class_name: string
    session_id: number
    snapshot_id: number
    suggestion_id: number
    point_codes: string[]
    dimension_ids: string[]
    topic_code: string
  }
  status: string
  verification_status: 'not_ready' | 'pending_teacher' | 'improved' | 'needs_reinforcement'
  verification_note: string
  verified_at: string | null
  version: number
  due_at: string
  tasks: PblTask[]
}
export type PblSummary = {
  participants: number
  diagnoses: number
  published_suggestions: number
  plans: number
  tasks: number
  completed_tasks: number
  pending_verification: number
  improved: number
  needs_reinforcement: number
  objective_retest_count: number
  objective_retest_average: number | null
}
export interface PblRepository {
  active(): Promise<PblSession[]>
  sessions(classId: string): Promise<PblSession[]>
  createSession(classId: string, topicCode: string, caseId: string, goals: string[]): Promise<PblSession>
  closeSession(classId: string, id: string): Promise<PblSession>
  phase(item: PblSession, phase: PblPhase): Promise<PblSession>
  participation(id: string): Promise<PblParticipation>
  message(id: string, content: string, clientMessageId: string): Promise<PblParticipation>
  diagnostics(filters?: PblFilters): Promise<{ items: PblDiagnostic[]; total: number }>
  diagnostic(id: string): Promise<PblDiagnostic>
  revisions(id: string): Promise<PblDiagnostic[]>
  editSuggestion(item: PblSuggestion, reject?: boolean): Promise<PblSuggestion>
  adopt(item: PblSuggestion, targets?: PblTargets): Promise<PblSuggestion>
  plans(): Promise<PblPlan[]>
  results(sessionId?: string): Promise<PblPlan[]>
  submitTask(
    taskId: number,
    submissionId: string,
    answer: { text?: string; selected_option?: number },
  ): Promise<PblPlan>
  verify(plan: PblPlan, decision: 'improved' | 'needs_reinforcement', note: string): Promise<PblPlan>
  summary(session: PblSession): Promise<PblSummary>
}
