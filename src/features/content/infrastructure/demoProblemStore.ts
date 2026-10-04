import { z } from 'zod'
import { createDemoProblems } from './demoProblemSeeds'
import { problemSchema, storage, storageKeys } from '@/platform/storage/storage'
import type { Problem } from '@/types/domain'
import { getSessionContext } from '@/platform/session/context'
import { AppError } from '@/types/errors'

const MAX_PROBLEMS = 200
const ownerSchema = z.record(z.string(), z.string())
const ownersKey = storageKeys.problemOwners
export function problemOwners(): Record<string, string> {
  return storage.read(ownersKey, ownerSchema, {})
}
export function assertProblemOwner(id: string): void {
  const owner = problemOwners()[id]
  if (owner && owner !== getSessionContext()?.openid) throw new AppError('内容不存在', { code: 'RESOURCE_NOT_FOUND' })
}
export function claimProblemOwner(id: string): void {
  const user = getSessionContext()
  if (!user || user.role !== 'teacher') throw new AppError('无权编辑内容', { code: 'FORBIDDEN' })
  assertProblemOwner(id)
  storage.write(ownersKey, { ...problemOwners(), [id]: user.openid }, ownerSchema)
}

export function getProblems(): Problem[] {
  return storage.read(storageKeys.problems, z.array(problemSchema), [])
}

export function saveProblems(problems: Problem[]): void {
  storage.write(storageKeys.problems, problems.slice(0, MAX_PROBLEMS), z.array(problemSchema))
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
