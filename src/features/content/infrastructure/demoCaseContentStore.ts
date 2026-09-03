import { AppError } from '@/types/errors'
import { additionalShowcaseDrafts, showcaseDraft } from './demoSeeds'
import { z } from 'zod'
import { storage, storageKeys } from '@/platform/storage/storage'
import { localDraftSchema, localCaseRecordSchema } from '@/platform/storage/caseSchemas'
import { getSessionContext } from '@/platform/session/context'
import type { CaseDraftGenerateResult } from '@/types/case'
import type { Problem } from '@/types/domain'
import { fromProblemView } from '@/shared/mappers/presentation'
import type { Problem as RecordProblem } from '@/types/records'
import type { MedicalReviewView } from '@/types/review'

const guidedDraftKey = storageKeys.guidedDrafts

interface DemoReview {
  id: string
  reviewerOpenid: string
  reviewerName: string
  decision: 'approved' | 'rejected'
  comment: string
  problemVersion: number
  caseDigest: string
  createdAt: string
}

interface DemoCaseRecord {
  problem: Problem
  draft: CaseDraftGenerateResult
  authorOpenid: string
  reviews: DemoReview[]
}

function builtInProblem(id: string): Problem | undefined {
  const draft = id === 'cap-undergraduate-showcase' ? showcaseDraft : additionalShowcaseDrafts[id]
  if (!draft) return undefined
  return {
    id,
    type: '病例分析',
    title: draft.title,
    description: draft.description,
    target: 'all',
    status: '已发布',
    time: new Date(0).toISOString(),
    contentType: 'guided_case',
    slug: id,
    specialty: draft.specialty,
    difficulty: draft.difficulty,
    estimatedMinutes: draft.estimatedMinutes,
    version: 1,
    opening: draft.caseDefinition.opening,
    medicalReviewStatus: 'approved',
  }
}

export function demoDraftForProblem(id: string): { problem: Problem; draft: CaseDraftGenerateResult } | undefined {
  const builtIn = builtInProblem(id)
  if (builtIn) {
    const draft = id === 'cap-undergraduate-showcase' ? showcaseDraft : additionalShowcaseDrafts[id]
    return draft ? { problem: builtIn, draft } : undefined
  }
  const record = normalizedRecords().find((item) => item.problem.id === id)
  return record ? { problem: record.problem, draft: record.draft } : undefined
}

export function demoCaseCatalog(id: string): { problem: RecordProblem; draft: CaseDraftGenerateResult } | undefined {
  const target = demoDraftForProblem(id)
  return target ? { problem: fromProblemView(target.problem), draft: target.draft } : undefined
}

