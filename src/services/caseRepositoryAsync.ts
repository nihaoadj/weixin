import { apiRequest, isRemoteApiEnabled } from '@/services/apiClient'
import type {
  CaseAssessment,
  CaseAttempt,
  CaseDraftGenerateInput,
  CaseDraftGenerateResult,
  CaseMessage,
  StageAnswer,
} from '@/types/case'
import type { Problem } from '@/types/domain'

export interface MedicalReviewEntry {
  id: number
  problemId: number
  reviewerId: number
  decision: 'approved' | 'rejected'
  comment: string
  problemVersion: number
  caseDigest: string
  createdAt: string
}

export interface MedicalReviewView extends Problem {
  caseDefinition: CaseDraftGenerateResult['caseDefinition']
  rubric: CaseDraftGenerateResult['rubric']
  currentDigest: string
  authorNickname?: string
  reviews: MedicalReviewEntry[]
}

const snake = (value: unknown): unknown => {
  if (Array.isArray(value)) return value.map(snake)
  if (!value || typeof value !== 'object') return value
  return Object.fromEntries(
    Object.entries(value as Record<string, unknown>).map(([key, item]) => [
      key.replace(/_([a-z])/g, (_, letter: string) => letter.toUpperCase()),
      snake(item),
    ]),
  )
}
const camel = <T>(value: unknown): T => snake(value) as T
function toProblem(value: Record<string, unknown>): Problem {
  return {
    id: String(value.id),
    type: String(value.type) as Problem['type'],
    title: String(value.title || ''),
    description: String(value.description || ''),
    target: value.target as Problem['target'],
    targetLabel: String(value.targetLabel || ''),
    targetIds: (value.targetIds || []) as string[],
    status: value.status === 'published' ? '已发布' : value.status === 'rejected' ? '已拒绝' : '待审核',
    time: String(value.createdAt || ''),
    publishTime: value.publishedAt ? String(value.publishedAt) : undefined,
    contentType: value.contentType as Problem['contentType'],
    slug: value.slug ? String(value.slug) : undefined,
    specialty: String(value.specialty || ''),
    difficulty: value.difficulty as Problem['difficulty'],
    estimatedMinutes: Number(value.estimatedMinutes || 10),
    version: Number(value.version || 1),
    parentProblemId: value.parentProblemId ? Number(value.parentProblemId) : undefined,
    authorId: value.authorId ? Number(value.authorId) : undefined,
    medicalReviewStatus: value.medicalReviewStatus as Problem['medicalReviewStatus'],
    opening: value.opening as Problem['opening'],
    capabilityTags: (value.capabilityTags || []) as string[],
  }
}
function toDraft(value: Record<string, unknown>): CaseDraftGenerateResult {
  return {
    title: String(value.title || ''),
    description: String(value.description || ''),
    specialty: String(value.specialty || ''),
    difficulty: value.difficulty as CaseDraftGenerateResult['difficulty'],
    estimatedMinutes: Number(value.estimatedMinutes || 10),
    caseDefinition: value.caseDefinition as CaseDraftGenerateResult['caseDefinition'],
    rubric: value.rubric as CaseDraftGenerateResult['rubric'],
    generationMode: 'fallback',
    safetyNotice: '合成教学病例，不构成诊疗建议。',
  }
}
const apiAnswer = (answer: StageAnswer) => {
  const convert = (value: unknown): unknown => {
    if (Array.isArray(value)) return value.map(convert)
    if (!value || typeof value !== 'object') return value
    return Object.fromEntries(
      Object.entries(value as Record<string, unknown>).map(([key, item]) => [
        key.replace(/[A-Z]/g, (letter) => `_${letter.toLowerCase()}`),
        convert(item),
      ]),
    )
  }
  return convert(answer)
}
const demoRepository = import.meta.env.VITE_APP_MODE === 'api' ? undefined : () => import('@/services/caseRepository')

async function local() {
  if (!demoRepository) throw new Error('API 模式不包含离线病例数据')
  return demoRepository()
}

