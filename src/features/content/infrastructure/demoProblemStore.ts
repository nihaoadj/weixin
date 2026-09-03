import { z } from 'zod'
import { createDemoProblems } from './demoProblemSeeds'
import { problemSchema, storage, storageKeys } from '@/platform/storage/storage'
import type { Problem } from '@/types/domain'

const MAX_PROBLEMS = 200

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
