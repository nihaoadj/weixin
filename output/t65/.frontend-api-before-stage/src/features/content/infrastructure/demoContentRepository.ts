import * as problems from './demoProblemStore'
import * as cases from './demoCaseContentStore'
import { fromProblemView, optional } from '@/shared/mappers/presentation'
import { getSessionContext } from '@/platform/session/context'
import type { ContentRepository } from '@/features/content/domain/ports'
import type { TeacherContentActionSummary } from '@/features/content/domain/teacherActionSummary'
import type { CaseDraftGenerateInput, CaseDraftGenerateResult } from '@/types/case'
import type { UserRole } from '@/types/domain'
import type { Problem } from '@/types/records'
import { AppError } from '@/types/errors'
import { z } from 'zod'
import { storage } from '@/platform/storage/storage'
import type { KnowledgeCardContribution, KnowledgeCardContributionInput } from '@/types/knowledge'
import type {
  TeacherQuestionBankContent,
  TeacherQuestionBankFilters,
  TeacherQuestionBankImportInput,
  TeacherQuestionBankItem,
  TeacherQuestionBankPage,
  TeacherQuestionBankSource,
} from '@/features/content/domain/questionBank'

const demoTimestamp = '2026-09-18T08:30:00.000Z'
// Retained historical seed; retired interfaces never read or mutate it.
const _demoKnowledgeCards: KnowledgeCardContribution[] = [
  {
    id: 1,
    pointCode: 'pathology.inflammation.vascular',
    classCode: 'demo_class_1',
    version: 1,
    cardType: 'recall',
    prompt: '低氧血症时，哪些机制会造成组织供氧不足？',
    options: [],
    explanation: '从通气、弥散、灌注与血红蛋白携氧四个环节逐层定位，再把病例证据与机制对应。',
    reference: '',
    status: 'draft',
    reviewComment: '',
    createdAt: demoTimestamp,
    updatedAt: demoTimestamp,
    aiTitle: '低氧血症知识补充卡',
    sourceType: 'pbl_ai',
    sourceSnapshotId: 901,
    sourcePosition: 0,
    sourceFindingIds: ['gap-hypoxemia', 'reason-evidence'],
    originStudentId: 1,
    originStudentName: '演示学生',
    targetStudentIds: [1],
  },
]
const _demoKnowledgeCardOwners = new Map<number, string>([[1, 'demo_teacher']])
let demoQuestionBankItems: TeacherQuestionBankItem[] = []
let nextDemoBankItemId = 60001
const demoBankItemOwners = new Map<number, string>()
const demoBankImportReceipts = new Map<string, { digest: string; itemId: number }>()
const demoBankSources = new Map<string, { digest: string; itemId: number }>()
const demoBankArchiveReceipts = new Map<string, { itemId: number; version: number }>()
const bankSnapshotKey = 'content:t64-question-bank'
const bankSnapshotSchema = z.object({
  items: z.array(
    z.object({
      id: z.number().int(),
      version: z.number().int(),
      status: z.enum(['active', 'archived']),
      taskType: z.enum(['retest', 'knowledge_review', 'discussion', 'micro_drill']),
      title: z.string(),
      prompt: z.string(),
      options: z.array(z.string()),
      answer: z.record(z.string(), z.unknown()),
      explanation: z.string(),
      pointCodes: z.array(z.string()),
      dimensionIds: z.array(z.string()),
      medicalReviewStatus: z.string().nullable(),
      updatedAt: z.string(),
    }),
  ),
  nextId: z.number().int(),
  owners: z.array(z.tuple([z.number().int(), z.string()])),
  imports: z.array(z.tuple([z.string(), z.object({ digest: z.string(), itemId: z.number().int() })])),
  sources: z.array(z.tuple([z.string(), z.object({ digest: z.string(), itemId: z.number().int() })])),
  deletions: z.array(z.tuple([z.string(), z.object({ itemId: z.number().int(), version: z.number().int() })])),
})

function demoBankSnapshot() {
  return bankSnapshotSchema.parse({
    items: demoQuestionBankItems,
    nextId: nextDemoBankItemId,
    owners: [...demoBankItemOwners],
    imports: [...demoBankImportReceipts],
    sources: [...demoBankSources],
    deletions: [...demoBankArchiveReceipts],
  })
}

function hydrateDemoQuestionBank(): void {
  const saved = storage.read(bankSnapshotKey, bankSnapshotSchema.optional(), undefined)
  if (!saved) return
  restoreDemoQuestionBank(saved)
}

