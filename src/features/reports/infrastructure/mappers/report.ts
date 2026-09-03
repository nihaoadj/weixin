import type { ApiReport } from '@/platform/contracts/core'
import { toChatMessage } from '@/platform/mappers/messages'
import type { Report } from '@/types/records'
import { AppError } from '@/types/errors'
import { reportLabels } from '@/shared/mappers/status'

export function toReport(report: ApiReport): Report {
  const status = report.status as keyof typeof reportLabels
  if (!(status in reportLabels)) throw new AppError('报告状态不符合领域契约', { code: 'CONTRACT_ERROR' })
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
    reviewTopicCodes: report.review_topic_codes || [],
  }
}
