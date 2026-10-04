import { getApplicationServices } from '@/bootstrap/wiring'
import type { InteractionStyle, PblRepository } from './domain/ports'
export type * from './domain/ports'
const pbl = (): PblRepository => getApplicationServices().pbl
export const getLearningDialogues = (limit = 20, offset = 0) => pbl().dialogues(limit, offset)
export const getLearningDialogue = (id: string) => pbl().dialogue(id)
export const createLearningDialogue = (input: {
  clientSessionId: string
  interactionStyle: InteractionStyle
  goalPointCodes: string[]
}) => pbl().createDialogue(input)
export const startLearningDialogue = (id: string, interactionStyle: InteractionStyle) =>
  pbl().startDialogue(id, interactionStyle)
export const getLearningDialogueSubmission = (id: string) => pbl().dialogueSubmission(id)
export const getActivePblSessions = () => pbl().active()
export const getTeacherPblSessions = (classId: string) => pbl().sessions(classId)
export const createPblSession = (classId: string, topicCode: string, caseId: string, goals: string[]) =>
  pbl().createSession(classId, topicCode, caseId, goals)
export const closePblSession = (classId: string, id: string) => pbl().closeSession(classId, id)
export const getPblParticipation = (id: string) => pbl().participation(id)
export const createPblMessageId = () => `${Date.now()}-${Math.random().toString(36).slice(2)}`
export const sendPblMessage = (
  id: string,
  content: string,
  clientMessageId: string,
  interactionStyle: InteractionStyle,
) => pbl().message(id, content, clientMessageId, interactionStyle)
export const getTeacherPblWorkItem = (snapshotId: string) => pbl().workItem(snapshotId)
export const getTeacherPblSessionPage = (filters?: Parameters<PblRepository['teacherSessions']>[0]) =>
  pbl().teacherSessions(filters)
export const getTeacherPblDashboard = (classId: string, sessionId: string) => pbl().dashboard(classId, sessionId)
export const getTeacherPblDiagnostic = (id: string) => pbl().diagnostic(id)
export const getPblDiagnosticRevisions = (id: string) => pbl().revisions(id)
export const getPblLearningPlans = () => pbl().plans()
export const getPblLearningReports = (limit = 20, offset = 0) => pbl().reports(limit, offset)
export const getPblLearningReport = (sessionId: string) => pbl().report(sessionId)
export const submitPblTask = (
  taskId: number,
  submissionId: string,
  answer: { text?: string; selected_option?: number },
) => pbl().submitTask(taskId, submissionId, answer)