function restoreDemoQuestionBank(saved: z.infer<typeof bankSnapshotSchema>): void {
  demoQuestionBankItems = saved.items
  nextDemoBankItemId = saved.nextId
  demoBankItemOwners.clear()
  for (const [id, owner] of saved.owners) demoBankItemOwners.set(id, owner)
  demoBankImportReceipts.clear()
  for (const [key, receipt] of saved.imports) demoBankImportReceipts.set(key, receipt)
  demoBankSources.clear()
  for (const [key, source] of saved.sources) demoBankSources.set(key, source)
  demoBankArchiveReceipts.clear()
  for (const [key, receipt] of saved.deletions) demoBankArchiveReceipts.set(key, receipt)
}

function changeDemoQuestionBank(change: () => void): void {
  const before = demoBankSnapshot()
  try {
    change()
    storage.write(bankSnapshotKey, demoBankSnapshot(), bankSnapshotSchema)
  } catch (error) {
    restoreDemoQuestionBank(before)
    throw error
  }
}
type DemoTeacherQuestionBankSourcePort = {
  getTeacherQuestionBankSource(sourceId: string): Promise<TeacherQuestionBankSource>
}
let demoQuestionBankSource: DemoTeacherQuestionBankSourcePort | undefined
export const configureDemoTeacherQuestionBankSource = (source: DemoTeacherQuestionBankSourcePort) => {
  demoQuestionBankSource = source
}

function retiredContent(flow: string): never {
  throw new AppError(`${flow}流程已退役`, { code: 'RETIRED_FLOW', statusCode: 409 })
}

function requireUser(role?: UserRole) {
  const user = getSessionContext()
  if (!user) throw new AppError('请先登录', { code: 'AUTH_REQUIRED', statusCode: 401 })
  if (role && user.role !== role) throw new AppError('无权执行此操作', { code: 'FORBIDDEN', statusCode: 403 })
  return user
}

function assertTeacherUnchanged(openid: string): void {
  if (requireUser('teacher').openid !== openid)
    throw new AppError('教师身份已变化，请重新操作', { code: 'STATE_CONFLICT', statusCode: 409 })
}

function questionBankContent(value: TeacherQuestionBankContent): TeacherQuestionBankContent {
  return {
    taskType: value.taskType,
    title: value.title.trim(),
    prompt: value.prompt.trim(),
    options: value.options.map((option) => option.trim()),
    answer: { ...value.answer },
    explanation: value.explanation.trim(),
    pointCodes: [...value.pointCodes],
    dimensionIds: [...value.dimensionIds],
  }
}

function copyQuestionBankContent(value: TeacherQuestionBankContent): TeacherQuestionBankContent {
  return {
    taskType: value.taskType,
    title: value.title,
    prompt: value.prompt,
    options: [...value.options],
    answer: { ...value.answer },
    explanation: value.explanation,
    pointCodes: [...value.pointCodes],
    dimensionIds: [...value.dimensionIds],
  }
}

