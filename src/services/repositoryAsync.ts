import { apiRequest, isRemoteApiEnabled } from '@/services/apiClient'
import * as localRepository from '@/services/repository'
import type { ChatMessage, Conversation, Problem, QuestionThread, Report, StudentQuestion } from '@/types/domain'
import { AppError } from '@/types/errors'

interface ApiMessage {
  id: number
  role: ChatMessage['role']
  content: string
  created_at: string
}

interface ApiConversation {
  id: number
  client_id: string
  student_id: number
  created_at: string
  updated_at: string
  messages: ApiMessage[]
}

interface ApiReport {
  id: number
  conversation_id: number
  conversation_client_id?: string
  student_id: number
  student_name?: string
  status: 'draft' | 'pending_review' | 'reviewed'
  ai_score: number
  ai_summary: string
  analysis?: {
    errors?: Array<{ content: string; suggestion: string }>
    strengths?: string[]
    general_suggestions?: string[]
  } | null
  messages: ApiMessage[]
  teacher_score?: number | null
  teacher_feedback?: string | null
  created_at: string
  updated_at: string
}

interface ApiProblem {
  id: number
  type: string
  title: string
  description: string
  target: Problem['target']
  target_label: string
  target_ids: string[]
  status: 'draft' | 'published' | 'rejected'
  created_at: string
  published_at?: string | null
  answer_count: number
  content_type?: 'question' | 'guided_case'
  slug?: string | null
  specialty?: string
  difficulty?: 'basic' | 'intermediate' | 'advanced'
  estimated_minutes?: number
  version?: number
  parent_problem_id?: number | null
  opening?: { setting: string; patient_intro: string; chief_complaint: string } | null
  author_id?: number | null
  medical_review_status?: 'not_submitted' | 'pending' | 'approved' | 'rejected'
  capability_tags?: string[]
}

interface ApiQuestionThread {
  question_id: number
  messages: ApiMessage[]
  updated_at: string
}

type ReportDraftInput = Omit<Report, 'studentId' | 'studentName' | 'status'>

const localReportStatus = {
  draft: '草稿',
  pending_review: '待批阅',
  reviewed: '已批阅',
} as const

const localProblemStatus = {
  draft: '待审核',
  published: '已发布',
  rejected: '已拒绝',
} as const

function toApiProblemStatus(status: Problem['status']): ApiProblem['status'] {
  if (status === '已发布') return 'published'
  if (status === '已拒绝') return 'rejected'
  return 'draft'
}

function toChatMessage(message: ApiMessage): ChatMessage {
  return {
    id: String(message.id),
    role: message.role,
    content: message.content,
    timestamp: message.created_at,
  }
}

function toConversation(conversation: ApiConversation): Conversation {
  return {
    conversationId: conversation.client_id,
    messages: conversation.messages.map(toChatMessage),
    createdAt: conversation.created_at,
    updatedAt: conversation.updated_at,
  }
}

function toReport(report: ApiReport): Report {
  const analysis = report.analysis
  return {
    id: String(report.id),
    conversationId: report.conversation_client_id || String(report.conversation_id),
    messages: report.messages.map(toChatMessage),
    analysis: {
      errors: analysis?.errors || [],
      strengths: analysis?.strengths?.length ? analysis.strengths : report.ai_summary ? [report.ai_summary] : [],
      generalSuggestions: analysis?.general_suggestions || [],
      score: report.ai_score,
      summary: report.ai_summary,
    },
    createdAt: report.created_at,
    studentId: String(report.student_id),
    studentName: report.student_name || '学生',
    status: localReportStatus[report.status],
    teacherScore: report.teacher_score ?? undefined,
    teacherFeedback: report.teacher_feedback ?? undefined,
  }
}

function toProblem(problem: ApiProblem): Problem {
  return {
    id: String(problem.id),
    type: problem.type as Problem['type'],
    title: problem.title,
    description: problem.description,
    target: problem.target,
    targetIds: problem.target_ids,
    targetLabel: problem.target_label,
    status: localProblemStatus[problem.status],
    time: problem.created_at,
    publishTime: problem.published_at || undefined,
    answerCount: problem.answer_count,
    contentType: problem.content_type || 'question',
    slug: problem.slug || undefined,
    specialty: problem.specialty || undefined,
    difficulty: problem.difficulty || undefined,
    estimatedMinutes: problem.estimated_minutes,
    version: problem.version,
    parentProblemId: problem.parent_problem_id ?? undefined,
    authorId: problem.author_id ?? undefined,
    medicalReviewStatus: problem.medical_review_status,
    capabilityTags: problem.capability_tags || [],
    opening: problem.opening
      ? {
          setting: problem.opening.setting,
          patientIntro: problem.opening.patient_intro,
          chiefComplaint: problem.opening.chief_complaint,
        }
      : undefined,
  }
}

