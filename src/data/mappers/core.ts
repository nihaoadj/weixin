import type { ApiMessage, ApiConversation, ApiReport, ApiProblem, ApiQuestionThread } from '@/data/contracts/core'
import { apiProblemSchema } from '@/data/contracts/core'
import type { ChatMessage, Conversation, Report, Problem, QuestionThread } from '@/types/records'
import { AppError } from '@/types/errors'
import { reportLabels, problemLabels } from './status'
const reportStatus = reportLabels

const problemStatus = problemLabels

export function toChatMessage(message: ApiMessage): ChatMessage {
  if (message.role !== 'user' && message.role !== 'assistant') {
    throw new AppError('消息角色不符合领域契约', { code: 'CONTRACT_ERROR' })
  }
  return { id: String(message.id), role: message.role, content: message.content, timestamp: message.created_at }
}

export function toConversation(conversation: ApiConversation): Conversation {
  return {
    conversationId: conversation.client_id,
    messages: (conversation.messages || []).map(toChatMessage),
    createdAt: conversation.created_at,
    updatedAt: conversation.updated_at,
  }
}

export function toReport(report: ApiReport): Report {
  const status = report.status as keyof typeof reportStatus
  if (!(status in reportStatus)) throw new AppError('报告状态不符合领域契约', { code: 'CONTRACT_ERROR' })
  return {
    id: String(report.id),
    conversationId: report.conversation_client_id || String(report.conversation_id),
    messages: (report.messages || []).map(toChatMessage),
    analysis: {
      errors: (report.analysis?.errors || []).map((item) => ({
        content: item.content,
        suggestion: item.suggestion || '',
      })),
      strengths: report.analysis?.strengths?.length
        ? report.analysis.strengths
        : report.ai_summary
          ? [report.ai_summary]
          : [],
      generalSuggestions: report.analysis?.general_suggestions || [],
      score: report.ai_score,
      summary: report.ai_summary,
    },
    createdAt: report.created_at,
    updatedAt: report.updated_at,
    studentId: String(report.student_id),
    studentName: report.student_name || '学生',
    status,
    teacherScore: report.teacher_score ?? undefined,
    teacherFeedback: report.teacher_feedback ?? undefined,
  }
}

export function toProblem(dto: ApiProblem): Problem {
  const problem = apiProblemSchema.parse(dto)
  const status = problem.status as keyof typeof problemStatus
  if (!(status in problemStatus)) throw new AppError('题目状态不符合领域契约', { code: 'CONTRACT_ERROR' })
  return {
    id: String(problem.id),
    type: problem.type,
    title: problem.title,
    description: problem.description || '',
    target: problem.target,
    targetIds: problem.target_ids || [],
    targetLabel: problem.target_label,
    status,
    time: problem.created_at,
    publishTime: problem.published_at || undefined,
    answerCount: problem.answer_count || 0,
    contentType: problem.content_type,
    slug: problem.slug || undefined,
    specialty: problem.specialty || undefined,
    difficulty: problem.difficulty,
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

export function toThread(thread: ApiQuestionThread): QuestionThread {
  return {
    questionId: String(thread.question_id),
    messages: (thread.messages || []).map(toChatMessage),
    updatedAt: thread.updated_at,
  }
}

export function undefinedOnNotFound<T>(error: unknown): T | undefined {
  if (error instanceof AppError && error.statusCode === 404) return undefined
  throw error
}

export function problemPayload(problem: Problem) {
  return {
    type: problem.type,
    title: problem.title,
    description: problem.description,
    target: problem.target,
    target_label: problem.targetLabel || problem.className || '全体学生',
    target_ids: problem.target === 'all' ? [] : problem.targetIds || [],
    status: problem.status,
  }
}