function canonicalJson(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(',')}]`
  if (value && typeof value === 'object') {
    return `{${Object.entries(value)
      .sort(([left], [right]) => (left < right ? -1 : left > right ? 1 : 0))
      .map(([key, item]) => `${JSON.stringify(key)}:${canonicalJson(item)}`)
      .join(',')}}`
  }
  return JSON.stringify(value) ?? 'null'
}

function questionBankSourceView(source: TeacherQuestionBankSource): TeacherQuestionBankSource {
  return {
    sourceType: source.sourceType,
    sourceId: source.sourceId,
    sourceDigest: source.sourceDigest,
    ...copyQuestionBankContent(source),
  }
}

function assertQuestionBankContent(value: TeacherQuestionBankContent) {
  const normalized = questionBankContent(value)
  if (
    !normalized.title ||
    normalized.title.length > 200 ||
    !normalized.prompt ||
    normalized.prompt.length > 2000 ||
    normalized.explanation.length > 2000
  )
    throw new AppError('题库标题、题干或解析长度无效', { code: 'VALIDATION_ERROR' })
  if (
    !normalized.pointCodes.length ||
    normalized.pointCodes.length > 3 ||
    new Set(normalized.pointCodes).size !== normalized.pointCodes.length
  )
    throw new AppError('题库目标无效', { code: 'VALIDATION_ERROR' })
  if (new Set(normalized.dimensionIds).size !== normalized.dimensionIds.length || normalized.dimensionIds.length > 6)
    throw new AppError('题库能力维度无效', { code: 'VALIDATION_ERROR' })
  if (normalized.taskType === 'retest' || normalized.taskType === 'knowledge_review') {
    const answer = normalized.answer.correct_option
    if (
      normalized.options.length < 2 ||
      normalized.options.length > 6 ||
      new Set(normalized.options).size !== normalized.options.length ||
      !Number.isInteger(answer) ||
      typeof answer !== 'number' ||
      answer < 0 ||
      answer >= normalized.options.length ||
      !normalized.explanation
    )
      throw new AppError('客观题选项、答案或解析无效', { code: 'VALIDATION_ERROR' })
  } else if (
    normalized.options.length ||
    (normalized.taskType === 'discussion' && Object.keys(normalized.answer).length)
  ) {
    throw new AppError('非客观题不能包含选项或自由评分答案', { code: 'VALIDATION_ERROR' })
  }
  if (normalized.taskType === 'micro_drill' && !normalized.dimensionIds.length)
    throw new AppError('推理题必须保留能力维度', { code: 'VALIDATION_ERROR' })
  const text = [normalized.title, normalized.prompt, normalized.explanation, ...normalized.options]
    .join('\n')
    .toLocaleLowerCase()
  if (['student_id', 'snapshot_id', '学号：', '学生姓名：'].some((marker) => text.includes(marker)))
    throw new AppError('题目可能包含学生身份或诊断标识，请先去标识化', { code: 'VALIDATION_ERROR' })
}

function makeQuestionBankItem(
  id: number,
  value: TeacherQuestionBankContent,
  medicalReviewStatus: string | null,
  version = 1,
): TeacherQuestionBankItem {
  const normalized = questionBankContent(value)
  return {
    id,
    version,
    status: 'active',
    ...normalized,
    medicalReviewStatus,
    updatedAt: new Date().toISOString(),
  }
}

const demoTeacherQuestionBankSamples: Array<{ id: number; content: TeacherQuestionBankContent }> = [
  {
    id: 640001,
    content: {
      taskType: 'retest',
      title: 'Demo 样例：细胞损伤与适应',
      prompt: 'Demo 合成单选题：可逆性细胞损伤早期最常见的形态学变化是什么？',
      options: ['细胞肿胀', '核碎裂', '广泛纤维化', '恶性细胞浸润'],
      answer: { correct_option: 0 },
      explanation: '细胞膜离子泵功能受损可导致钠、水进入细胞，形成细胞肿胀；核碎裂属于不可逆损伤的核变化。',
      pointCodes: ['pathology.cell-injury.reversible'],
      dimensionIds: [],
    },
  },
  {
    id: 640002,
    content: {
      taskType: 'retest',
      title: 'Demo 样例：炎症',
      prompt: 'Demo 合成单选题：急性炎症中，微血管通透性增加最直接的结果是什么？',
      options: ['血浆蛋白和液体进入组织间隙', '血液黏度立即降低', '血管内皮细胞数量增加', '局部组织液停止流动'],
      answer: { correct_option: 0 },
      explanation: '通透性增加促使含蛋白液体外渗，形成渗出并造成组织水肿。',
      pointCodes: ['pathology.inflammation.vascular'],
      dimensionIds: [],
    },
  },
  {
    id: 640003,
    content: {
      taskType: 'retest',
      title: 'Demo 样例：循环障碍',
      prompt: 'Demo 合成单选题：慢性静脉回流受阻时，局部最符合淤血的变化是什么？',
      options: [
        '静脉和毛细血管内血量增加',
        '动脉血流突然完全中断',
        '组织内细胞外液全部消失',
        '淋巴管扩张并替代动脉供血',
      ],
      answer: { correct_option: 0 },
      explanation: '淤血由静脉回流障碍引起，表现为局部静脉及毛细血管内血量增加。',
      pointCodes: ['pathology.circulatory.congestion'],
      dimensionIds: [],
    },
  },
]

export class DemoContentRepository implements ContentRepository {
  constructor() {
    hydrateDemoQuestionBank()
  }

  /** Called only by the Demo App bootstrap; never by a read or API adapter. */
  ensureDemoContentSamples(): void {
    cases.ensureDemoGuidedCaseSamples()

    const existingIds = new Set(demoQuestionBankItems.map((item) => item.id))
    const missing = demoTeacherQuestionBankSamples.filter((sample) => !existingIds.has(sample.id))
    for (const sample of missing) assertQuestionBankContent(sample.content)

    const earlyCellInjurySample = demoTeacherQuestionBankSamples.find((sample) => sample.id === 640001)
    const earlyCellInjuryItem = demoQuestionBankItems.find((item) => item.id === 640001)
    const upgradeEarlyCellInjuryPointCode = (() => {
      if (
        !earlyCellInjurySample ||
        !earlyCellInjuryItem ||
        earlyCellInjuryItem.status !== 'active' ||
        earlyCellInjuryItem.version !== 1 ||
        demoBankItemOwners.get(earlyCellInjuryItem.id) !== 'demo_teacher' ||
        canonicalJson(earlyCellInjuryItem.pointCodes) !== canonicalJson(['pathology.cell-injury.adaptation'])
      )
        return false

      const {
        id: _id,
        version: _version,
        status: _status,
        medicalReviewStatus: _review,
        updatedAt: _updatedAt,
        ...actualContent
      } = earlyCellInjuryItem
      const { pointCodes: _pointCodes, ...actualContentWithoutPointCodes } = actualContent
      const { pointCodes: _expectedPointCodes, ...expectedContentWithoutPointCodes } = earlyCellInjurySample.content
      return canonicalJson(actualContentWithoutPointCodes) === canonicalJson(expectedContentWithoutPointCodes)
    })()

    const nextId = Math.max(
      nextDemoBankItemId,
      ...demoQuestionBankItems.map((item) => item.id + 1),
      ...demoTeacherQuestionBankSamples.map((sample) => sample.id + 1),
    )
    if (!missing.length && nextId === nextDemoBankItemId && !upgradeEarlyCellInjuryPointCode) return

    changeDemoQuestionBank(() => {
      demoQuestionBankItems = [
        ...missing.map((sample) => makeQuestionBankItem(sample.id, sample.content, null)),
        ...demoQuestionBankItems.map((item) =>
          upgradeEarlyCellInjuryPointCode && item.id === 640001 && earlyCellInjurySample
            ? { ...item, pointCodes: [...earlyCellInjurySample.content.pointCodes] }
            : item,
        ),
      ]
      for (const sample of missing) demoBankItemOwners.set(sample.id, 'demo_teacher')
      nextDemoBankItemId = nextId
    })
  }

  async getTeacherContentActionSummary(): Promise<TeacherContentActionSummary> {
    const user = requireUser('teacher')
    const casesSummary = cases.demoCaseActionCounts()
    const reviewer = Boolean(user.permissions?.includes('medical_review'))
    return {
      casesDraft: casesSummary.casesDraft,
      casesRejected: casesSummary.casesRejected,
      casesApproved: casesSummary.casesApproved,
      questionsDraft: 0,
      questionsRejected: 0,
      cardsDraft: 0,
      cardsRejected: 0,
      medicalCasesPending: reviewer ? casesSummary.medicalCasesPending : null,
      medicalCardsPending: reviewer ? 0 : null,
      asOf: new Date().toISOString(),
    }
  }
  async getTeacherQuestionBankSource(sourceId: string): Promise<TeacherQuestionBankSource> {
    const user = requireUser('teacher')
    if (!demoQuestionBankSource) throw new AppError('Demo 题库来源尚未接入', { code: 'UNSUPPORTED_OPERATION' })
    const source = await demoQuestionBankSource.getTeacherQuestionBankSource(sourceId)
    assertTeacherUnchanged(user.openid)
    return questionBankSourceView(source)
  }

  async listTeacherQuestionBank(filters: TeacherQuestionBankFilters = {}): Promise<TeacherQuestionBankPage> {
    const user = requireUser('teacher')
    const status = filters.status || 'active'
    if (!['active', 'archived'].includes(status)) throw new AppError('题库状态无效', { code: 'VALIDATION_ERROR' })
    const query = filters.query?.trim().toLocaleLowerCase()
    const all = demoQuestionBankItems
      .filter(() => status !== 'archived')
      .filter((item) => demoBankItemOwners.get(item.id) === user.openid && item.status === status)
      .filter((item) => !filters.pointCode || item.pointCodes.includes(filters.pointCode))
      .filter((item) => !filters.taskType || item.taskType === filters.taskType)
      .filter((item) => !query || item.title.toLocaleLowerCase().includes(query))
      .sort((left, right) => right.updatedAt.localeCompare(left.updatedAt))
    const limit = Math.min(100, Math.max(1, filters.limit ?? 20))
    const offset = Math.max(0, filters.offset ?? 0)
    return { items: all.slice(offset, offset + limit).map((item) => ({ ...item })), total: all.length, limit, offset }
  }

  async getTeacherQuestionBankItem(id: number): Promise<TeacherQuestionBankItem> {
    const user = requireUser('teacher')
    const item = demoQuestionBankItems.find(
      (candidate) => candidate.id === id && candidate.status === 'active' && demoBankItemOwners.get(id) === user.openid,
    )
    if (!item) throw new AppError('个人题库题目不存在', { code: 'RESOURCE_NOT_FOUND', statusCode: 404 })
    return {
      ...item,
      options: [...item.options],
      pointCodes: [...item.pointCodes],
      dimensionIds: [...item.dimensionIds],
      answer: { ...item.answer },
    }
  }

  async importTeacherQuestionBankItem(input: TeacherQuestionBankImportInput): Promise<TeacherQuestionBankItem> {
    const user = requireUser('teacher')
    if (!demoQuestionBankSource) throw new AppError('Demo 题库来源尚未接入', { code: 'UNSUPPORTED_OPERATION' })
    if (!input.deidentified || !input.clientRequestId.trim() || input.clientRequestId.length > 100)
      throw new AppError('请确认去标识化并提供请求标识', { code: 'VALIDATION_ERROR' })
    if (
      input.sourceType !== 'route_test_question' ||
      !/^[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}$/i.test(input.sourceId) ||
      !/^[0-9a-f]{64}$/.test(input.sourceDigest)
    )
      throw new AppError('题库来源无效', { code: 'VALIDATION_ERROR' })
    assertQuestionBankContent(input)
    const normalized = questionBankContent(input)
    const requestKey = `${user.openid}:${input.clientRequestId}`
    const requestDigest = canonicalJson([input.sourceType, input.sourceId, input.sourceDigest, normalized])
    const previous = demoBankImportReceipts.get(requestKey)
    if (previous) {
      if (previous.digest !== requestDigest)
        throw new AppError('入库请求标识已用于其他题目', { code: 'STATE_CONFLICT' })
      return this.getTeacherQuestionBankItem(previous.itemId)
    }
    const sourceKey = `${user.openid}:${input.sourceType}:${input.sourceId}:${input.sourceDigest}`
    const bySource = demoBankSources.get(sourceKey)
    if (bySource) throw new AppError('该来源版本已脱钩，不能再次导入', { code: 'STATE_CONFLICT' })

    const source = await this.getTeacherQuestionBankSource(input.sourceId)
    assertTeacherUnchanged(user.openid)
    if (
      source.sourceType !== input.sourceType ||
      source.sourceId !== input.sourceId ||
      source.sourceDigest !== input.sourceDigest
    )
      throw new AppError('来源题目已更新，请重新预览', { code: 'STATE_CONFLICT' })
    if (canonicalJson(copyQuestionBankContent(source)) !== canonicalJson(normalized))
      throw new AppError('首次入库须完整保留来源题目的去标识内容', { code: 'STATE_CONFLICT' })

    const item = makeQuestionBankItem(nextDemoBankItemId, source, null)
    changeDemoQuestionBank(() => {
      nextDemoBankItemId++
      demoQuestionBankItems = [item, ...demoQuestionBankItems]
      demoBankItemOwners.set(item.id, user.openid)
      demoBankImportReceipts.set(requestKey, { digest: requestDigest, itemId: item.id })
      demoBankSources.set(sourceKey, { digest: canonicalJson(normalized), itemId: item.id })
    })
    return {
      ...item,
      options: [...item.options],
      answer: { ...item.answer },
      pointCodes: [...item.pointCodes],
      dimensionIds: [...item.dimensionIds],
    }
  }

  async updateTeacherQuestionBankItem(
    id: number,
    version: number,
    content: TeacherQuestionBankContent,
  ): Promise<TeacherQuestionBankItem> {
    const user = requireUser('teacher')
    const current = await this.getTeacherQuestionBankItem(id)
    assertTeacherUnchanged(user.openid)
    if (current.status !== 'active' || current.version !== version)
      throw new AppError('题库版本已更新', { code: 'STATE_CONFLICT', statusCode: 409 })
    assertQuestionBankContent(content)
    if (content.taskType !== current.taskType)
      throw new AppError('题型不能在题库版本中改变', { code: 'STATE_CONFLICT' })
    const updated = makeQuestionBankItem(id, content, 'not_required', version + 1)
    changeDemoQuestionBank(() => {
      demoQuestionBankItems = demoQuestionBankItems.map((item) => (item.id === id ? updated : item))
    })
    return {
      ...updated,
      options: [...updated.options],
      answer: { ...updated.answer },
      pointCodes: [...updated.pointCodes],
      dimensionIds: [...updated.dimensionIds],
    }
  }

  async archiveTeacherQuestionBankItem(
    id: number,
    version: number,
    clientRequestId: string,
  ): Promise<TeacherQuestionBankItem> {
    await this.deleteTeacherQuestionBankItem(id, version, clientRequestId)
    const deleted = demoQuestionBankItems.find((item) => item.id === id)
    if (!deleted) throw new AppError('个人题库题目不存在', { code: 'RESOURCE_NOT_FOUND', statusCode: 404 })
    return { ...deleted, ...copyQuestionBankContent(deleted) }
  }

  async deleteTeacherQuestionBankItem(id: number, version: number, clientRequestId: string): Promise<void> {
    const user = requireUser('teacher')
    if (!clientRequestId.trim() || clientRequestId.length > 100)
      throw new AppError('删除请求标识无效', { code: 'VALIDATION_ERROR' })
    const key = `${user.openid}:${clientRequestId}`
    const previous = demoBankArchiveReceipts.get(key)
    if (previous) {
      if (previous.itemId !== id || previous.version !== version)
        throw new AppError('删除请求标识已用于其他题目', { code: 'STATE_CONFLICT', statusCode: 409 })
      return
    }
    const current = await this.getTeacherQuestionBankItem(id)
    assertTeacherUnchanged(user.openid)
    if (current.status !== 'active' || current.version !== version)
      throw new AppError('题库版本已更新', { code: 'STATE_CONFLICT', statusCode: 409 })
    changeDemoQuestionBank(() => {
      demoQuestionBankItems = demoQuestionBankItems.map((item) =>
        item.id === id
          ? { ...item, status: 'archived', version: version + 1, updatedAt: new Date().toISOString() }
          : item,
      )
      demoBankArchiveReceipts.set(key, { itemId: id, version })
    })
  }

  async getKnowledgeCardContributions(_pointCode?: string): Promise<KnowledgeCardContribution[]> {
    requireUser()
    return []
  }

  async getKnowledgeCardReviewQueue(): Promise<KnowledgeCardContribution[]> {
    const user = requireUser('teacher')
    if (!user.permissions?.includes('medical_review'))
      throw new AppError('无医学审核权限', { code: 'FORBIDDEN', statusCode: 403 })
    return []
  }

  async createKnowledgeCardContribution(_input: KnowledgeCardContributionInput): Promise<KnowledgeCardContribution> {
    requireUser('teacher')
    return retiredContent('教师补充知识卡')
  }

  async updateKnowledgeCardContribution(
    _id: number,
    _input: KnowledgeCardContributionInput,
  ): Promise<KnowledgeCardContribution> {
    requireUser('teacher')
    return retiredContent('教师补充知识卡')
  }

  async submitKnowledgeCardContribution(_id: number): Promise<KnowledgeCardContribution> {
    requireUser('teacher')
    return retiredContent('教师补充知识卡')
  }

  async reviewKnowledgeCardContribution(
    _id: number,
    _decision: 'approved' | 'rejected',
    _comment: string,
  ): Promise<KnowledgeCardContribution> {
    const user = requireUser('teacher')
    if (!user.permissions?.includes('medical_review'))
      throw new AppError('无医学审核权限', { code: 'FORBIDDEN', statusCode: 403 })
    return retiredContent('教师补充知识卡')
  }

  async disableKnowledgeCardContribution(_id: number): Promise<KnowledgeCardContribution> {
    const user = requireUser('teacher')
    if (!user.permissions?.includes('medical_review'))
      throw new AppError('无医学审核权限', { code: 'FORBIDDEN', statusCode: 403 })
    return retiredContent('教师补充知识卡')
  }

  async getProblems(): Promise<Problem[]> {
    const user = requireUser()
    const stored = problems
      .getProblems()
      .filter((problem) => problem.contentType === 'guided_case' && !cases.demoCaseIsDeleted(problem.id))
      .map(fromProblemView)
    const owners = problems.problemOwners()
    const projected = cases.demoCaseProblems().map(fromProblemView)
    const caseIds = new Set(projected.map((problem) => problem.id))
    const all = [
      ...projected,
      ...stored
        .filter((problem) => !caseIds.has(problem.id))
        .map((problem) => ({
          ...problem,
          allowedActions:
            user.role === 'teacher' && owners[problem.id] === user.openid ? ['edit' as const, 'delete' as const] : [],
        })),
    ]
    if (user.role === 'teacher') return all
    return all.filter(
      (problem) =>
        problem.status === 'published' &&
        (problem.target === 'all' ||
          (problem.target === 'individual'
            ? problem.targetIds?.includes(user?.openid || '')
            : user?.classIds?.some((id) => problem.targetIds?.includes(id)))),
    )
  }

  async findProblem(id: string): Promise<Problem | undefined> {
    return (await this.getProblems()).find((problem) => problem.id === id)
  }

  async saveProblems(_values: Problem[]): Promise<void> {
    requireUser('teacher')
    return retiredContent('开放讨论题')
  }

  async upsertProblem(_problem: Problem): Promise<Problem> {
    requireUser('teacher')
    return retiredContent('开放讨论题')
  }

  async publishProblem(id: string): Promise<Problem | null> {
    requireUser('teacher')
    this.assertActiveCaseWrite(id)
    return retiredContent('病例发布')
  }

  async rejectProblem(id: string): Promise<Problem | null> {
    requireUser('teacher')
    this.assertActiveCaseWrite(id)
    return retiredContent('病例审核')
  }

  async resetProblems(): Promise<Problem[]> {
    requireUser('teacher')
    return retiredContent('旧内容重置')
  }

  private assertActiveCaseWrite(id: string): void {
    const stored = problems.findProblem(id)
    if (stored) {
      problems.assertProblemOwner(id)
      if (stored.contentType !== 'guided_case') retiredContent('开放讨论题')
    }
  }

  async getDemoCaseProblemsAsync(): Promise<Problem[]> {
    return cases.demoCaseProblems().map(fromProblemView)
  }

  async getGuidedCasesAsync(): Promise<Problem[]> {
    return this.getProblems()
  }

  async deleteGuidedCaseAsync(id: string): Promise<void> {
    requireUser('teacher')
    this.assertActiveCaseWrite(id)
    cases.demoDeleteCase(id)
  }

  async getCaseAuthoringAsync(id: string): Promise<CaseDraftGenerateResult | undefined> {
    return cases.demoAuthoring(id)
  }

  async cloneCaseVersionAsync(id: string) {
    const problem = cases.demoCloneCase(id)
    return { id: problem?.id || id, slug: problem?.slug, draft: problem ? cases.demoAuthoring(problem.id) : undefined }
  }

  async publishGuidedCaseAsync(id: string) {
    return (await this.publishProblem(id)) || undefined
  }

  async submitGuidedCaseForReviewAsync(id: string) {
    requireUser('teacher')
    this.assertActiveCaseWrite(id)
    return retiredContent('病例审核')
  }

  async getMedicalReviewQueueAsync(status = 'pending') {
    return cases.demoReviewQueue(status).map(fromProblemView)
  }

  async getMedicalReviewViewAsync(id: string) {
    return optional(cases.demoReviewView(id), fromProblemView)
  }

  async decideGuidedCaseReviewAsync(id: string, decision: 'approved' | 'rejected', comment: string) {
    return optional(cases.demoDecideCaseReview(id, decision, comment), fromProblemView)
  }

  async generateCaseDraftAsync(input: CaseDraftGenerateInput) {
    return cases.demoDraft(input.topic)
  }

  async saveGuidedCaseAsync(
    draft: CaseDraftGenerateResult,
    id?: string,
    metadata?: { slug?: string; knowledgePointCodes?: string[] },
  ) {
    if (id && !cases.demoDraftForProblem(id))
      throw new AppError('病例不存在', { code: 'RESOURCE_NOT_FOUND', statusCode: 404 })
    const problem = fromProblemView(cases.demoSaveCaseDraft(draft, id, metadata))
    return {
      id: problem.id,
      slug: problem.slug,
      status: problem.status,
      medicalReviewStatus: problem.medicalReviewStatus,
    }
  }
}