function toApiProblemPayload(problem: Problem) {
  return {
    type: problem.type,
    title: problem.title,
    description: problem.description,
    target: problem.target,
    target_label: problem.targetLabel || problem.className || '全体学生',
    target_ids: problem.target === 'all' ? [] : problem.targetIds || [],
    status: toApiProblemStatus(problem.status),
  }
}

function undefinedOnNotFound<T>(error: unknown): T | undefined {
  if (error instanceof AppError && error.statusCode === 404) return undefined
  throw error
}

async function upsertRemoteConversation(conversation: Conversation): Promise<ApiConversation> {
  return apiRequest<ApiConversation>({
    path: '/conversations',
    method: 'POST',
    body: {
      client_id: conversation.conversationId,
      messages: conversation.messages.map(({ role, content }) => ({ role, content })),
    },
  })
}

export async function getConversationsAsync(): Promise<Conversation[]> {
  if (!isRemoteApiEnabled()) return localRepository.getConversations()
  const conversations = await apiRequest<ApiConversation[]>({ path: '/conversations' })
  return conversations.map(toConversation)
}

export async function findConversationAsync(conversationId: string): Promise<Conversation | undefined> {
  if (!isRemoteApiEnabled()) return localRepository.findConversation(conversationId)
  return (await getConversationsAsync()).find((conversation) => conversation.conversationId === conversationId)
}

export async function upsertConversationAsync(conversation: Conversation): Promise<void> {
  if (!isRemoteApiEnabled()) {
    localRepository.upsertConversation(conversation)
    return
  }
  await upsertRemoteConversation(conversation)
}

export async function getReportsAsync(): Promise<Report[]> {
  if (!isRemoteApiEnabled()) return localRepository.getReports()
  const reports = await apiRequest<ApiReport[]>({ path: '/reports' })
  return reports.map(toReport)
}

export async function findReportAsync(conversationIdOrReportId: string): Promise<Report | undefined> {
  if (!isRemoteApiEnabled()) return localRepository.findReport(conversationIdOrReportId)
  return (await getReportsAsync()).find(
    (report) => report.conversationId === conversationIdOrReportId || report.id === conversationIdOrReportId,
  )
}

export async function saveDraftReportAsync(input: ReportDraftInput): Promise<Report> {
  if (!isRemoteApiEnabled()) return localRepository.saveDraftReport(input)
  const conversation = await upsertRemoteConversation({
    conversationId: input.conversationId,
    messages: input.messages,
    createdAt: input.createdAt,
    updatedAt: new Date().toISOString(),
  })
  const report = await apiRequest<ApiReport>({
    path: '/reports',
    method: 'POST',
    body: {
      conversation_id: conversation.id,
      ai_score: input.analysis.score,
      ai_summary: input.analysis.summary,
      analysis: {
        errors: input.analysis.errors,
        strengths: input.analysis.strengths || [],
        general_suggestions: input.analysis.generalSuggestions || [],
      },
    },
  })
  return toReport(report)
}

export async function submitReportForReviewAsync(conversationId: string): Promise<Report | null> {
  if (!isRemoteApiEnabled()) return localRepository.submitReportForReview(conversationId)
  const report = await findReportAsync(conversationId)
  if (!report?.id) return null
  const submitted = await apiRequest<ApiReport>({
    path: `/reports/${report.id}/submit`,
    method: 'POST',
  })
  return toReport(submitted)
}

export async function reviewReportAsync(
  conversationIdOrReportId: string,
  score: number,
  feedback: string,
): Promise<Report | null> {
  if (!isRemoteApiEnabled()) return localRepository.reviewReport(conversationIdOrReportId, score, feedback)
  const report = await findReportAsync(conversationIdOrReportId)
  if (!report?.id) return null
  const reviewed = await apiRequest<ApiReport>({
    path: `/reports/${report.id}/review`,
    method: 'POST',
    body: {
      teacher_score: score,
      teacher_feedback: feedback,
    },
  })
  return toReport(reviewed)
}

export function getProblemsAsync(): Promise<Problem[]> {
  if (!isRemoteApiEnabled()) return Promise.resolve(localRepository.getProblems())
  return apiRequest<ApiProblem[]>({ path: '/problems' }).then((problems) => problems.map(toProblem))
}