export async function getCaseAttemptsAsync(): Promise<CaseAttempt[]> {
  if (!isRemoteApiEnabled()) return (await local()).demoAttempts()
  return camel(await apiRequest({ path: '/attempts' }))
}
export async function getDemoCaseProblemsAsync(): Promise<Problem[]> {
  if (isRemoteApiEnabled()) return []
  return (await local()).demoCaseProblems()
}
export async function getGuidedCasesAsync(): Promise<Problem[]> {
  if (!isRemoteApiEnabled()) return (await local()).demoGuidedCases()
  const problems = await apiRequest<Array<Record<string, unknown>>>({ path: '/problems' })
  return problems
    .map((raw) => toProblem(camel<Record<string, unknown>>(raw)))
    .filter((item) => item.contentType === 'guided_case')
}
export async function getCaseAuthoringAsync(id: string): Promise<CaseDraftGenerateResult | undefined> {
  if (!isRemoteApiEnabled()) return (await local()).demoAuthoring(id)
  return toDraft(camel(await apiRequest({ path: `/problems/${id}/authoring` })))
}
export async function cloneCaseVersionAsync(
  id: string,
): Promise<{ id: string; slug?: string; draft?: CaseDraftGenerateResult }> {
  if (!isRemoteApiEnabled()) {
    const problem = (await local()).demoCloneCase(id)
    return {
      id: problem?.id || id,
      slug: problem?.slug,
      draft: problem ? (await local()).demoAuthoring(problem.id) : undefined,
    }
  }
  const cloned = camel<Record<string, unknown>>(
    await apiRequest({ path: `/problems/${id}/clone-version`, method: 'POST' }),
  )
  return {
    id: String(cloned.id),
    slug: cloned.slug ? String(cloned.slug) : undefined,
    draft: toDraft(cloned),
  }
}
export async function publishGuidedCaseAsync(id: string): Promise<Problem | undefined> {
  if (!isRemoteApiEnabled()) return (await local()).demoPublishCase(id)
  return toProblem(camel(await apiRequest({ path: `/problems/${id}/publish`, method: 'POST' })))
}
export async function submitGuidedCaseForReviewAsync(id: string): Promise<Problem | undefined> {
  if (!isRemoteApiEnabled()) return (await local()).demoSubmitCaseForReview(id)
  return toProblem(camel(await apiRequest({ path: `/problems/${id}/medical-review/submit`, method: 'POST' })))
}
export async function getMedicalReviewQueueAsync(status = 'pending'): Promise<Problem[]> {
  if (!isRemoteApiEnabled()) return (await local()).demoReviewQueue(status)
  const queue = await apiRequest<Array<Record<string, unknown>>>({
    path: `/problems/review-queue?status=${encodeURIComponent(status)}`,
  })
  return queue.map((item) => toProblem(camel(item)))
}
export async function getMedicalReviewViewAsync(id: string): Promise<MedicalReviewView | undefined> {
  if (!isRemoteApiEnabled()) return (await local()).demoReviewView(id) as MedicalReviewView | undefined
  const raw = camel<Record<string, unknown>>(await apiRequest({ path: `/problems/${id}/medical-review-view` }))
  return {
    ...toProblem(raw),
    caseDefinition: raw.caseDefinition as MedicalReviewView['caseDefinition'],
    rubric: raw.rubric as MedicalReviewView['rubric'],
    currentDigest: String(raw.currentDigest || ''),
    authorNickname: raw.authorNickname ? String(raw.authorNickname) : undefined,
    reviews: (raw.reviews || []) as MedicalReviewEntry[],
  }
}
export async function decideGuidedCaseReviewAsync(
  id: string,
  decision: 'approved' | 'rejected',
  comment: string,
): Promise<Problem | undefined> {
  if (!isRemoteApiEnabled()) return (await local()).demoDecideCaseReview(id, decision, comment)
  return toProblem(
    camel(await apiRequest({ path: `/problems/${id}/medical-review`, method: 'POST', body: { decision, comment } })),
  )
}
export async function getCaseAttemptAsync(id: string): Promise<CaseAttempt | undefined> {
  if (!isRemoteApiEnabled()) return (await local()).demoFind(id)
  return camel(await apiRequest({ path: `/attempts/${id}` }))
}
export async function startCaseAttemptAsync(problemId: string, retryOfId?: string): Promise<CaseAttempt> {
  if (!isRemoteApiEnabled()) return (await local()).demoStart(problemId, retryOfId)
  return camel(
    await apiRequest({
      path: `/problems/${problemId}/attempts`,
      method: 'POST',
      body: { retry_of_id: retryOfId ? Number(retryOfId) : null },
    }),
  )
}
export async function sendPatientMessageAsync(id: string, content: string): Promise<CaseMessage> {
  if (!isRemoteApiEnabled()) {
    const attempt = (await local()).demoMessage(id, content)
    return attempt.messages[attempt.messages.length - 1]
  }
  return camel(await apiRequest({ path: `/attempts/${id}/messages`, method: 'POST', body: { content } }))
}
export async function submitCaseStageAsync(id: string, answer: StageAnswer): Promise<void> {
  if (!isRemoteApiEnabled()) {
    ;(await local()).demoSubmit(id, answer)
    return
  }
  await apiRequest({
    path: `/attempts/${id}/stages/${answer.stageId}/submit`,
    method: 'POST',
    body: { answer: apiAnswer(answer) },
  })
}
export async function completeCaseAttemptAsync(id: string): Promise<CaseAssessment> {
  if (!isRemoteApiEnabled()) return (await local()).demoComplete(id)
  return camel(await apiRequest({ path: `/attempts/${id}/complete`, method: 'POST' }))
}
export async function getCaseAssessmentAsync(id: string): Promise<CaseAssessment | undefined> {
  if (!isRemoteApiEnabled()) return (await local()).demoAssessments().find((item) => item.attemptId === id)
  return camel(await apiRequest({ path: `/attempts/${id}/assessment` }))
}
export async function generateCaseDraftAsync(input: CaseDraftGenerateInput): Promise<CaseDraftGenerateResult> {
  if (!isRemoteApiEnabled()) return (await local()).demoDraft(input.topic)
  return camel(
    await apiRequest({
      path: '/problems/case-drafts/generate',
      method: 'POST',
      body: { topic: input.topic, learner_level: input.learnerLevel, learning_objectives: input.learningObjectives },
    }),
  )
}

