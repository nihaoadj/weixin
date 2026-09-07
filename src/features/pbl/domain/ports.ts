export type PblPhase = 'problem_framing' | 'hypothesis' | 'evidence' | 'synthesis' | 'completed'
export type InteractionStyle = 'guided' | 'direct'
export type PblSessionKind = 'classroom' | 'student_initiated'
export type StudentClassSummary = { id: string; name: string; code: string }
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
  studentPhase?: PblPhase
  phaseStatus?: 'active' | 'completed'
  phaseCounts?: Partial<Record<PblPhase, number>>
  version: number
  sessionKind: PblSessionKind
  interactionStyle?: InteractionStyle
  styleSelectedAt?: string
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
  phase?: Exclude<PblPhase, 'completed'>
  phaseDecision?: 'continue' | 'advance' | 'complete' | 'unavailable'
  phaseEvidenceSummary?: string
  phaseMissingElements?: string[]
  sessionKind?: PblSessionKind
  interactionStyle?: InteractionStyle
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
export type PblParticipation = {
  messages: PblMessage[]
  diagnostic?: PblDiagnostic
  currentPhase: PblPhase
  phaseStartedRevision: number
  phaseStatus: 'active' | 'completed'
  phaseCompletedAt?: string
  interactionStyle: InteractionStyle
  styleSelectedAt?: string
}
export type LearningDialogue = { session: PblSession; participation?: PblParticipation }
export type LearningDialoguePage = { items: PblSession[]; total: number; limit: number; offset: number }
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
    answer: { text?: string; selected_option?: number; dimension_scores?: Record<string, number> }
    submitted_at: string | null
  } | null
  cycle_number: number
  target_type: string
  target_code: string
  variant_code: string
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
  current_cycle: number
  max_cycles: number
  automation_exhausted: boolean
  decision_policy_version: string
  decision_basis: {
    result?: string
    cycle?: number
    offline_support_required?: boolean
    failed_targets?: Array<{ target_type: string; target_code: string }>
    checks?: Array<{
      target_type: string
      target_code: string
      threshold: number | null
      score: number | null
      evidence_present: boolean
      passed: boolean
    }>
  }
  evaluated_at: string | null
  evaluations?: PblCycleEvaluation[]
}
export type PblCycleCheck = {
  target_type: string
  target_code: string
  label?: string
  threshold: number | null
  score: number | null
  evidence_present: boolean
  passed: boolean
}
export type PblCycleEvaluation = {
  cycle_number: number
  policy_version: string
  result: string
  checks: PblCycleCheck[]
  failed_targets: Array<{ target_type: string; target_code: string; label?: string }>
  automation_exhausted: boolean
  record_source: string
  evaluated_at: string
}
export type PblReportStatus =
  'discussing' | 'awaiting_learning' | 'learning_cycle_1' | 'learning_cycle_2' | 'improved' | 'support_needed'
export type PblReportSession = {
  id: string
  topicCode: string
  topicLabel: string
  caseTitle: string
  status: string
  createdAt: string
  closedAt?: string
}
export type PblReportAction = { kind: 'discussion' | 'tasks' | 'none'; label: string }
export type PblReportListItem = {
  session: PblReportSession
  status: PblReportStatus
  currentPhase?: PblPhase
  phaseStatus?: 'active' | 'completed'
  knowledgeGapCount: number
  reasoningIssueCount: number
  taskProgress: { completed: number; total: number }
  summaryText: string
  nextAction: PblReportAction
  updatedAt: string
}
export type PblReportPage = {
  summary: {
    totalReports: number
    statusCounts: Record<PblReportStatus, number>
    recurringTargets: Array<{ targetType: string; targetCode: string; label: string; occurrences: number }>
    nextAction?: PblReportAction & { sessionId: string; caseTitle: string }
  }
  items: PblReportListItem[]
  total: number
  limit: number
  offset: number
}
export type PblLearningReport = {
  session: PblReportSession
  status: PblReportStatus
  currentPhase?: PblPhase
  phaseStatus?: 'active' | 'completed'
  phaseProgress: Array<{
    phase: Exclude<PblPhase, 'completed'>
    label: string
    state: 'completed' | 'current' | 'pending'
    evidenceSummary: string
    missingElements: string[]
    evidencedAt?: string
  }>
  diagnosis: {
    createdAt?: string
    knowledgeGaps: Array<{
      id: string
      pointCode: string
      label: string
      summary: string
      confidence: string
      evidenceSummary: string
    }>
    reasoningIssues: Array<{
      id: string
      dimensionId: string
      label: string
      summary: string
      issueType: string
      improvement: string
      evidenceSummary: string
    }>
  }
  plans: Array<{
    id: number
    assignmentBasis: 'personal' | 'classroom'
    status: string
    verificationStatus: string
    currentCycle: number
    maxCycles: number
    automationExhausted: boolean
    decisionPolicyVersion: string
    dueAt: string
    createdAt: string
    tasks: Array<{
      id: number
      taskType: string
      status: string
      cycleNumber: number
      targetType: string
      targetCode: string
      targetLabel: string
      prompt: string
      score: number | null
      feedback: string
      evidencePresent: boolean
      submittedAt?: string
    }>
    evaluations: PblCycleEvaluation[]
  }>
  targetProgress: Array<{
    planId: number
    targetType: string
    targetCode: string
    label: string
    cycles: Array<PblCycleCheck & { cycleNumber: number }>
  }>
  taskProgress: { completed: number; total: number }
  summaryText: string
  nextAction: PblReportAction
  timeline: Array<{ type: string; label: string; cycleNumber?: number; occurredAt: string }>
  updatedAt: string
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
  phase_counts: Partial<Record<PblPhase, number>>
  automation_exhausted: number
}
export interface PblRepository {
  classes(): Promise<StudentClassSummary[]>
  dialogues(limit?: number, offset?: number): Promise<LearningDialoguePage>
  dialogue(id: string): Promise<LearningDialogue>
  createDialogue(input: {
    clientSessionId: string
    classId: string
    interactionStyle: InteractionStyle
    goalPointCodes: string[]
  }): Promise<LearningDialogue>
  startDialogue(id: string, interactionStyle: InteractionStyle): Promise<LearningDialogue>
  active(): Promise<PblSession[]>
  sessions(classId: string): Promise<PblSession[]>
  createSession(classId: string, topicCode: string, caseId: string, goals: string[]): Promise<PblSession>
  closeSession(classId: string, id: string): Promise<PblSession>
  participation(id: string): Promise<PblParticipation>
  message(id: string, content: string, clientMessageId: string): Promise<PblParticipation>
  diagnostics(filters?: PblFilters): Promise<{ items: PblDiagnostic[]; total: number }>
  diagnostic(id: string): Promise<PblDiagnostic>
  revisions(id: string): Promise<PblDiagnostic[]>
  editSuggestion(item: PblSuggestion, reject?: boolean): Promise<PblSuggestion>
  adopt(item: PblSuggestion, targets?: PblTargets): Promise<PblSuggestion>
  plans(): Promise<PblPlan[]>
  reports(limit?: number, offset?: number): Promise<PblReportPage>
  report(sessionId: string): Promise<PblLearningReport>
  results(sessionId?: string): Promise<PblPlan[]>
  submitTask(
    taskId: number,
    submissionId: string,
    answer: { text?: string; selected_option?: number },
  ): Promise<PblPlan>
  summary(session: PblSession): Promise<PblSummary>
}
