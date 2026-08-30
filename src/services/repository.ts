import { builtInQuestions, createDemoConversations, createDemoProblems, createDemoReports } from '@/data/demo'
import type {
  Conversation,
  Problem,
  QuestionThread,
  Report,
  SessionUser,
  StudentQuestion,
  UserRole,
} from '@/types/domain'

const STORAGE_SCHEMA_VERSION = 2
const MAX_CONVERSATION_MESSAGES = 100
const MAX_CONVERSATIONS = 10
const MAX_REPORTS = 100
const MAX_PROBLEMS = 200
const MAX_QUESTION_THREADS = 50

const keys = {
  user: 'userInfo',
  role: 'role',
  openid: 'openid',
  conversations: 'conversationHistory',
  reports: 'reports',
  problems: 'problems',
  answeredQuestions: 'answeredQuestionIds',
  questionThreads: 'questionThreads',
  schemaVersion: 'storageSchemaVersion',
} as const

type ReportDraftInput = Omit<Report, 'studentId' | 'studentName' | 'status'>

function readArray<T>(key: string): T[] {
  const value = uni.getStorageSync(key) as unknown
  return Array.isArray(value) ? (value as T[]) : []
}

function writeArray<T>(key: string, value: T[]): void {
  try {
    uni.setStorageSync(key, value)
  } catch (error) {
    console.error(`写入本地存储失败: ${key}`, error)
    throw new Error('本地存储空间不足，请清理历史数据后重试', { cause: error })
  }
}

function userScopedKey(baseKey: string, openid?: string): string | null {
  const userId = openid || getSession()?.openid
  return userId ? `${baseKey}:${encodeURIComponent(userId)}` : null
}

function migrateLegacyStudentData(user: SessionUser): void {
  if (user.role !== 'student') return
  const currentVersion = Number(uni.getStorageSync(keys.schemaVersion) || 0)
  if (currentVersion >= STORAGE_SCHEMA_VERSION) return

  const privateCollections = [keys.conversations, keys.answeredQuestions, keys.questionThreads]
  for (const legacyKey of privateCollections) {
    const legacyValue = uni.getStorageSync(legacyKey) as unknown
    const scopedKey = userScopedKey(legacyKey, user.openid)
    if (scopedKey && Array.isArray(legacyValue) && !readArray<unknown>(scopedKey).length) {
      writeArray(scopedKey, legacyValue)
    }
    uni.removeStorageSync(legacyKey)
  }

  const migratedReports = readArray<Report>(keys.reports).map((report) => ({
    ...report,
    studentId: report.studentId || user.openid,
    studentName: report.studentName || user.nickName,
    status: report.status || '草稿',
  }))
  writeArray(keys.reports, migratedReports)
  uni.setStorageSync(keys.schemaVersion, STORAGE_SCHEMA_VERSION)
}

export function saveSession(user: SessionUser): void {
  migrateLegacyStudentData(user)
  uni.setStorageSync(keys.user, user)
  uni.setStorageSync(keys.role, user.role)
  uni.setStorageSync(keys.openid, user.openid)
}

export function getSession(): SessionUser | null {
  const value = uni.getStorageSync(keys.user) as SessionUser | undefined
  if (!value?.openid || (value.role !== 'student' && value.role !== 'teacher')) return null
  return value
}

export function getRole(): UserRole | null {
  return getSession()?.role || null
}

export function clearSession(): void {
  uni.removeStorageSync(keys.user)
  uni.removeStorageSync(keys.role)
  uni.removeStorageSync(keys.openid)
  uni.removeStorageSync('apiAccessToken')
}

export function getConversations(): Conversation[] {
  const scopedKey = userScopedKey(keys.conversations)
  return scopedKey ? readArray<Conversation>(scopedKey) : []
}

export function findConversation(conversationId: string): Conversation | undefined {
  return getConversations().find((item) => item.conversationId === conversationId)
}

export function upsertConversation(conversation: Conversation): void {
  const scopedKey = userScopedKey(keys.conversations)
  if (!scopedKey) throw new Error('保存对话前必须登录')
  const history = getConversations()
  const index = history.findIndex((item) => item.conversationId === conversation.conversationId)
  if (index >= 0) history.splice(index, 1)
  history.unshift({ ...conversation, messages: conversation.messages.slice(-MAX_CONVERSATION_MESSAGES) })
  writeArray(scopedKey, history.slice(0, MAX_CONVERSATIONS))
}

function getAllReports(): Report[] {
  return readArray<Report>(keys.reports)
}

function writeReports(reports: Report[]): void {
  writeArray(keys.reports, reports.slice(-MAX_REPORTS))
}

export function getReports(): Report[] {
  const session = getSession()
  if (!session) return []
  const reports = getAllReports()
  return session.role === 'teacher' ? reports : reports.filter((report) => report.studentId === session.openid)
}

export function findReport(conversationId: string): Report | undefined {
  return getReports().find((report) => report.conversationId === conversationId)
}

export function saveDraftReport(input: ReportDraftInput): Report {
  const session = getSession()
  if (!session || session.role !== 'student') throw new Error('只有学生可以生成报告')

  const reports = getAllReports()
  const index = reports.findIndex(
    (report) => report.conversationId === input.conversationId && report.studentId === session.openid,
  )
  const existing = index >= 0 ? reports[index] : undefined
  if (existing && existing.status !== '草稿') return existing

  const draft: Report = {
    ...input,
    messages: input.messages.slice(-MAX_CONVERSATION_MESSAGES),
    createdAt: existing?.createdAt || input.createdAt,
    studentId: session.openid,
    studentName: session.nickName,
    status: '草稿',
  }
  if (index >= 0) reports[index] = draft
  else reports.push(draft)
  writeReports(reports)
  return draft
}

