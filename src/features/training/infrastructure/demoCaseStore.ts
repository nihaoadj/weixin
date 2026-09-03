import { z } from 'zod'
import { AppError } from '@/types/errors'
import { storage, storageKeys } from '@/platform/storage/storage'
import { localAttemptSchema, localAssessmentSchema } from '@/platform/storage/caseSchemas'
import { getSessionContext } from '@/platform/session/context'
import type { CaseCatalogPort } from '@/features/training/domain/ports'
import { scoreDemoCase } from '@/features/training/domain/scoring'
import type { CaseAssessment, CaseAttempt, CaseStageId, StageAnswer } from '@/types/case'

const key = (name: string) => storage.scopedKey(name, getSessionContext()?.openid || 'anonymous')
const write = <T>(name: string, value: T[], schema: z.ZodType<T>) => storage.write(key(name), value, z.array(schema))
const stages: CaseStageId[] = ['history', 'problem_representation', 'differential', 'tests', 'management']

let caseCatalog: CaseCatalogPort | undefined

export function configureDemoCaseCatalog(catalog: CaseCatalogPort): void {
  caseCatalog = catalog
}

function demoDraftForProblem(id: string) {
  if (!caseCatalog) {
    throw new AppError('病例训练尚未完成装配', { code: 'CONFIGURATION_ERROR', statusCode: 500 })
  }
  return caseCatalog.findCaseDraft(id)
}

export function demoAttempts(): CaseAttempt[] {
  return storage.read(key(storageKeys.caseAttempts), z.array(localAttemptSchema), [])
}

export function demoStart(problemId: string, retryOfId?: string): CaseAttempt {
  const target = demoDraftForProblem(problemId)
  if (!target) throw new AppError('病例不存在', { code: 'RESOURCE_NOT_FOUND', statusCode: 404 })
  const prior = retryOfId ? demoAttempts().find((item) => item.id === retryOfId) : undefined
  const focus = prior
    ? demoAssessments().find((item) => item.attemptId === prior.id)?.focusStage || 'history'
    : 'history'
  const attempt: CaseAttempt = {
    id: `case-${Date.now()}`,
    problemId,
    problemVersion: target.problem.version || 1,
    status: 'in_progress',
    currentStage: focus,
    focusStage: prior ? focus : undefined,
    retryOfId,
    opening: target.draft.caseDefinition.opening,
    messages: [],
    submissions: prior ? prior.submissions.filter((item) => stages.indexOf(item.stageId) < stages.indexOf(focus)) : [],
    assessmentReady: false,
    startedAt: new Date().toISOString(),
  }
  write(storageKeys.caseAttempts, [attempt, ...demoAttempts()].slice(0, 30), localAttemptSchema)
  return attempt
}

export function demoFind(id: string): CaseAttempt | undefined {
  return demoAttempts().find((item) => item.id === id)
}

export function demoMessage(id: string, content: string): CaseAttempt {
  const attempt = demoFind(id)
  if (!attempt || attempt.currentStage !== 'history')
    throw new AppError('病史阶段已锁定', { code: 'STATE_CONFLICT', statusCode: 409 })
  const target = demoDraftForProblem(attempt.problemId)
  if (!target) throw new AppError('病例不存在', { code: 'RESOURCE_NOT_FOUND', statusCode: 404 })
  const asked = attempt.messages.filter((item) => item.role === 'user').length
  if (asked >= 30) throw new AppError('请先提交病史小结', { code: 'STATE_CONFLICT', statusCode: 409 })
  const seen = new Set(
    attempt.messages.filter((item) => item.role === 'assistant').flatMap((item) => item.revealedFactIds || []),
  )
  const matching = target.draft.caseDefinition.facts
    .filter(
      (fact) =>
        fact.triggers.some((trigger) => content.toLowerCase().includes(trigger.toLowerCase())) && !seen.has(fact.id),
    )
    .slice(0, 2)
  const reply = matching.length
    ? matching.map((item) => item.value).join(' ')
    : '您想具体了解症状经过、伴随表现还是既往情况？'
  attempt.messages.push(
    { id: `${Date.now()}u`, role: 'user', content, createdAt: new Date().toISOString() },
    {
      id: `${Date.now()}a`,
      role: 'assistant',
      content: reply,
      revealedFactIds: matching.map((fact) => fact.id),
      createdAt: new Date().toISOString(),
    },
  )
  saveAttempt(attempt)
  return attempt
}

