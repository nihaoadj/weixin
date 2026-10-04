import { AppError } from '@/types/errors'
import { additionalShowcaseDrafts, showcaseDraft } from './demoSeeds'
import catalog from './pathologyCatalog.generated.json'
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
let demoCaseSequence = 0

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
  deletedAt?: string
  problem: Problem
  draft: CaseDraftGenerateResult
  authorOpenid: string
  reviews: DemoReview[]
}

let beforeCaseChange: ((problemId: string, draft: CaseDraftGenerateResult) => void) | undefined
export function configureDemoCaseBeforeChange(callback: (problemId: string, draft: CaseDraftGenerateResult) => void) {
  beforeCaseChange = callback
}

function builtInProblem(id: string): Problem | undefined {
  const draft = id === 'pathology.cell-injury-showcase' ? showcaseDraft : additionalShowcaseDrafts[id]
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
    medicalReviewStatus: 'not_required',
    knowledgePointCodes: catalog
      .filter((p) => p.case_slug === id)
      .slice(0, 3)
      .map((p) => p.code),
  }
}

export function demoDraftForProblem(id: string): { problem: Problem; draft: CaseDraftGenerateResult } | undefined {
  const record = normalizedRecords().find((item) => item.problem.id === id)
  if (record) return record.deletedAt ? undefined : { problem: record.problem, draft: record.draft }
  const builtIn = builtInProblem(id)
  if (builtIn) {
    const draft = id === 'pathology.cell-injury-showcase' ? showcaseDraft : additionalShowcaseDrafts[id]
    return draft ? { problem: builtIn, draft } : undefined
  }
  return undefined
}

export function demoCaseCatalog(id: string): { problem: RecordProblem; draft: CaseDraftGenerateResult } | undefined {
  const user = getSessionContext()
  if (!user) return undefined
  const target = demoDraftForProblem(id)
  if (target && user.role === 'student' && target.problem.target !== 'all') {
    const allowed =
      target.problem.target === 'individual'
        ? target.problem.targetIds?.includes(user.openid)
        : user.classIds?.some((classId) => target.problem.targetIds?.includes(classId))
    if (!allowed) return undefined
  }
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
      status: '已发布',
    },
  }))
}

function writeRecords(records: DemoCaseRecord[]) {
  storage.write(guidedDraftKey, records, z.array(localCaseRecordSchema))
}

export function demoDraft(topic: string): CaseDraftGenerateResult {
  const point = catalog.find((p) => topic === p.system_code || topic.includes(p.system_label))
  const source =
    point && point.system_code !== 'pathology.cell-injury' ? additionalShowcaseDrafts[point.case_slug] : showcaseDraft
  const draft = cloneDraft(source)
  if (!point) draft.title = `${topic}：病理学讨论（待教师补全）`
  return draft
}

const demoCaseSamplePresentation: Record<string, { title: string; description: string; time: string }> = {
  'pathology.cell-injury-showcase': {
    title: '细胞损伤与适应',
    description: 'Demo 合成：比较可逆损伤与不可逆损伤的形态变化。',
    time: '2026-10-03T08:05:00.000Z',
  },
  'pathology.inflammation-showcase': {
    title: '炎症的病理变化',
    description: 'Demo 合成：梳理血管反应、渗出与炎症细胞迁移。',
    time: '2026-10-03T08:04:00.000Z',
  },
  'pathology.circulatory-showcase': {
    title: '血液循环障碍',
    description: 'Demo 合成：辨析淤血、水肿与血栓形成的机制。',
    time: '2026-10-03T08:03:00.000Z',
  },
  'pathology.repair-showcase': {
    title: '组织修复',
    description: 'Demo 合成：追踪再生、肉芽组织与基质重塑过程。',
    time: '2026-10-03T08:02:00.000Z',
  },
  'pathology.neoplasm-showcase': {
    title: '肿瘤的形态特征',
    description: 'Demo 合成：观察肿瘤细胞异型性及生长行为。',
    time: '2026-10-03T08:01:00.000Z',
  },
}
const earlyDemoCaseSampleTitles: Record<string, string> = {
  'pathology.cell-injury-showcase': '细胞损伤与适应',
  'pathology.inflammation-showcase': '炎症',
  'pathology.circulatory-showcase': '循环障碍',
  'pathology.repair-showcase': '修复',
  'pathology.neoplasm-showcase': '肿瘤',
}
const earlyDemoCaseSampleDescription = 'Demo 合成教学病例，用于教师病例库查看与编辑。'