export async function saveGuidedCaseAsync(
  draft: CaseDraftGenerateResult,
  id?: string,
  metadata?: { slug?: string },
): Promise<{
  id: string
  slug?: string
  status?: Problem['status']
  medicalReviewStatus?: Problem['medicalReviewStatus']
}> {
  const body = {
    type: '病例分析',
    title: draft.title,
    description: draft.description,
    target: 'all',
    target_label: '全体学生',
    target_ids: [],
    content_type: 'guided_case',
    slug: metadata?.slug || (id ? undefined : `case-${Date.now()}`),
    specialty: draft.specialty,
    difficulty: draft.difficulty,
    estimated_minutes: draft.estimatedMinutes,
    version: 1,
    case_definition: apiAnswer(draft.caseDefinition as never),
    rubric: apiAnswer(draft.rubric as never),
    capability_tags: [...new Set((draft.caseDefinition?.practiceBlueprints || []).map((item) => item.dimensionId))],
  }
  if (!isRemoteApiEnabled()) {
    const problem = (await local()).demoSaveCaseDraft(draft, id)
    return {
      id: problem.id,
      slug: problem.slug,
      status: problem.status,
      medicalReviewStatus: problem.medicalReviewStatus,
    }
  }
  const saved = toProblem(
    camel(await apiRequest({ path: id ? `/problems/${id}` : '/problems', method: id ? 'PUT' : 'POST', body })),
  )
  return {
    id: saved.id,
    slug: saved.slug,
    status: saved.status,
    medicalReviewStatus: saved.medicalReviewStatus,
  }
}