export function demoSubmit(id: string, answer: StageAnswer): CaseAttempt {
  const attempt = demoFind(id)
  if (!attempt || attempt.currentStage !== answer.stageId)
    throw new AppError('训练状态已同步，请重新进入', { code: 'STATE_CONFLICT', statusCode: 409 })
  attempt.submissions.push({
    id: `${Date.now()}`,
    stageId: answer.stageId,
    answer,
    feedback: '已保存。请继续下一阶段。',
    createdAt: new Date().toISOString(),
  })
  const index = stages.indexOf(answer.stageId)
  attempt.currentStage = index === 4 ? 'completed' : stages[index + 1]
  if (index === 4) attempt.status = 'completed'
  saveAttempt(attempt)
  return attempt
}

export function demoAssessments(): CaseAssessment[] {
  return storage.read(key(storageKeys.caseAssessments), z.array(localAssessmentSchema), [])
}

export function demoComplete(id: string): CaseAssessment {
  const attempt = demoFind(id)
  if (!attempt || attempt.status !== 'completed')
    throw new AppError('请先完成五个阶段', { code: 'STATE_CONFLICT', statusCode: 409 })
  const target = demoDraftForProblem(attempt.problemId)
  if (!target) throw new AppError('病例不存在', { code: 'RESOURCE_NOT_FOUND', statusCode: 404 })
  const dimensions = scoreDemoCase(attempt, target.draft)
  const focus = dimensions.reduce((lowest, item) => (item.score < lowest.score ? item : lowest)).dimensionId
  const focusStage = target.draft.rubric.dimensions.find((item) => item.id === focus)?.stageIds[0] || 'history'
  const previous = attempt.retryOfId
    ? demoAssessments().find((item) => item.attemptId === attempt.retryOfId)
    : undefined
  const assessment: CaseAssessment = {
    attemptId: id,
    totalScore: Math.round(dimensions.reduce((sum, item) => sum + item.weightedScore, 0)),
    dimensions,
    strengths: dimensions.filter((item) => item.score >= 70).map((item) => item.label),
    weaknesses: dimensions.filter((item) => item.score < 70).map((item) => item.label),
    nextSteps: ['针对最低分维度进行强化练习。'],
    summary: '本结果仅用于教学训练，不构成诊断或治疗建议。',
    focusStage,
    modelName: 'deterministic-fallback',
    promptVersion: 'case-v2',
    fallbackUsed: true,
    comparison: previous
      ? {
          totalDelta:
            Math.round((dimensions.reduce((sum, item) => sum + item.weightedScore, 0) - previous.totalScore) * 10) / 10,
          dimensions: dimensions.map((item) => ({
            dimensionId: item.dimensionId,
            previousScore: previous.dimensions.find((old) => old.dimensionId === item.dimensionId)?.score || 0,
            currentScore: item.score,
            delta:
              Math.round(
                (item.score - (previous.dimensions.find((old) => old.dimensionId === item.dimensionId)?.score || 0)) *
                  10,
              ) / 10,
          })),
        }
      : undefined,
  }
  attempt.status = 'assessed'
  attempt.assessmentReady = true
  saveAttempt(attempt)
  write(
    storageKeys.caseAssessments,
    [assessment, ...demoAssessments().filter((item) => item.attemptId !== id)],
    localAssessmentSchema,
  )
  return assessment
}

function saveAttempt(attempt: CaseAttempt) {
  write(
    storageKeys.caseAttempts,
    demoAttempts().map((item) => (item.id === attempt.id ? attempt : item)),
    localAttemptSchema,
  )
}
