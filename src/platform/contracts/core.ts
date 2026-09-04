import { z } from 'zod'
import type { components } from '@/data/contracts/openapi.generated'

export type ApiMessage = components['schemas']['MessageRead']
export type ApiConversation = components['schemas']['ConversationRead']
export type ApiConversationSummaryPage = components['schemas']['ConversationSummaryPage']
export type ApiReport = components['schemas']['ReportRead']
export type ApiReportSummaryPage = components['schemas']['ReportSummaryPage']
export type ApiProblem = components['schemas']['ProblemRead']
export type ApiQuestionThread = components['schemas']['QuestionThreadRead']
export type ApiStudentQuestion = components['schemas']['StudentQuestionRead']

const timestamp = z.string().min(1)
const apiMessageSchema = z.object({
  id: z.number().int(),
  role: z.enum(['user', 'assistant']),
  content: z.string(),
  created_at: timestamp,
})

const analysisIssueSchema = z.object({ content: z.string(), suggestion: z.string().optional().default('') })
const reportAnalysisSchema = z.object({
  errors: z.array(analysisIssueSchema).optional().default([]),
  strengths: z.array(z.string()).optional().default([]),
  general_suggestions: z.array(z.string()).optional().default([]),
})

export const apiConversationSchema = z.object({
  id: z.number().int(),
  client_id: z.string().min(1),
  student_id: z.number().int(),
  created_at: timestamp,
  updated_at: timestamp,
  messages: z.array(apiMessageSchema).optional().default([]),
  topic_codes: z.array(z.string().min(1)).max(3).optional().default([]),
})

export const apiConversationListSchema = z.array(apiConversationSchema)

const conversationSummarySchema = z.object({
  id: z.number().int(),
  client_id: z.string().min(1),
  message_preview: z.string().optional().default(''),
  message_count: z.number().int().nonnegative().optional().default(0),
  report_id: z.number().int().nullable().optional(),
  report_status: z.enum(['draft', 'pending_review', 'reviewed']).nullable().optional(),
  created_at: timestamp,
  updated_at: timestamp,
  topic_codes: z.array(z.string().min(1)).max(3).optional().default([]),
})

export const apiConversationSummaryPageSchema = z.object({
  items: z.array(conversationSummarySchema),
  total: z.number().int().nonnegative(),
  limit: z.number().int().positive(),
  offset: z.number().int().nonnegative(),
})

export const apiReportSchema = z.object({
  id: z.number().int(),
  conversation_id: z.number().int(),
  conversation_client_id: z.string().nullable().optional(),
  student_id: z.number().int(),
  student_name: z.string().nullable().optional(),
  status: z.enum(['draft', 'pending_review', 'reviewed']),
  ai_score: z.number(),
  ai_summary: z.string(),
  analysis: reportAnalysisSchema.nullable().optional(),
  messages: z.array(apiMessageSchema).optional().default([]),
  teacher_score: z.number().nullable().optional(),
  teacher_feedback: z.string().nullable().optional(),
  reviewer_id: z.number().int().nullable().optional(),
  review_topic_codes: z.array(z.string().min(1)).max(3).optional().default([]),
  created_at: timestamp,
  updated_at: timestamp,
})

export const apiReportListSchema = z.array(apiReportSchema)

const reportSummarySchema = z.object({
  id: z.number().int(),
  conversation_id: z.number().int(),
  conversation_client_id: z.string().min(1),
  student_id: z.number().int(),
  student_name: z.string(),
  status: z.enum(['draft', 'pending_review', 'reviewed']),
  ai_score: z.number(),
  teacher_score: z.number().nullable().optional(),
  message_preview: z.string().optional().default(''),
  message_count: z.number().int().nonnegative().optional().default(0),
  created_at: timestamp,
  updated_at: timestamp,
})

export const apiReportSummaryPageSchema = z.object({
  items: z.array(reportSummarySchema),
  total: z.number().int().nonnegative(),
  pending_count: z.number().int().nonnegative(),
  reviewed_count: z.number().int().nonnegative(),
  limit: z.number().int().positive(),
  offset: z.number().int().nonnegative(),
})

const openingSchema = z.object({
  setting: z.string(),
  patient_intro: z.string(),
  chief_complaint: z.string(),
})

export const apiProblemSchema = z.object({
  id: z.number().int(),
  // The backend keeps this as a display label rather than a closed enum. Keep
  // runtime validation at the DTO boundary without rejecting historical or
  // newly introduced teaching content types (for example, "病例单选").
  type: z.string().min(1),
  title: z.string(),
  description: z.string().optional().default(''),
  target: z.enum(['all', 'class', 'individual']),
  target_label: z.string(),
  target_ids: z.array(z.string()).optional().default([]),
  status: z.enum(['draft', 'published', 'rejected']),
  created_at: timestamp,
  published_at: timestamp.nullable().optional(),
  answer_count: z.number().int().nonnegative().optional().default(0),
  content_type: z.enum(['question', 'guided_case']).optional().default('question'),
  slug: z.string().nullable().optional(),
  specialty: z.string().optional().default(''),
  difficulty: z.enum(['basic', 'intermediate', 'advanced']).optional().default('basic'),
  estimated_minutes: z.number().int().positive().optional().default(10),
  version: z.number().int().positive().optional().default(1),
  parent_problem_id: z.number().int().nullable().optional(),
  author_id: z.number().int().nullable().optional(),
  medical_review_status: z.enum(['not_submitted', 'pending', 'approved', 'rejected']).default('not_submitted'),
  opening: openingSchema.nullable().optional(),
  capability_tags: z.array(z.string()).optional().default([]),
  knowledge_point_codes: z.array(z.string()).optional().default([]),
})

export const apiProblemListSchema = z.array(apiProblemSchema)

export const apiQuestionThreadSchema = z.object({
  question_id: z.number().int(),
  messages: z.array(apiMessageSchema).optional().default([]),
  updated_at: timestamp,
})

export const studentQuestionSchema = z.object({
  id: z.number().int(),
  type: z.string().min(1),
  title: z.string(),
  description: z.string().optional().default(''),
  published_at: timestamp,
  status: z.enum(['answered', 'unanswered']),
  topic_codes: z.array(z.string()).optional().default([]),
})

export const apiStudentQuestionListSchema = z.array(studentQuestionSchema)

export const apiStudentQuestionPageSchema = z.object({
  items: z.array(studentQuestionSchema),
  total: z.number().int().nonnegative(),
  limit: z.number().int().positive(),
  offset: z.number().int().nonnegative(),
})