function stableStringify(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(stableStringify).join(',')}]`
  if (value && typeof value === 'object') {
    return `{${Object.entries(value as Record<string, unknown>)
      .sort(([left], [right]) => left.localeCompare(right))
      .map(([name, item]) => `${JSON.stringify(name)}:${stableStringify(item)}`)
      .join(',')}}`
  }
  return JSON.stringify(value)
}

function demoCaseDigest(problem: Problem, draft: CaseDraftGenerateResult): string {
  const input = {
    title: problem.title,
    description: problem.description,
    specialty: problem.specialty,
    difficulty: problem.difficulty,
    estimatedMinutes: problem.estimatedMinutes,
    target: problem.target,
    targetIds: problem.targetIds || [],
    caseDefinition: draft.caseDefinition,
    rubric: draft.rubric,
    capabilityTags: problem.capabilityTags || [],
    schemaVersion: draft.caseDefinition.schemaVersion,
  }
  const seed = 2166136261
  const parts: string[] = []
  for (let round = 0; round < 8; round += 1) {
    let hash = (seed + round * 374761393) >>> 0
    for (const char of stableStringify(input)) {
      hash ^= char.charCodeAt(0)
      hash = Math.imul(hash, 16777619) >>> 0
    }
    parts.push(hash.toString(16).padStart(8, '0'))
  }
  return parts.join('')
}

function currentDemoUser() {
  const user = getSessionContext()
  if (!user || user.role !== 'teacher')
    throw new AppError('只有教师可以编排病例', { code: 'FORBIDDEN', statusCode: 403 })
  return user
}

function cloneDraft(draft: CaseDraftGenerateResult): CaseDraftGenerateResult {
  return localDraftSchema.parse(draft)
}

function normalizedRecords(): DemoCaseRecord[] {
  return storage.read(guidedDraftKey, z.array(localCaseRecordSchema), []).map((record) => ({
    ...record,
    authorOpenid: record.authorOpenid || 'demo_teacher',
    reviews: record.reviews || [],
    problem: {
      ...record.problem,
      medicalReviewStatus:
        record.problem.medicalReviewStatus ||
        (record.reviews?.some((review) => review.decision === 'approved') ? 'approved' : 'not_submitted'),
      status:
        record.problem.medicalReviewStatus === 'approved' &&
        record.reviews?.some((review) => review.decision === 'approved')
          ? record.problem.status
          : record.problem.status === '已发布'
            ? '待审核'
            : record.problem.status,
    },
  }))
}

function writeRecords(records: DemoCaseRecord[]) {
  storage.write(guidedDraftKey, records.slice(-30), z.array(localCaseRecordSchema))
}

export function demoDraft(topic: string): CaseDraftGenerateResult {
  const source = topic.includes('胸痛')
    ? additionalShowcaseDrafts['acute-chest-pain-undergraduate-showcase']
    : topic.includes('右下腹') || topic.includes('阑尾')
      ? additionalShowcaseDrafts['right-lower-quadrant-pain-undergraduate-showcase']
      : showcaseDraft
  const draft = cloneDraft(source)
  if (!['肺炎', '胸痛', '右下腹', '阑尾'].some((keyword) => topic.includes(keyword))) {
    draft.title = `${topic}：结构化临床推理（示例）`
  }
  return draft
}
export function demoCaseProblems(): Problem[] {
  const stored = normalizedRecords()
  const builtIns = ['cap-undergraduate-showcase', ...Object.keys(additionalShowcaseDrafts)]
    .map(builtInProblem)
    .filter((item): item is Problem => Boolean(item))
  const session = getSessionContext()
  const visibleStored = stored
    .filter((item) => item.problem.id !== 'cap-undergraduate-showcase')
    .filter((item) => session?.role !== 'student' || item.problem.status === '已发布')
    .map((item) => item.problem)
  return [...builtIns, ...visibleStored]
}
export function demoGuidedCases(): Problem[] {
  return demoCaseProblems()
}
export function demoAuthoring(id: string): CaseDraftGenerateResult | undefined {
  const user = getSessionContext()
  if (!user || user.role !== 'teacher') return undefined
  if (id === 'cap-undergraduate-showcase' || additionalShowcaseDrafts[id]) {
    return user.openid === 'demo_teacher' ? demoDraftForProblem(id)?.draft : undefined
  }
  return normalizedRecords().find((item) => item.problem.id === id && item.authorOpenid === user.openid)?.draft
}
export function demoSaveCaseDraft(draft: CaseDraftGenerateResult, existingId?: string): Problem {
  const user = currentDemoUser()
  const records = normalizedRecords()
  const old = existingId ? records.find((item) => item.problem.id === existingId) : undefined
  if (old && old.authorOpenid !== user.openid)
    throw new AppError('只有病例作者可以编辑', { code: 'FORBIDDEN', statusCode: 403 })
  if (old && old.problem.medicalReviewStatus === 'pending')
    throw new AppError('审核中的病例不可编辑', { code: 'STATE_CONFLICT', statusCode: 409 })
  if (old && old.problem.medicalReviewStatus === 'approved')
    throw new AppError('已审核病例不可编辑，请创建新版本', { code: 'STATE_CONFLICT', statusCode: 409 })
  const problem: Problem = {
    id: existingId || `demo-case-${Date.now()}`,
    type: '病例分析',
    title: draft.title,
    description: draft.description,
    target: old?.problem.target || 'all',
    status: '待审核',
    time: old?.problem.time || new Date().toISOString(),
    contentType: 'guided_case',
    slug: old?.problem.slug || `demo-case-${Date.now()}`,
    specialty: draft.specialty,
    difficulty: draft.difficulty,
    estimatedMinutes: draft.estimatedMinutes,
    version: old?.problem.version || 1,
    opening: draft.caseDefinition.opening,
    medicalReviewStatus: 'not_submitted',
    authorId: old?.problem.authorId,
  }
  writeRecords([
    ...records.filter((item) => item.problem.id !== problem.id),
    {
      problem,
      draft,
      authorOpenid: user.openid,
      reviews: old?.reviews || [],
    },
  ])
  return problem
}
export function demoCloneCase(id: string): Problem | undefined {
  currentDemoUser()
  const source = demoGuidedCases().find((item) => item.id === id)
  const sourceRecord = normalizedRecords().find((item) => item.problem.id === id)
  const draft = sourceRecord?.draft || demoDraftForProblem(id)?.draft
  if (source && (source.status !== '已发布' || source.medicalReviewStatus !== 'approved')) return undefined
  if (!source || !draft) return undefined
  const version =
    Math.max(
      ...demoGuidedCases()
        .filter((item) => item.slug === source.slug)
        .map((item) => item.version || 1),
    ) + 1
  const cloneId = `demo-case-${Date.now()}-${version}`
  const clone = demoSaveCaseDraft(cloneDraft(draft), cloneId)
  const records = normalizedRecords()
  const record = records.find((item) => item.problem.id === clone.id)
  if (record) {
    record.problem.slug = source.slug
    record.problem.version = version
    record.problem.medicalReviewStatus = 'not_submitted'
    record.reviews = []
    writeRecords(records)
  }
  return record?.problem || clone
}
export function demoPublishCase(id: string): Problem | undefined {
  const user = currentDemoUser()
  const records = normalizedRecords()
  const index = records.findIndex((item) => item.problem.id === id)
  if (index < 0) return id === 'cap-undergraduate-showcase' ? demoCaseProblems()[0] : undefined
  const record = records[index]
  if (record.authorOpenid !== user.openid)
    throw new AppError('只有病例作者可以发布', { code: 'FORBIDDEN', statusCode: 403 })
  if (record.problem.medicalReviewStatus !== 'approved')
    throw new AppError('病例必须先通过医学审核', { code: 'STATE_CONFLICT', statusCode: 409 })
  const latest = [...record.reviews].reverse().find((review) => review.decision === 'approved')
  if (!latest || latest.caseDigest !== demoCaseDigest(record.problem, record.draft)) {
    record.problem.medicalReviewStatus = 'not_submitted'
    writeRecords(records)
    throw new AppError('审核摘要已变化，请重新提交审核', { code: 'STATE_CONFLICT', statusCode: 409 })
  }
  records[index].problem.status = '已发布'
  records[index].problem.publishTime = new Date().toISOString()
  writeRecords(records)
  return records[index].problem
}

export function demoSubmitCaseForReview(id: string): Problem | undefined {
  const user = currentDemoUser()
  const records = normalizedRecords()
  const record = records.find((item) => item.problem.id === id)
  if (!record || record.authorOpenid !== user.openid)
    throw new AppError('只有病例作者可以提交审核', { code: 'FORBIDDEN', statusCode: 403 })
  if (record.problem.medicalReviewStatus === 'approved')
    throw new AppError('已审核病例不可重复提交', { code: 'STATE_CONFLICT', statusCode: 409 })
  if (record.problem.medicalReviewStatus === 'pending') return record.problem
  record.problem.status = '待审核'
  record.problem.medicalReviewStatus = 'pending'
  writeRecords(records)
  return record.problem
}

export function demoReviewQueue(status = 'pending'): Problem[] {
  return normalizedRecords()
    .filter((record) => record.problem.medicalReviewStatus === status)
    .map((record) => record.problem)
}

export function demoReviewView(id: string): MedicalReviewView | undefined {
  const user = getSessionContext()
  if (
    !user ||
    user.role !== 'teacher' ||
    (!user.permissions?.includes('medical_review') && user.openid !== 'demo_reviewer')
  ) {
    throw new AppError('需要医学审核权限', { code: 'FORBIDDEN', statusCode: 403 })
  }
  const record = normalizedRecords().find((item) => item.problem.id === id)
  if (!record) return undefined
  return {
    ...record.problem,
    caseDefinition: record.draft.caseDefinition,
    rubric: record.draft.rubric,
    currentDigest: demoCaseDigest(record.problem, record.draft),
    authorNickname: record.authorOpenid,
    reviews: record.reviews,
  }
}

export function demoDecideCaseReview(
  id: string,
  decision: 'approved' | 'rejected',
  comment: string,
): Problem | undefined {
  const user = getSessionContext()
  if (
    !user ||
    user.role !== 'teacher' ||
    (!user.permissions?.includes('medical_review') && user.openid !== 'demo_reviewer')
  ) {
    throw new AppError('需要医学审核权限', { code: 'FORBIDDEN', statusCode: 403 })
  }
  if (decision === 'rejected' && comment.trim().length < 5)
    throw new AppError('退回意见至少需要 5 个字符', { code: 'VALIDATION_ERROR', statusCode: 422 })
  const records = normalizedRecords()
  const record = records.find((item) => item.problem.id === id)
  if (!record) return undefined
  if (record.authorOpenid === user.openid)
    throw new AppError('作者不能审核自己的病例', { code: 'FORBIDDEN', statusCode: 403 })
  if (record.problem.medicalReviewStatus !== 'pending')
    throw new AppError('病例不在待审核状态', { code: 'STATE_CONFLICT', statusCode: 409 })
  const review: DemoReview = {
    id: `review-${Date.now()}`,
    reviewerOpenid: user.openid,
    reviewerName: user.nickName,
    decision,
    comment,
    problemVersion: record.problem.version || 1,
    caseDigest: demoCaseDigest(record.problem, record.draft),
    createdAt: new Date().toISOString(),
  }
  record.reviews.push(review)
  record.problem.medicalReviewStatus = decision
  record.problem.status = decision === 'approved' ? '待审核' : '已拒绝'
  writeRecords(records)
  return record.problem
}