function upgradeEarlyDemoCaseSample(record: DemoCaseRecord, id: string, sourceDraft: CaseDraftGenerateResult) {
  const legacyTitle = earlyDemoCaseSampleTitles[id]
  const current = demoCaseSamplePresentation[id]
  const allCodes = catalog.filter((point) => point.case_slug === id).map((point) => point.code)
  if (
    record.authorOpenid !== 'demo_teacher' ||
    record.deletedAt ||
    record.problem.version !== 1 ||
    record.reviews.length !== 0 ||
    !legacyTitle ||
    !current ||
    record.problem.title !== legacyTitle ||
    record.draft.title !== legacyTitle ||
    record.problem.description !== earlyDemoCaseSampleDescription ||
    record.draft.description !== earlyDemoCaseSampleDescription ||
    stableStringify(record.problem.knowledgePointCodes || []) !== stableStringify(allCodes)
  )
    return false

  const legacyDraft = cloneDraft({
    ...sourceDraft,
    title: legacyTitle,
    description: earlyDemoCaseSampleDescription,
  })
  if (stableStringify(record.draft) !== stableStringify(legacyDraft)) return false

  const baseProblem = builtInProblem(id)
  if (!baseProblem) return false
  record.problem = {
    ...record.problem,
    title: current.title,
    description: current.description,
    time: current.time,
    knowledgePointCodes: baseProblem.knowledgePointCodes,
  }
  record.draft = cloneDraft({ ...sourceDraft, title: current.title, description: current.description })
  return true
}

/** Add missing built-in teaching cases once from the App Demo bootstrap. */
export function ensureDemoGuidedCaseSamples(): void {
  const records = normalizedRecords()
  const existingIds = new Set(records.map((record) => record.problem.id))
  const samples: DemoCaseRecord[] = []
  let upgradedEarlyFixture = false
  const fixtures = [
    ['pathology.cell-injury-showcase', showcaseDraft] as const,
    ...Object.entries(additionalShowcaseDrafts),
  ]

  for (const [id, sourceDraft] of fixtures) {
    if (existingIds.has(id)) {
      const record = records.find((item) => item.problem.id === id)
      if (record && upgradeEarlyDemoCaseSample(record, id, sourceDraft)) upgradedEarlyFixture = true
      continue
    }
    const baseProblem = builtInProblem(id)
    const sample = demoCaseSamplePresentation[id]
    if (!baseProblem || !sample) continue
    const draft = cloneDraft({ ...sourceDraft, title: sample.title, description: sample.description })
    samples.push({
      problem: {
        ...baseProblem,
        ...sample,
      },
      draft,
      authorOpenid: 'demo_teacher',
      reviews: [],
    })
    existingIds.add(id)
  }

  if (samples.length || upgradedEarlyFixture) writeRecords([...records, ...samples])
}