export function findProblemAsync(id: string): Promise<Problem | undefined> {
  if (!isRemoteApiEnabled()) return Promise.resolve(localRepository.findProblem(id))
  return apiRequest<ApiProblem>({ path: `/problems/${id}` })
    .then(toProblem)
    .catch((error) => undefinedOnNotFound<Problem>(error))
}

export function saveProblemsAsync(problems: Problem[]): Promise<void> {
  if (isRemoteApiEnabled()) return Promise.reject(new Error('API 模式不支持批量覆盖问题数据'))
  localRepository.saveProblems(problems)
  return Promise.resolve()
}

export async function upsertProblemAsync(problem: Problem): Promise<Problem> {
  if (!isRemoteApiEnabled()) {
    localRepository.upsertProblem(problem)
    return problem
  }
  const numericId = Number(problem.id)
  const payload = toApiProblemPayload(problem)
  const saved = Number.isFinite(numericId)
    ? await apiRequest<ApiProblem>({ path: `/problems/${numericId}`, method: 'PUT', body: payload })
    : await apiRequest<ApiProblem>({ path: '/problems', method: 'POST', body: payload })
  return toProblem(saved)
}

export async function publishProblemAsync(id: string): Promise<Problem | null> {
  if (!isRemoteApiEnabled()) {
    const problem = localRepository.findProblem(id)
    if (!problem) return null
    const updated = { ...problem, status: '已发布' as const, publishTime: new Date().toISOString().slice(0, 10) }
    localRepository.upsertProblem(updated)
    return updated
  }
  const problem = await apiRequest<ApiProblem>({ path: `/problems/${id}/publish`, method: 'POST' })
  return toProblem(problem)
}

export async function rejectProblemAsync(id: string): Promise<Problem | null> {
  if (!isRemoteApiEnabled()) {
    const problem = localRepository.findProblem(id)
    if (!problem) return null
    const updated = { ...problem, status: '已拒绝' as const }
    localRepository.upsertProblem(updated)
    return updated
  }
  const problem = await apiRequest<ApiProblem>({ path: `/problems/${id}/reject`, method: 'POST' })
  return toProblem(problem)
}

export function resetProblemsAsync(): Promise<Problem[]> {
  if (isRemoteApiEnabled()) return Promise.reject(new Error('API 模式不支持恢复本地示例数据'))
  return Promise.resolve(localRepository.resetProblems())
}

export function getStudentQuestionsAsync(): Promise<StudentQuestion[]> {
  if (!isRemoteApiEnabled()) return Promise.resolve(localRepository.getStudentQuestions())
  return getProblemsAsync().then(async (problems) => {
    const threads = await Promise.all(problems.map((problem) => getQuestionThreadAsync(problem.id)))
    const answered = new Set(threads.filter(Boolean).map((thread) => thread?.questionId))
    return problems
      .filter((problem) => problem.status === '已发布')
      .map((problem) => ({
        id: problem.id,
        type: problem.type,
        title: problem.title,
        description: problem.description,
        time: problem.publishTime || problem.time,
        status: answered.has(problem.id) ? ('已回答' as const) : ('未回答' as const),
      }))
  })
}

export function findStudentQuestionAsync(id: string): Promise<StudentQuestion | undefined> {
  if (!isRemoteApiEnabled()) return Promise.resolve(localRepository.findStudentQuestion(id))
  return findProblemAsync(id).then((problem) =>
    problem && problem.status === '已发布'
      ? {
          id: problem.id,
          type: problem.type,
          title: problem.title,
          description: problem.description,
          time: problem.publishTime || problem.time,
          status: '未回答',
        }
      : undefined,
  )
}

export function getQuestionThreadAsync(questionId: string): Promise<QuestionThread | undefined> {
  if (!isRemoteApiEnabled()) return Promise.resolve(localRepository.getQuestionThread(questionId))
  return apiRequest<ApiQuestionThread>({ path: `/problems/${questionId}/thread` })
    .then((thread) => ({
      questionId: String(thread.question_id),
      messages: thread.messages.map(toChatMessage),
      updatedAt: thread.updated_at,
    }))
    .catch((error) => undefinedOnNotFound<QuestionThread>(error))
}

export function saveQuestionThreadAsync(thread: QuestionThread): Promise<void> {
  if (!isRemoteApiEnabled()) {
    localRepository.saveQuestionThread(thread)
    return Promise.resolve()
  }
  return apiRequest<ApiQuestionThread>({
    path: `/problems/${thread.questionId}/thread`,
    method: 'POST',
    body: {
      messages: thread.messages.map(({ role, content }) => ({ role, content })),
    },
  }).then(() => undefined)
}
