import { getCoreRepository } from '@/data/repositories/container'
import type { ReportDraftInput } from '@/data/repositories/core'
import type { Conversation, Problem, QuestionThread } from '@/types/domain'

import {
  fromProblemView,
  toProblemView,
  toReportView,
  toQuestionView,
  toConversationSummaryView,
  toReportSummaryView,
  optional,
  nullable,
} from '@/data/mappers/presentation'

const repository = getCoreRepository()
export const findReportByConversationAsync = async (id: string) =>
  optional(await repository.findReportByConversation(id), toReportView)

export const getConversationsAsync = () => repository.getConversations()
export const getConversationSummariesAsync = async (limit = 20, offset = 0) => {
  const page = await repository.getConversationSummaries(limit, offset)
  return { ...page, items: page.items.map(toConversationSummaryView) }
}
export const findConversationAsync = (conversationId: string) => repository.findConversation(conversationId)
export const upsertConversationAsync = (conversation: Conversation) => repository.upsertConversation(conversation)
export const getReportsAsync = async () => (await repository.getReports()).map(toReportView)
export const getReportSummariesAsync = async (limit = 20, offset = 0) => {
  const page = await repository.getReportSummaries(limit, offset)
  return { ...page, items: page.items.map(toReportSummaryView) }
}
export const findReportAsync = async (conversationIdOrReportId: string) =>
  optional(await repository.findReport(conversationIdOrReportId), toReportView)
export const saveDraftReportAsync = async (input: ReportDraftInput) =>
  toReportView(await repository.saveDraftReport(input))
export const submitReportForReviewAsync = async (conversationId: string) =>
  nullable(await repository.submitReportForReview(conversationId), toReportView)
export const reviewReportAsync = async (conversationIdOrReportId: string, score: number, feedback: string) =>
  nullable(await repository.reviewReport(conversationIdOrReportId, score, feedback), toReportView)
export const getProblemsAsync = async () => (await repository.getProblems()).map(toProblemView)
export const findProblemAsync = async (id: string) => optional(await repository.findProblem(id), toProblemView)
export const saveProblemsAsync = (problems: Problem[]) => repository.saveProblems(problems.map(fromProblemView))
export const upsertProblemAsync = async (problem: Problem) =>
  toProblemView(await repository.upsertProblem(fromProblemView(problem)))
export const publishProblemAsync = async (id: string) => nullable(await repository.publishProblem(id), toProblemView)
export const rejectProblemAsync = async (id: string) => nullable(await repository.rejectProblem(id), toProblemView)
export const resetProblemsAsync = async () => (await repository.resetProblems()).map(toProblemView)
export const getStudentQuestionsAsync = async () => (await repository.getStudentQuestions()).map(toQuestionView)
export const findStudentQuestionAsync = async (id: string) =>
  optional(await repository.findStudentQuestion(id), toQuestionView)
export const getQuestionThreadAsync = (questionId: string) => repository.getQuestionThread(questionId)
export const saveQuestionThreadAsync = (thread: QuestionThread) => repository.saveQuestionThread(thread)