export function demoCaseProblems(): Problem[] {
  const stored = normalizedRecords()
  const builtIns = ['pathology.cell-injury-showcase', ...Object.keys(additionalShowcaseDrafts)]
    .map(builtInProblem)
    .filter((item): item is Problem => Boolean(item))
  const session = getSessionContext()
  const storedIds = new Set(stored.map((item) => item.problem.id))
  const visibleStored = stored
    .filter((item) => !item.deletedAt)
    .map((item) => {
      const problem = item.problem
      const allowedActions: NonNullable<Problem['allowedActions']> = []
      if (session?.role === 'teacher' && item.authorOpenid === session.openid) {
        allowedActions.push('edit', 'delete')
      }
      return { ...problem, allowedActions }
    })
  return [
    ...builtIns
      .filter((problem) => !storedIds.has(problem.id))
      .map((problem) => ({
        ...problem,
        allowedActions:
          session?.role === 'teacher' && session.openid === 'demo_teacher' ? ['edit' as const, 'delete' as const] : [],
      })),
    ...visibleStored,
  ]
}
export function demoGuidedCases(): Problem[] {
  return demoCaseProblems()
}
export function demoCaseIsDeleted(id: string): boolean {
  return Boolean(normalizedRecords().find((item) => item.problem.id === id)?.deletedAt)
}
export function demoCaseActionCounts() {
  currentDemoUser()
  return { casesDraft: 0, casesRejected: 0, casesApproved: 0, medicalCasesPending: 0 }
}
export function demoAuthoring(id: string): CaseDraftGenerateResult | undefined {
  const user = getSessionContext()
  if (!user || user.role !== 'teacher') return undefined
  const record = normalizedRecords().find((item) => item.problem.id === id)
  if (record) return !record.deletedAt && record.authorOpenid === user.openid ? cloneDraft(record.draft) : undefined
  if (id === 'pathology.cell-injury-showcase' || additionalShowcaseDrafts[id]) {
    return user.openid === 'demo_teacher' ? demoDraftForProblem(id)?.draft : undefined
  }
  return undefined
}
export function demoSaveCaseDraft(
  draft: CaseDraftGenerateResult,
  existingId?: string,
  metadata?: { slug?: string; knowledgePointCodes?: string[] },
): Problem {
  const user = currentDemoUser()
  const records = normalizedRecords()
  const old = existingId ? records.find((item) => item.problem.id === existingId) : undefined
  if (old && old.authorOpenid !== user.openid)
    throw new AppError('只有病例作者可以编辑', { code: 'FORBIDDEN', statusCode: 403 })
  if (old?.deletedAt) throw new AppError('病例不存在', { code: 'RESOURCE_NOT_FOUND', statusCode: 404 })
  const builtIn = existingId ? builtInProblem(existingId) : undefined
  if (builtIn && !old && user.openid !== 'demo_teacher')
    throw new AppError('系统病例只读', { code: 'FORBIDDEN', statusCode: 403 })
  const normalized = cloneDraft(draft)
  if (
    !normalized.title.trim() ||
    !normalized.description.trim() ||
    !normalized.caseDefinition.facts.length ||
    !normalized.rubric.dimensions.length
  )
    throw new AppError('病例内容不完整', { code: 'VALIDATION_ERROR', statusCode: 422 })
  const prior = old
    ? { problem: old.problem, draft: old.draft }
    : existingId
      ? demoDraftForProblem(existingId)
      : undefined
  const boundCodes =
    metadata?.knowledgePointCodes ||
    old?.problem.knowledgePointCodes ||
    builtIn?.knowledgePointCodes ||
    catalog
      .filter((point) =>
        normalized.caseDefinition.practiceBlueprints?.some((blueprint) =>
          blueprint.id.startsWith(`${point.system_code}.`),
        ),
      )
      .map((point) => point.code)
      .slice(0, 3)
  if (
    !boundCodes.length ||
    (metadata?.knowledgePointCodes !== undefined && boundCodes.length > 3) ||
    new Set(boundCodes).size !== boundCodes.length ||
    boundCodes.some((code) => !catalog.some((point) => point.code === code))
  )
    throw new AppError('病例知识点绑定无效', { code: 'VALIDATION_ERROR', statusCode: 422 })
  if (prior) beforeCaseChange?.(prior.problem.id, prior.draft)
  const newId = `demo-case-${Date.now()}-${demoCaseSequence++}`
  const problem: Problem = {
    id: existingId || newId,
    type: '病例分析',
    title: draft.title,
    description: draft.description,
    target: old?.problem.target || 'all',
    status: '已发布',
    time: old?.problem.time || new Date().toISOString(),
    contentType: 'guided_case',
    slug: metadata?.slug || old?.problem.slug || builtIn?.slug || newId,
    specialty: draft.specialty,
    difficulty: draft.difficulty,
    estimatedMinutes: draft.estimatedMinutes,
    version: old ? (old.problem.version || 1) + 1 : builtIn ? (builtIn.version || 1) + 1 : 1,
    opening: draft.caseDefinition.opening,
    medicalReviewStatus: 'not_required',
    knowledgePointCodes: [...boundCodes],
    authorId: old?.problem.authorId,
  }
  writeRecords([
    ...records.filter((item) => item.problem.id !== problem.id),
    {
      problem,
      draft: normalized,
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
    record.problem.medicalReviewStatus = 'not_required'
    record.reviews = []
    writeRecords(records)
  }
  return record?.problem || clone
}
export function demoDeleteCase(id: string): void {
  const user = currentDemoUser()
  const records = normalizedRecords()
  let record = records.find((item) => item.problem.id === id)
  if (record && record.authorOpenid !== user.openid)
    throw new AppError('只有病例作者可以删除', { code: 'FORBIDDEN', statusCode: 403 })
  if (record?.deletedAt) return
  if (!record) {
    const source = demoDraftForProblem(id)
    if (!source) throw new AppError('病例不存在', { code: 'RESOURCE_NOT_FOUND', statusCode: 404 })
    if (user.openid !== 'demo_teacher') throw new AppError('系统病例只读', { code: 'FORBIDDEN', statusCode: 403 })
    record = { ...source, authorOpenid: user.openid, reviews: [] }
    records.push(record)
  }
  beforeCaseChange?.(id, record.draft)
  record.deletedAt = new Date().toISOString()
  writeRecords(records)
}

function retiredCaseOperation(): never {
  throw new AppError('病例审核与发布流程已退役，保存后即可使用', { code: 'RETIRED_FLOW', statusCode: 409 })
}

export function demoPublishCase(_id: string): Problem | undefined {
  currentDemoUser()
  return retiredCaseOperation()
}

export function demoSubmitCaseForReview(_id: string): Problem | undefined {
  currentDemoUser()
  return retiredCaseOperation()
}

export function demoReviewQueue(_status = 'pending'): Problem[] {
  const user = currentDemoUser()
  if (!user.permissions?.includes('medical_review') && user.openid !== 'demo_reviewer')
    throw new AppError('需要医学审核权限', { code: 'FORBIDDEN', statusCode: 403 })
  return []
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
  const record = normalizedRecords().find((item) => item.problem.id === id && !item.deletedAt)
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
  _id: string,
  _decision: 'approved' | 'rejected',
  _comment: string,
): Problem | undefined {
  const user = getSessionContext()
  if (
    !user ||
    user.role !== 'teacher' ||
    (!user.permissions?.includes('medical_review') && user.openid !== 'demo_reviewer')
  ) {
    throw new AppError('需要医学审核权限', { code: 'FORBIDDEN', statusCode: 403 })
  }
  return retiredCaseOperation()
}