export function submitReportForReview(conversationId: string): Report | null {
  const session = getSession()
  if (!session || session.role !== 'student') return null
  const reports = getAllReports()
  const index = reports.findIndex(
    (report) => report.conversationId === conversationId && report.studentId === session.openid,
  )
  const report = index >= 0 ? reports[index] : undefined
  if (!report || report.status !== '草稿') return null
  const submitted: Report = { ...report, status: '待批阅' }
  reports[index] = submitted
  writeReports(reports)
  return submitted
}

export function reviewReport(conversationId: string, score: number, feedback: string): Report | null {
  const session = getSession()
  if (!session || session.role !== 'teacher') return null
  const reports = getAllReports()
  const index = reports.findIndex((report) => report.conversationId === conversationId)
  const report = index >= 0 ? reports[index] : undefined
  if (!report || (report.status !== '待批阅' && report.status !== '已批阅')) return null
  const reviewed: Report = {
    ...report,
    status: '已批阅',
    teacherScore: score,
    teacherFeedback: feedback,
  }
  reports[index] = reviewed
  writeReports(reports)
  return reviewed
}

export function getProblems(): Problem[] {
  return readArray<Problem>(keys.problems)
}

export function saveProblems(problems: Problem[]): void {
  writeArray(keys.problems, problems.slice(0, MAX_PROBLEMS))
}

export function findProblem(id: string): Problem | undefined {
  return getProblems().find((problem) => problem.id === id)
}

export function upsertProblem(problem: Problem): void {
  const problems = getProblems()
  const index = problems.findIndex((item) => item.id === problem.id)
  if (index >= 0) problems[index] = problem
  else problems.unshift(problem)
  saveProblems(problems)
}

export function resetProblems(): Problem[] {
  const problems = createDemoProblems()
  saveProblems(problems)
  return problems
}

export function getAnsweredQuestionIds(): string[] {
  const scopedKey = userScopedKey(keys.answeredQuestions)
  return scopedKey ? readArray<string>(scopedKey) : []
}

export function markQuestionAnswered(questionId: string): void {
  const scopedKey = userScopedKey(keys.answeredQuestions)
  if (!scopedKey) throw new Error('记录作答前必须登录')
  const ids = new Set(getAnsweredQuestionIds())
  ids.add(questionId)
  writeArray(scopedKey, Array.from(ids))
}

export function getQuestionAnswerCount(questionId: string): number {
  const storageInfo = uni.getStorageInfoSync()
  return storageInfo.keys
    .filter((key) => key.startsWith(`${keys.answeredQuestions}:`))
    .reduce((count, key) => count + (readArray<string>(key).includes(questionId) ? 1 : 0), 0)
}

function isProblemVisibleToStudent(problem: Problem, student: SessionUser): boolean {
  if (problem.status !== '已发布') return false
  if (problem.target === 'all') return true
  const targetIds = problem.targetIds || []
  if (problem.target === 'individual') return targetIds.includes(student.openid)
  return Boolean(student.classIds?.some((classId) => targetIds.includes(classId)))
}

export function getStudentQuestions(): StudentQuestion[] {
  const student = getSession()
  if (!student || student.role !== 'student') return []
  const answered = new Set(getAnsweredQuestionIds())
  const published: StudentQuestion[] = getProblems()
    .filter((problem) => isProblemVisibleToStudent(problem, student))
    .map((problem) => ({
      id: problem.id,
      type: problem.type,
      title: problem.title,
      description: problem.description,
      time: problem.publishTime || problem.time,
      status: answered.has(problem.id) ? '已回答' : '未回答',
    }))
  const builtIn = builtInQuestions.map((question) => ({
    ...question,
    status: answered.has(question.id) ? ('已回答' as const) : ('未回答' as const),
  }))
  const publishedIds = new Set(published.map((question) => question.id))
  return [...published, ...builtIn.filter((question) => !publishedIds.has(question.id))]
}

export function findStudentQuestion(id: string): StudentQuestion | undefined {
  return getStudentQuestions().find((question) => question.id === id)
}

export function getQuestionThread(questionId: string): QuestionThread | undefined {
  const scopedKey = userScopedKey(keys.questionThreads)
  return scopedKey ? readArray<QuestionThread>(scopedKey).find((thread) => thread.questionId === questionId) : undefined
}

export function saveQuestionThread(thread: QuestionThread): void {
  const scopedKey = userScopedKey(keys.questionThreads)
  if (!scopedKey) throw new Error('保存作答前必须登录')
  const threads = readArray<QuestionThread>(scopedKey)
  const index = threads.findIndex((item) => item.questionId === thread.questionId)
  const boundedThread = { ...thread, messages: thread.messages.slice(-MAX_CONVERSATION_MESSAGES) }
  if (index >= 0) threads[index] = boundedThread
  else threads.unshift(boundedThread)
  writeArray(scopedKey, threads.slice(0, MAX_QUESTION_THREADS))
}

export function ensureDemoData(): void {
  const current = uni.getStorageSync(keys.problems) as unknown
  if (!Array.isArray(current)) resetProblems()
  const demoConversationKey = userScopedKey(keys.conversations, 'demo_student')
  if (demoConversationKey) {
    const conversations = readArray<Conversation>(demoConversationKey)
    const fixtures = createDemoConversations()
    const missing = fixtures.filter(
      (fixture) => !conversations.some((conversation) => conversation.conversationId === fixture.conversationId),
    )
    if (missing.length) writeArray(demoConversationKey, [...conversations, ...missing])
  }
  const reports = getAllReports()
  const fixtures = createDemoReports()
  const missing = fixtures.filter(
    (fixture) => !reports.some((report) => report.conversationId === fixture.conversationId),
  )
  if (missing.length) writeReports([...reports, ...missing])
}
