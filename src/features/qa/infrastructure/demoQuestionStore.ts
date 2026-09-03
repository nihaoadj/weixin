import { z, type ZodType } from 'zod'
import { builtInQuestions } from './demoSeeds'
import { questionThreadSchema, storage, storageKeys } from '@/platform/storage/storage'
import { getSessionContext } from '@/platform/session/context'
import type { Problem, QuestionThread, StudentQuestion } from '@/types/domain'

const MAX_CONVERSATION_MESSAGES = 100
const MAX_QUESTION_THREADS = 50

function userScopedKey(baseKey: string, openid?: string): string | null {
  const userId = openid || getSessionContext()?.openid
  return userId ? storage.scopedKey(baseKey, userId) : null
}

function readArray<T>(key: string, itemSchema: ZodType<T>): T[] {
  return storage.read(key, z.array(itemSchema), [])
}

function writeArray<T>(key: string, value: T[], itemSchema: ZodType<T>): void {
  storage.write(key, value, z.array(itemSchema))
}

export function getAnsweredQuestionIds(): string[] {
  const scopedKey = userScopedKey(storageKeys.answeredQuestions)
  return scopedKey ? readArray(scopedKey, z.string()) : []
}

export function markQuestionAnswered(questionId: string): void {
  const scopedKey = userScopedKey(storageKeys.answeredQuestions)
  if (!scopedKey) throw new Error('记录作答前必须登录')
  const ids = new Set(getAnsweredQuestionIds())
  ids.add(questionId)
  writeArray(scopedKey, Array.from(ids), z.string())
}

export function getQuestionAnswerCount(questionId: string): number {
  return storage
    .keys()
    .filter((key) => key.startsWith(`${storageKeys.answeredQuestions}:`))
    .reduce((count, key) => count + (readArray(key, z.string()).includes(questionId) ? 1 : 0), 0)
}

function isProblemVisibleToStudent(
  problem: Problem,
  student: NonNullable<ReturnType<typeof getSessionContext>>,
): boolean {
  if (problem.status !== '已发布') return false
  if (problem.target === 'all') return true
  const targetIds = problem.targetIds || []
  if (problem.target === 'individual') return targetIds.includes(student.openid)
  return Boolean(student.classIds?.some((classId) => targetIds.includes(classId)))
}

export function getStudentQuestions(problems: Problem[] = []): StudentQuestion[] {
  const student = getSessionContext()
  if (!student || student.role !== 'student') return []
  const answered = new Set(getAnsweredQuestionIds())
  const published = problems
    .filter((problem) => problem.contentType !== 'guided_case' && isProblemVisibleToStudent(problem, student))
    .map((problem) => ({
      id: problem.id,
      type: problem.type,
      title: problem.title,
      description: problem.description,
      time: problem.publishTime || problem.time,
      status: answered.has(problem.id) ? ('已回答' as const) : ('未回答' as const),
    }))
  const builtIn = builtInQuestions.map((question) => ({
    ...question,
    status: answered.has(question.id) ? ('已回答' as const) : ('未回答' as const),
  }))
  const publishedIds = new Set(published.map((question) => question.id))
  return [...published, ...builtIn.filter((question) => !publishedIds.has(question.id))]
}

export function findStudentQuestion(id: string, problems: Problem[] = []): StudentQuestion | undefined {
  return getStudentQuestions(problems).find((question) => question.id === id)
}

export function getQuestionThread(questionId: string): QuestionThread | undefined {
  const scopedKey = userScopedKey(storageKeys.questionThreads)
  return scopedKey
    ? readArray(scopedKey, questionThreadSchema).find((thread) => thread.questionId === questionId)
    : undefined
}

export function saveQuestionThread(thread: QuestionThread): void {
  const scopedKey = userScopedKey(storageKeys.questionThreads)
  if (!scopedKey) throw new Error('保存作答前必须登录')
  const threads = readArray(scopedKey, questionThreadSchema)
  const index = threads.findIndex((item) => item.questionId === thread.questionId)
  const boundedThread = { ...thread, messages: thread.messages.slice(-MAX_CONVERSATION_MESSAGES) }
  if (index >= 0) threads[index] = boundedThread
  else threads.unshift(boundedThread)
  writeArray(scopedKey, threads.slice(0, MAX_QUESTION_THREADS), questionThreadSchema)
}
