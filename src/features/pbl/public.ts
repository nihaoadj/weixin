import { getApplicationServices } from '@/bootstrap/wiring'
import type {
  InteractionStyle,
  PblRepository,
  PblFilters,
  PblSession,
  PblSuggestion,
  PblTargets,
  PblWorkStatus,
} from './domain/ports'
export type * from './domain/ports'
const pbl = (): PblRepository => getApplicationServices().pbl
export const getStudentClasses = () => pbl().classes()
export const getLearningDialogues = (limit = 20, offset = 0) => pbl().dialogues(limit, offset)
export const getLearningDialogue = (id: string) => pbl().dialogue(id)
export const createLearningDialogue = (input: {
  clientSessionId: string
  classId?: string
  interactionStyle: InteractionStyle
  goalPointCodes: string[]
}) => pbl().createDialogue(input)
export const startLearningDialogue = (id: string, interactionStyle: InteractionStyle) =>
  pbl().startDialogue(id, interactionStyle)
export const getLearningDialogueSubmission = (id: string) => pbl().dialogueSubmission(id)
export const submitLearningDialogue = (input: {
  id: string
  snapshotId: string
  classId: string
  clientSubmissionId: string
}) => pbl().submitDialogue(input)
export const getActivePblSessions = () => pbl().active()
export const getTeacherPblSessions = (classId: string) => pbl().sessions(classId)
export const createPblSession = (classId: string, topicCode: string, caseId: string, goals: string[]) =>
  pbl().createSession(classId, topicCode, caseId, goals)
export const closePblSession = (classId: string, id: string) => pbl().closeSession(classId, id)
export const getPblParticipation = (id: string) => pbl().participation(id)
export const createPblMessageId = () => `${Date.now()}-${Math.random().toString(36).slice(2)}`
export const sendPblMessage = (id: string, content: string, clientMessageId: string) =>
  pbl().message(id, content, clientMessageId)
export const getTeacherPblDiagnostics = (filters?: PblFilters) => pbl().diagnostics(filters)
export const getTeacherPblWorkItems = (
  filters?: PblFilters & { source?: 'student_submission' | 'classroom_diagnostic'; workStatus?: PblWorkStatus },
) => pbl().workItems(filters)
export const getTeacherPblWorkItem = (snapshotId: string) => pbl().workItem(snapshotId)
export const sendTeacherPblFeedback = (input: Parameters<PblRepository['feedback']>[0]) => pbl().feedback(input)
export const getTeacherPblSessionPage = (filters?: Parameters<PblRepository['teacherSessions']>[0]) =>
  pbl().teacherSessions(filters)
export const getTeacherPblDashboard = (classId: string, sessionId: string) => pbl().dashboard(classId, sessionId)
export const getTeacherPblFollowUps = (filters?: Parameters<PblRepository['followUps']>[0]) => pbl().followUps(filters)
export const getTeacherPblFollowUp = (planId: number) => pbl().followUp(planId)
export const sendTeacherPblFollowUpFeedback = (planId: number, clientFeedbackId: string, body: string) =>
  pbl().followUpFeedback(planId, clientFeedbackId, body)
export const getTeacherPblDiagnostic = (id: string) => pbl().diagnostic(id)
export const getPblDiagnosticRevisions = (id: string) => pbl().revisions(id)
export const editPblSuggestion = (item: PblSuggestion, reject = false) => pbl().editSuggestion(item, reject)
export const adoptPblSuggestion = (item: PblSuggestion, targets?: PblTargets) => pbl().adopt(item, targets)
export const getPblLearningPlans = () => pbl().plans()
export const getPblLearningReports = (limit = 20, offset = 0) => pbl().reports(limit, offset)
export const getPblLearningReport = (sessionId: string) => pbl().report(sessionId)
export const getPblLearningResults = (sessionId?: string) => pbl().results(sessionId)
export const submitPblTask = (
  taskId: number,
  submissionId: string,
  answer: { text?: string; selected_option?: number },
) => pbl().submitTask(taskId, submissionId, answer)
export const getPblSummary = (session: PblSession) => pbl().summary(session)
