import { z, type ZodType } from 'zod'
import type { Conversation, Problem, QuestionThread, Report, SessionUser } from '@/types/domain'

export const STORAGE_SCHEMA_VERSION = 3

export const storageKeys = {
  user: 'userInfo',
  role: 'role',
  openid: 'openid',
  apiToken: 'apiAccessToken',
  conversations: 'conversationHistory',
  reports: 'reports',
  problems: 'problems',
  answeredQuestions: 'answeredQuestionIds',
  questionThreads: 'questionThreads',
  schemaVersion: 'storageSchemaVersion',
  caseAttempts: 'caseAttempts',
  caseAssessments: 'caseAssessments',
  guidedDrafts: 'guidedCaseDrafts',
  logs: 'logs',
} as const

const timestamp = z.string().min(1)
const messageSchema = z.object({
  id: z.string(),
  role: z.enum(['user', 'assistant']),
  content: z.string(),
  timestamp,
})

export const sessionSchema: ZodType<SessionUser> = z.object({
  openid: z.string().min(1),
  role: z.enum(['student', 'teacher']),
  nickName: z.string(),
  avatarUrl: z.string(),
  classIds: z.array(z.string()).optional(),
  permissions: z.array(z.string()).optional(),
  createdAt: timestamp,
})

export const conversationSchema: ZodType<Conversation> = z.object({
  conversationId: z.string().min(1),
  messages: z.array(messageSchema),
  createdAt: timestamp,
  updatedAt: timestamp,
  topicCodes: z.array(z.string().min(1)).max(3).optional(),
})

const analysisIssueSchema = z.object({ content: z.string(), suggestion: z.string() })

export const reportSchema: ZodType<Report> = z.object({
  updatedAt: timestamp.optional(),
  id: z.string().optional(),
  conversationId: z.string().min(1),
  messages: z.array(messageSchema),
  analysis: z.object({
    errors: z.array(analysisIssueSchema),
    strengths: z.array(z.string()).optional(),
    generalSuggestions: z.array(z.string()).optional(),
    score: z.number(),
    summary: z.string(),
  }),
  createdAt: timestamp,
  studentId: z.string(),
  studentName: z.string(),
  status: z.enum(['草稿', '待批阅', '已批阅']),
  teacherScore: z.number().optional(),
  teacherFeedback: z.string().optional(),
  reviewTopicCodes: z.array(z.string().min(1)).max(3).optional(),
})

export const problemSchema: ZodType<Problem> = z.object({
  id: z.string(),
  type: z.enum(['医学常识', '模拟诊疗', '病例分析']),
  title: z.string(),
  description: z.string(),
  target: z.enum(['all', 'class', 'individual']),
  status: z.enum(['待审核', '已发布', '已拒绝']),
  time: timestamp,
  publishTime: z.string().optional(),
  targetIds: z.array(z.string()).optional(),
  targetLabel: z.string().optional(),
  className: z.string().optional(),
  studentCount: z.number().optional(),
  answerCount: z.number().optional(),
  contentType: z.enum(['question', 'guided_case']).optional(),
  slug: z.string().optional(),
  specialty: z.string().optional(),
  difficulty: z.enum(['basic', 'intermediate', 'advanced']).optional(),
  estimatedMinutes: z.number().optional(),
  version: z.number().optional(),
  authorId: z.number().optional(),
  parentProblemId: z.number().optional(),
  medicalReviewStatus: z.enum(['not_submitted', 'pending', 'approved', 'rejected']).optional(),
  opening: z.object({ setting: z.string(), patientIntro: z.string(), chiefComplaint: z.string() }).optional(),
  capabilityTags: z.array(z.string()).optional(),
  knowledgePointCodes: z.array(z.string()).optional(),
})

export const questionThreadSchema: ZodType<QuestionThread> = z.object({
  questionId: z.string(),
  messages: z.array(messageSchema),
  updatedAt: timestamp,
})

export interface StoragePort {
  scopedKey(baseKey: string, userId: string): string
  read<T>(key: string, schema: ZodType<T>, fallback: T): T
  readRaw(key: string): unknown
  write<T>(key: string, value: T, schema: ZodType<T>): void
  remove(key: string): void
  keys(): string[]
}

export class StorageGateway implements StoragePort {
  scopedKey(baseKey: string, userId: string): string {
    if (!userId) throw new Error('用户作用域不能为空')
    return `${baseKey}:${encodeURIComponent(userId)}`
  }

  read<T>(key: string, schema: ZodType<T>, fallback: T): T {
    const raw: unknown = uni.getStorageSync(key)
    const parsed = schema.safeParse(raw)
    if (parsed.success) return parsed.data
    if (raw !== '' && raw !== undefined) {
      console.warn(`忽略不符合本地数据契约的存储项: ${key}`)
    }
    return fallback
  }

  readRaw(key: string): unknown {
    return uni.getStorageSync(key) as unknown
  }

  write<T>(key: string, value: T, schema: ZodType<T>): void {
    const parsed = schema.safeParse(value)
    if (!parsed.success) throw new Error(`拒绝写入不符合本地数据契约的数据: ${key}`)
    try {
      uni.setStorageSync(key, parsed.data)
    } catch (error) {
      console.error(`写入本地存储失败: ${key}`)
      throw new Error('本地存储空间不足，请清理历史数据后重试', { cause: error })
    }
  }

  remove(key: string): void {
    uni.removeStorageSync(key)
  }

  keys(): string[] {
    return uni.getStorageInfoSync().keys
  }
}

export const storage = new StorageGateway()
