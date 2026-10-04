import { z } from 'zod'
import { storage, storageKeys } from '@/platform/storage/storage'
import { getSessionContext } from '@/platform/session/context'
import { AppError } from '@/types/errors'
import type { LearningRoutesPort } from '../domain/learningRoutesPort'
import type {
  LearningRouteDetail,
  LearningRouteReading,
  LearningRouteStep,
  LearningRouteSummary,
} from '../domain/learningRoutes'
import type { RouteCaseMessage, RouteCaseMessageResult, RouteCaseRead, RouteCaseStage } from '../domain/routeCases'
import { ROUTE_CASE_STAGES } from '../domain/routeCases'
import type {
  FinalTestAnswer,
  FinalTestGradingStatus,
  FinalTestQuestionType,
  FinalTestRubricCriterion,
  FinalTestRubricResult,
  EditableTeacherFinalTestQuestion,
  LearningResult,
  LearningResultTutorThread,
  StudentFinalTest,
  StudentFinalTestQuestion,
  TeacherFinalTest,
  TeacherFinalTestQuestion,
  TeacherFinalTestReviewQueueFilters,
  TeacherFinalTestReviewQueueItem,
  TeacherFinalTestReviewQueueKind,
  TeacherFinalTestReviewQueuePage,
} from '../domain/finalTests'

type State = {
  studentOpenid: string
  publishedAt?: string
  sourceSessionId?: string
  summary: LearningRouteSummary
  detail: LearningRouteDetail
  reading: Record<string, LearningRouteReading>
  cases: Record<string, RouteCaseRead>
  test: StudentFinalTest
  teacherTest?: TeacherFinalTest
  gradingQuestions?: TeacherFinalTestQuestion[]
  result?: LearningResult
  tutor?: LearningResultTutorThread
  tutorReceipts?: Record<string, { fingerprint: string; thread: LearningResultTutorThread }>
  receipts: Record<string, { fingerprint: string; value: unknown }>
  submissions: Record<string, { fingerprint: string; resultId: string }>
}
const demoCaseStages: RouteCaseStage[] = [
  {
    phase: 'pathology_recognition',
    goals: [
      { goalId: 'inflammation-vessels', objective: '识别局部红、热对应的血管变化。' },
      { goalId: 'inflammation-edema', objective: '结合组织肿胀与中性粒细胞聚集描述炎症形态。' },
    ],
    prompt: '这例局部红肿中，哪些事实提示急性炎症的关键病理变化？',
  },
  {
    phase: 'mechanism_explanation',
    goals: [
      { goalId: 'inflammation-flow', objective: '解释小血管扩张如何产生局部红、热。' },
      { goalId: 'inflammation-exudate', objective: '解释通透性升高与组织水肿的联系。' },
    ],
    prompt: '请把血流和通透性变化分别对应到病例表现。',
  },
  {
    phase: 'evidence_judgment',
    goals: [
      { goalId: 'inflammation-evidence', objective: '用水肿和中性粒细胞聚集支持病理判断。' },
      { goalId: 'inflammation-uncertainty', objective: '说明现有事实不能确定的内容。' },
    ],
    prompt: '哪些病例证据支持你的判断，还有什么需要核对？',
  },
  {
    phase: 'summary_reflection',
    goals: [
      { goalId: 'summary_reflection.reasoning', objective: '串联病例事实、病理变化、发生机制与判断，总结推理过程。' },
      { goalId: 'summary_reflection.improvement', objective: '反思仍不确定的内容或推理不足，提出具体学习改进。' },
    ],
    prompt: '请回顾你的病例分析，说明推理过程、仍不确定之处和下一次的改进方法。',
  },
]
const uuidSchema = z.string().uuid()
const jsonSchema = z.json()
const reviewKindSchema = z.enum(['teacher', 'ai_direct']).nullable()
const formatVersionSchema = z.enum(['single_choice_v1', 'mixed_v2']).default('single_choice_v1')
const questionTypeSchema = z.enum(['single_choice', 'multiple_choice', 'short_answer']).default('single_choice')
const rubricCriterionSchema = z
  .object({ criterionId: z.string(), description: z.string(), maxPoints: z.literal(10) })
  .strict()
const rubricResultSchema = z
  .object({ criterionId: z.string(), earnedPoints: z.number().int().min(0).max(10), evidence: z.string() })
  .strict()
const testSummarySchema = z
  .object({
    id: uuidSchema,
    title: z.string(),
    questionCount: z.number().int().nonnegative(),
    generationState: z.string(),
    reviewState: z.string(),
    reviewKind: reviewKindSchema,
    canStart: z.boolean(),
    lockReason: z.string().optional(),
    claimExpiresAt: z.string().optional(),
    retryAllowed: z.boolean(),
  })
  .strict()
const routeStepSchema = z
  .object({
    id: uuidSchema,
    position: z.number().int().positive(),
    kind: z.enum(['reading', 'case']),
    title: z.string(),
    goalPointCodes: z.array(z.string()),
    status: z.string(),
    caseId: uuidSchema.optional(),
    completedAt: z.string().optional(),
  })
  .strict()
const summarySchema = z
  .object({
    id: uuidSchema,
    title: z.string(),
    sourceKind: z.enum(['classroom', 'autonomous']),
    scopeStatus: z.enum(['active', 'inactive']),
    sessionLocator: z.string(),
    goalPointCodes: z.array(z.string()),
    status: z.string(),
    nextAction: z.string(),
    progress: z
      .object({ completedSteps: z.number().int().nonnegative(), totalSteps: z.number().int().nonnegative() })
      .strict(),
    updatedAt: z.string(),
    testSummary: testSummarySchema,
    resultId: uuidSchema.optional(),
    generationState: z.string(),
    claimExpiresAt: z.string().optional(),
    retryAllowed: z.boolean(),
  })
  .strict()
const detailSchema = z
  .object({
    summary: summarySchema,
    diagnosisSummary: z.record(z.string(), jsonSchema),
    steps: z.array(routeStepSchema),
    testSummary: testSummarySchema,
    canStartTest: z.boolean(),
    lockReasons: z.array(z.string()),
    routeVersion: z.number().int().positive(),
  })
  .strict()
const readingSchema = z
  .object({
    routeId: uuidSchema,
    step: routeStepSchema,
    sources: z.array(
      z
        .object({
          id: z.string(),
          title: z.string(),
          institution: z.string(),
          url: z.string().optional(),
          version: z.string().optional(),
          sourceType: z.string().optional(),
        })
        .strict(),
    ),
    aiGuide: z.string(),
    sections: z.array(z.object({ title: z.string(), text: z.string() }).strict()),
    learningPoints: z.array(z.string()),
    readingProgress: z
      .object({
        leaseToken: z.string().optional(),
        accumulatedSeconds: z.number().int().nonnegative(),
        lastSeenAt: z.string().optional(),
      })
      .strict(),
  })
  .strict()
const caseMessageSchema = z
  .object({
    id: z.string(),
    role: z.enum(['student', 'assistant']),
    content: z.string(),
    revision: z.number().int().nonnegative(),
    phase: z
      .enum(['pathology_recognition', 'mechanism_explanation', 'evidence_judgment', 'summary_reflection'])
      .optional(),
  })
  .strict()
const caseSchema = z
  .object({
    id: uuidSchema,
    routeId: uuidSchema,
    stepId: uuidSchema,
    syntheticCase: z
      .object({
        title: z.string(),
        publicScenario: z.string(),
        caseFacts: z.array(z.string()),
        targetPointCodes: z.array(z.string()),
      })
      .strict(),
    phase: z.string(),
    revision: z.number().int().nonnegative(),
    status: z.string(),
    goals: z.array(z.object({ goalId: z.string(), objective: z.string() }).strict()),
    stages: z
      .array(
        z
          .object({
            phase: z.enum([
              'pathology_recognition',
              'mechanism_explanation',
              'evidence_judgment',
              'summary_reflection',
            ]),
            goals: z.array(z.object({ goalId: z.string(), objective: z.string() }).strict()),
            prompt: z.string(),
          })
          .strict(),
      )
      .default(() => clone(demoCaseStages)),
    messages: z.array(caseMessageSchema),
    nextPrompt: z.string(),
    safetyNotice: z.string(),
    pendingMessage: z
      .object({
        clientMessageId: z.string(),
        requestRevision: z.number().int(),
        processingState: z.string(),
        retryAllowed: z.boolean(),
        claimExpiresAt: z.string().optional(),
      })
      .strict()
      .optional(),
  })
  .strict()
const studentQuestionSchema = z
  .object({
    id: uuidSchema,
    position: z.number().int().positive(),
    pointCode: z.string(),
    prompt: z.string(),
    questionType: questionTypeSchema,
    options: z.array(z.string()).max(4),
  })
  .strict()
const teacherQuestionSchema = z
  .object({
    id: uuidSchema.nullable(),
    position: z.number().int().positive(),
    primaryPointCode: z.string(),
    prompt: z.string(),
    questionType: questionTypeSchema,
    options: z.array(z.string()).max(4).optional(),
    correctOption: z.number().int().min(0).max(3).nullable().optional(),
    correctOptions: z.array(z.number().int().min(0).max(3)).nullable().optional(),
    referenceAnswer: z.string().nullable().optional(),
    rubric: z.array(rubricCriterionSchema).nullable().optional(),
    explanation: z.string(),
    sourceDigest: z
      .string()
      .regex(/^[0-9a-f]{64}$/)
      .optional(),
  })
  .strict()
const attemptSchema = z
  .object({
    id: uuidSchema,
    status: z.string(),
    version: z.number().int().positive(),
    answers: z.record(
      z.string(),
      z.union([z.number().int().min(0).max(3), z.array(z.number().int().min(0).max(3)).max(4), z.string()]),
    ),
    savedAt: z.string().optional(),
    submittedAt: z.string().optional(),
  })
  .strict()
const studentTestSchema = z
  .object({
    id: uuidSchema,
    title: z.string(),
    reviewKind: reviewKindSchema,
    formatVersion: formatVersionSchema,
    releasedVersion: z.number().int().positive(),
    releasedDigest: z.string(),
    questions: z.array(studentQuestionSchema),
    attempt: attemptSchema.nullable().optional(),
  })
  .strict() as unknown as z.ZodType<StudentFinalTest>
const teacherTestSchema = z
  .object({
    id: uuidSchema,
    routeId: uuidSchema,
    title: z.string(),
    sourceKind: z.literal('classroom'),
    classId: z.number().int().positive(),
    sessionId: z.number().int().positive(),
    studentId: z.number().int().positive(),
    diagnosisSummary: z.record(z.string(), jsonSchema),
    goalPointCodes: z.array(z.string()),
    generationState: z.string(),
    reviewState: z.string(),
    reviewKind: reviewKindSchema,
    currentScopeActive: z.boolean().default(false),
    formatVersion: formatVersionSchema,
    version: z.number().int().positive(),
    draftDigest: z.string(),
    questions: z.array(teacherQuestionSchema),
    releasedAt: z.string().optional(),
    feedbackDraft: z.string(),
  })
  .strict() as unknown as z.ZodType<TeacherFinalTest>
const resultQuestionSchema = studentQuestionSchema
  .extend({
    selectedOption: z.number().int().min(0).max(3).nullable().optional(),
    selectedOptions: z.array(z.number().int().min(0).max(3)).nullable().optional(),
    selectedText: z.string().nullable().optional(),
    correctOption: z.number().int().min(0).max(3).nullable().optional(),
    correctOptions: z.array(z.number().int().min(0).max(3)).nullable().optional(),
    referenceAnswer: z.string().nullable().optional(),
    rubricResults: z.array(rubricResultSchema).nullable().optional(),
    gradingFeedback: z.string().nullable().optional(),
    pointsAwarded: z.number().nonnegative().nullable().optional(),
    pointsPossible: z.number().nonnegative().nullable().optional(),
    explanation: z.string(),
  })
  .strict()
const resultSchema = z
  .object({
    id: uuidSchema,
    routeId: uuidSchema,
    sourceKind: z.enum(['classroom', 'autonomous']),
    goalPointCodes: z.array(z.string()),
    routeSummary: z.record(z.string(), jsonSchema),
    correctCount: z.number().int().nonnegative(),
    questionCount: z.number().int().positive(),
    score: z.number().min(0).max(100),
    submittedAt: z.string(),
    questions: z.array(resultQuestionSchema),
    reviewKind: reviewKindSchema,
    formatVersion: formatVersionSchema,
  })
  .strict() as unknown as z.ZodType<LearningResult>
const gradingStatusSchema = z
  .object({
    status: z.enum(['grading', 'completed']),
    testId: uuidSchema,
    routeId: uuidSchema,
    resultId: uuidSchema.optional(),
    retryAllowed: z.boolean(),
    errorCode: z.string().optional(),
  })
  .strict()
const tutorThreadSchema = z
  .object({
    resultId: uuidSchema,
    revision: z.number().int().nonnegative(),
    processingState: z.enum(['idle', 'processing', 'retry_allowed']),
    pendingMessageId: z.string().optional(),
    messages: z.array(
      z
        .object({
          id: z.string(),
          role: z.enum(['student', 'assistant']),
          questionId: uuidSchema,
          content: z.string(),
          sequence: z.number().int().positive(),
          createdAt: z.string(),
        })
        .strict(),
    ),
  })
  .strict()
const generationReceiptSchema = z
  .object({
    routeId: uuidSchema,
    component: z.enum(['route', 'test']),
    generationState: z.string(),
    claimExpiresAt: z.string().optional(),
  })
  .strict()
const caseResultSchema = z
  .object({
    clientMessageId: z.string(),
    requestRevision: z.number().int(),
    processingState: z.string(),
    retryAllowed: z.boolean(),
    reply: z.string().optional(),
    phase: z.string(),
    revision: z.number().int(),
    decision: z.string().optional(),
    missingElements: z.array(z.string()),
    status: z.string(),
  })
  .strict()
const readingReceiptSchema = z
  .object({
    leaseToken: z.string().optional(),
    accumulatedSeconds: z.number().int().nonnegative(),
    lastSeenAt: z.string().optional(),
  })
  .strict()
const releaseReceiptSchema = z
  .object({
    testId: uuidSchema,
    releasedVersion: z.number().int().positive(),
    releasedDigest: z.string(),
    releasedAt: z.string(),
  })
  .strict()
const receiptValueSchema = z.union([
  detailSchema,
  readingSchema,
  caseResultSchema,
  attemptSchema,
  gradingStatusSchema,
  tutorThreadSchema,
  studentTestSchema,
  teacherTestSchema,
  resultSchema,
  generationReceiptSchema,
  readingReceiptSchema,
  releaseReceiptSchema,
])
const stateSchema = z.array(
  z
    .object({
      studentOpenid: z.string().min(1),
      publishedAt: z.string().datetime({ offset: true }).optional(),
      sourceSessionId: z.string().optional(),
      summary: summarySchema,
      detail: detailSchema,
      reading: z.record(z.string(), readingSchema),
      cases: z.record(z.string(), caseSchema),
      test: studentTestSchema,
      teacherTest: teacherTestSchema.optional(),
      gradingQuestions: z.array(teacherQuestionSchema).optional(),
      result: resultSchema.optional(),
      tutor: tutorThreadSchema.optional(),
      tutorReceipts: z
        .record(z.string(), z.object({ fingerprint: z.string(), thread: tutorThreadSchema }).strict())
        .optional(),
      receipts: z.record(z.string(), z.object({ fingerprint: z.string(), value: receiptValueSchema }).strict()),
      submissions: z.record(z.string(), z.object({ fingerprint: z.string(), resultId: uuidSchema }).strict()),
    })
    .strict(),
) as unknown as z.ZodType<State[]>
const storeKey = storage.scopedKey(storageKeys.learningRoutes, 't44-demo')
const seedMarker = `${storeKey}:seed-version`
const demoStateVersion = 5
const clone = <T>(value: T): T => JSON.parse(JSON.stringify(value)) as T
const now = () => new Date().toISOString()
const uid = () =>
  'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0
    return (c === 'x' ? r : (r & 0x3) | 0x8).toString(16)
  })
const digest = (value: unknown) => {
  const source = JSON.stringify(value)
  return Array.from({ length: 8 }, (_, seed) => {
    let hash = (0x811c9dc5 ^ (seed * 0x9e3779b9)) >>> 0
    for (let i = 0; i < source.length; i++) hash = Math.imul(hash ^ source.charCodeAt(i), 0x01000193) >>> 0
    return hash.toString(16).padStart(8, '0')
  }).join('')
}
function fail(code: string, message: string): never {
  throw new AppError(message, { code, statusCode: code === 'RESOURCE_NOT_FOUND' ? 404 : 409 })
}
function actor() {
  const current = getSessionContext()
  if (!current) fail('AUTH_REQUIRED', '请先登录')
  return current
}
function requireStudent() {
  const current = actor()
  if (current.role !== 'student') fail('ROLE_REQUIRED', '学生身份不可用')
  return current
}
function requireTeacher() {
  const current = actor()
  if (current.role !== 'teacher' || current.openid !== 'demo_teacher') fail('RESOURCE_NOT_FOUND', '资源不存在')
  return current
}
function requireTeacherReadScope() {
  const current = actor()
  if (current.role !== 'teacher') throw new AppError('仅教师可查看课堂学情', { code: 'FORBIDDEN', statusCode: 403 })
  return current.openid === 'demo_teacher'
}
const goals = ['pathology.inflammation.acute']

function questionSet(routeId: string, targetGoals = goals) {
  const tail = (Number.parseInt(routeId.slice(-4), 16) * 10).toString().padStart(12, '0')
  const goalAt = (index: number) => targetGoals[index % targetGoals.length] || goals[0]
  return [
    {
      id: `${routeId.slice(0, 8)}-1000-4000-8000-${(Number(tail) + 1).toString().padStart(12, '0')}`,
      position: 1,
      pointCode: goalAt(0),
      prompt: '急性炎症早期局部发红、发热最直接的血管基础是什么？',
      questionType: 'single_choice' as const,
      options: ['小动脉扩张，局部血流增加', '淋巴回流立即停止', '纤维母细胞大量增殖', '血管内形成成熟肉芽组织'] as [
        string,
        string,
        string,
        string,
      ],
    },
    {
      id: `${routeId.slice(0, 8)}-1000-4000-8000-${(Number(tail) + 2).toString().padStart(12, '0')}`,
      position: 2,
      pointCode: goalAt(1),
      prompt: '血管通透性升高后，最可能出现哪项改变？',
      questionType: 'single_choice' as const,
      options: ['蛋白质丰富的液体外渗', '组织液完全消失', '血管壁增厚并闭塞', '红细胞生成减少'] as [
        string,
        string,
        string,
        string,
      ],
    },
    {
      id: `${routeId.slice(0, 8)}-1000-4000-8000-${(Number(tail) + 3).toString().padStart(12, '0')}`,
      position: 3,
      pointCode: goalAt(2),
      prompt: '判断急性炎症时，哪组证据最有助于联系机制与形态？',
      questionType: 'single_choice' as const,
      options: [
        '充血、水肿与中性粒细胞聚集',
        '瘢痕、钙化与脂肪萎缩',
        '异型核、核分裂与浸润',
        '腺体萎缩、纤维化与化生',
      ] as [string, string, string, string],
    },
  ]
}
const mixedQuestionSet = (routeId: string, targetGoals = goals): StudentFinalTestQuestion[] => {
  const base = questionSet(routeId, targetGoals)
  const pointCode = targetGoals[0] || goals[0]
  return [
    ...base,
    {
      id: `${routeId.slice(0, 8)}-1000-4000-8000-${(Number.parseInt(routeId.slice(-4), 16) * 10 + 4)
        .toString()
        .padStart(12, '0')}`,
      position: 4,
      pointCode,
      prompt: '下列哪些变化共同支持急性炎症的病理判断？',
      questionType: 'multiple_choice',
      options: ['小动脉扩张与局部充血', '成熟瘢痕形成', '血管通透性增加并有渗出', '腺体化生'],
    },
    {
      id: `${routeId.slice(0, 8)}-1000-4000-8000-${(Number.parseInt(routeId.slice(-4), 16) * 10 + 5)
        .toString()
        .padStart(12, '0')}`,
      position: 5,
      pointCode,
      prompt: '结合血管反应、组织水肿和炎症细胞证据，简要说明急性炎症的发生机制。',
      questionType: 'short_answer',
      options: [],
    },
  ]
}
const demoRubric: FinalTestRubricCriterion[] = [
  { criterionId: 'vascular_change', description: '说明小动脉扩张和局部血流增加', maxPoints: 10 },
  { criterionId: 'exudation', description: '说明通透性增加、渗出与组织水肿', maxPoints: 10 },
  { criterionId: 'cellular_evidence', description: '联系中性粒细胞聚集和急性炎症判断', maxPoints: 10 },
]
const teacherQuestionFor = (question: StudentFinalTestQuestion, id?: string): TeacherFinalTestQuestion => {
  const base = {
    id: id || question.id,
    position: question.position,
    primaryPointCode: question.pointCode,
    prompt: question.prompt,
    explanation: '将血流、通透性和组织形态证据联系起来判断。',
  }
  if (question.questionType === 'multiple_choice')
    return {
      ...base,
      questionType: 'multiple_choice',
      options: question.options as [string, string, string, string],
      correctOptions: [0, 2],
    }
  if (question.questionType === 'short_answer')
    return {
      ...base,
      questionType: 'short_answer',
      referenceAnswer:
        '急性炎症早期小动脉扩张使局部血流增加；微血管通透性升高使含蛋白液体外渗并形成水肿；中性粒细胞迁移和聚集支持急性炎症的形态判断。',
      rubric: clone(demoRubric),
    }
  return {
    ...base,
    questionType: 'single_choice',
    options: question.options as [string, string, string, string],
    correctOption: 0,
  }
}
function sourceDigest(question: TeacherFinalTestQuestion): string {
  const payload = {
    id: question.id,
    prompt: question.prompt,
    primary_point_code: question.primaryPointCode,
    question_type: question.questionType,
    explanation: question.explanation,
    options: question.questionType === 'short_answer' ? [] : question.options,
    correct_option: question.questionType === 'single_choice' ? question.correctOption : null,
    correct_options: question.questionType === 'multiple_choice' ? question.correctOptions : null,
    reference_answer: question.questionType === 'short_answer' ? question.referenceAnswer : null,
    rubric:
      question.questionType === 'short_answer'
        ? question.rubric.map((item) => ({
            criterion_id: item.criterionId,
            description: item.description,
            max_points: item.maxPoints,
          }))
        : null,
  }
  return digest(payload)
}

function createState(
  id: string,
  name: string,
  owner: string,
  sourceKind: 'classroom' | 'autonomous',
  stage: 'active' | 'waiting' | 'ready' | 'complete' | 'failed',
  goalPointCodes: string[] = goals,
  scopeStatus: 'active' | 'inactive' = 'active',
  formatVersion: 'single_choice_v1' | 'mixed_v2' = 'mixed_v2',
): State {
  const publishedAt = stage === 'failed' ? undefined : now()
  const routeGoals = goalPointCodes.length ? [...new Set(goalPointCodes)] : goals
  const routeId = id
  const testId = `f0000000-0000-4000-8000-${id.replace(/-/g, '').slice(-12)}`
  const readingId = `a0000000-0000-4000-8000-${id.replace(/-/g, '').slice(-12)}`
  const caseStepId = `b0000000-0000-4000-8000-${id.replace(/-/g, '').slice(-12)}`
  const caseId = `c0000000-0000-4000-8000-${id.replace(/-/g, '').slice(-12)}`
  const testQuestions =
    formatVersion === 'mixed_v2' ? mixedQuestionSet(routeId, routeGoals) : questionSet(routeId, routeGoals)
  const gradingQuestions = testQuestions.map((question) => {
    const testQuestionId = `${testId.slice(0, 8)}-${testId.slice(9, 13)}-4000-8000-${question.id.slice(-12)}`
    const mapped = teacherQuestionFor(question, testQuestionId)
    return { ...mapped, sourceDigest: sourceDigest(mapped) } as TeacherFinalTestQuestion
  })
  const routeCompleted = ['ready', 'complete', 'waiting'].includes(stage)
  const testGeneration = stage === 'failed' ? 'failed' : 'ready'
  const released = sourceKind === 'autonomous' || stage === 'ready' || stage === 'complete' || id.endsWith('006')
  const reviewState = sourceKind === 'autonomous' ? 'not_required' : released ? 'released' : 'pending_review'
  const testSummary = {
    id: testId,
    title: '研讨后最终测试',
    questionCount: testQuestions.length,
    generationState: testGeneration,
    reviewState,
    reviewKind: sourceKind === 'autonomous' ? ('ai_direct' as const) : released ? ('teacher' as const) : null,
    canStart: routeCompleted && released && stage !== 'complete',
    lockReason: routeCompleted ? (released ? undefined : 'TEST_NOT_RELEASED') : 'ROUTE_INCOMPLETE',
    retryAllowed: stage === 'failed',
  }
  const readingComplete = ['waiting', 'ready', 'complete'].includes(stage) || id.endsWith('004')
  const caseComplete = ['waiting', 'ready', 'complete'].includes(stage)
  const steps: LearningRouteStep[] =
    stage === 'failed'
      ? []
      : [
          {
            id: readingId,
            position: 1,
            kind: 'reading',
            title: '理解急性炎症的血管反应',
            goalPointCodes: routeGoals,
            status: readingComplete ? 'completed' : 'available',
            completedAt: readingComplete ? now() : undefined,
          },
          {
            id: caseStepId,
            position: 2,
            kind: 'case',
            title: '分析局部红肿的教学病例',
            goalPointCodes: routeGoals,
            status: caseComplete ? 'completed' : readingComplete ? 'available' : 'locked',
            caseId,
            completedAt: caseComplete ? now() : undefined,
          },
        ]
  const summary: LearningRouteSummary = {
    id: routeId,
    title: name,
    sourceKind,
    scopeStatus,
    sessionLocator: `${sourceKind === 'classroom' ? '课堂研讨' : '自主研讨'} · 急性炎症`,
    goalPointCodes: routeGoals,
    status:
      stage === 'failed'
        ? 'generation_failed'
        : stage === 'complete'
          ? 'completed'
          : routeCompleted
            ? released
              ? 'ready_for_test'
              : 'waiting_teacher'
            : 'learning',
    nextAction:
      stage === 'failed'
        ? 'retry_route'
        : stage === 'complete'
          ? 'view_result'
          : routeCompleted
            ? released
              ? 'test'
              : 'wait_teacher'
            : !readingComplete
              ? 'reading'
              : 'case',
    progress: { completedSteps: steps.filter((x) => x.status === 'completed').length, totalSteps: steps.length },
    updatedAt: now(),
    testSummary,
    resultId: undefined,
    generationState: stage === 'failed' ? 'generation_failed' : 'published',
    retryAllowed: stage === 'failed',
  }
  const detail: LearningRouteDetail = {
    summary,
    diagnosisSummary: {
      outcome: '综合局部充血、水肿与炎症细胞反应，解释急性炎症的形态表现。',
      knowledge_gaps: [{ point_code: routeGoals[0], summary: '血流变化与渗出的衔接需要进一步巩固。' }],
      reasoning_issues: [],
    },
    steps,
    testSummary,
    canStartTest: testSummary.canStart,
    lockReasons: testSummary.canStart ? [] : [testSummary.lockReason || 'ROUTE_INCOMPLETE'],
    routeVersion: 1,
  }
  const reading: LearningRouteReading = {
    routeId,
    step: steps[0] || {
      id: readingId,
      position: 1,
      kind: 'reading',
      title: '理解急性炎症的血管反应',
      goalPointCodes: routeGoals,
      status: 'available',
    },
    sources: [
      {
        id: 'source-demo-inflammation',
        title: '急性炎症与血管反应',
        institution: 'Demo 合成教学资源',
        version: '2026.09',
        sourceType: 'teaching_reference',
      },
    ],
    aiGuide: '阅读时关注血管扩张、通透性变化和炎症细胞迁移之间的顺序关系。',
    sections: [
      {
        title: '血流动力学变化',
        text: '急性炎症早期小动脉扩张，局部血流增加，形成发红和发热；随后血流减慢，使白细胞更容易靠近血管壁。',
      },
      {
        title: '通透性与渗出',
        text: '微血管通透性增加后，含蛋白液体进入组织间隙，造成水肿，并为炎症细胞迁移提供局部环境。',
      },
      { title: '形态与机制', text: '组织切片中的充血、间质水肿和中性粒细胞聚集可以与上述机制对应。' },
    ],
    learningPoints: ['用血流增加解释红、热。', '区分渗出与单纯液体积聚。', '将中性粒细胞聚集与急性炎症阶段联系。'],
    readingProgress: { accumulatedSeconds: readingComplete ? 95 : 0 },
  }
  const caseView: RouteCaseRead = {
    id: caseId,
    routeId,
    stepId: caseStepId,
    syntheticCase: {
      title: '合成教学病例：局部红肿',
      publicScenario: '患者皮肤有局限性红、热、肿，病灶中可见炎症细胞。请按阶段说明关键变化、发生机制和证据判断。',
      caseFacts: ['局部发红并有温度升高', '间质液体增加形成肿胀', '早期可见中性粒细胞聚集'],
      targetPointCodes: routeGoals,
    },
    phase: 'pathology_recognition',
    revision: 0,
    status: 'in_progress',
    goals: clone(demoCaseStages[0].goals),
    stages: clone(demoCaseStages),
    messages: [],
    nextPrompt: demoCaseStages[0].prompt,
    safetyNotice: '这是合成教学病例，仅用于课程学习。',
  }
  if (caseComplete) {
    caseView.phase = 'completed'
    caseView.status = 'completed'
    caseView.goals = []
    caseView.nextPrompt = ''
    caseView.revision = 6
    caseView.messages = [
      {
        id: `${caseId}-m1`,
        role: 'student',
        content: '局部小血管扩张并且通透性增加，含蛋白液体外渗，组织出现水肿，同时有中性粒细胞聚集。',
        revision: 1,
      },
      {
        id: `${caseId}-m2`,
        role: 'assistant',
        content: '你已完成病例学习，可以返回计划继续。',
        phase: 'evidence_judgment',
        revision: 6,
      },
    ]
  }
  if (id.endsWith('004')) {
    caseView.phase = 'mechanism_explanation'
    caseView.revision = 2
    caseView.status = 'in_progress'
  }
  const studentTest: StudentFinalTest = {
    id: testId,
    title: testSummary.title,
    reviewKind: testSummary.reviewKind,
    formatVersion,
    releasedVersion: 1,
    releasedDigest: digest(testQuestions),
    questions: testQuestions,
    attempt: null,
  }
  let teacherTest: TeacherFinalTest | undefined
  if (sourceKind === 'classroom') {
    teacherTest = {
      id: testId,
      routeId,
      title: testSummary.title,
      sourceKind: 'classroom',
      classId: 1,
      sessionId: 1,
      studentId: 1,
      diagnosisSummary: detail.diagnosisSummary,
      goalPointCodes: routeGoals,
      generationState: testGeneration,
      reviewState,
      reviewKind: released ? 'teacher' : null,
      currentScopeActive: scopeStatus === 'active',
      formatVersion,
      version: 1,
      draftDigest: digest(testQuestions),
      questions: clone(gradingQuestions),
      releasedAt: released ? now() : undefined,
      feedbackDraft: '',
    }
  }
  return {
    studentOpenid: owner,
    publishedAt,
    summary,
    detail,
    reading: { [readingId]: reading },
    cases: { [caseId]: caseView },
    test: studentTest,
    teacherTest,
    gradingQuestions: clone(gradingQuestions),
    receipts: {},
    submissions: {},
  }
}

function seeds(): State[] {
  return [
    createState(
      '10000000-0000-4000-8000-000000000003',
      '急性炎症：血管反应与形态',
      'demo_student',
      'autonomous',
      'active',
    ),
    createState(
      '10000000-0000-4000-8000-000000000004',
      '急性炎症：机制与病例证据',
      'demo_student',
      'autonomous',
      'active',
    ),
    createState('10000000-0000-4000-8000-000000000005', '急性炎症课堂研讨', 'demo_student', 'classroom', 'waiting'),
    createState(
      '10000000-0000-4000-8000-000000000006',
      '炎症细胞迁移课堂研讨',
      'demo_student_b',
      'classroom',
      'active',
      goals,
      'inactive',
    ),
    createState(
      '10000000-0000-4000-8000-000000000007',
      '急性炎症：学习结果待查看',
      'demo_student',
      'autonomous',
      'ready',
    ),
    createState(
      '10000000-0000-4000-8000-000000000008',
      '急性炎症课堂学习结果',
      'demo_student',
      'classroom',
      'complete',
    ),
    createState(
      '10000000-0000-4000-8000-000000000009',
      '炎症细胞迁移课堂学习结果',
      'demo_student_b',
      'classroom',
      'complete',
    ),
    createState(
      '10000000-0000-4000-8000-000000000010',
      '急性炎症学习计划生成失败',
      'demo_student',
      'autonomous',
      'failed',
    ),
  ].map((state, i) => {
    if (i === 5 || i === 6) {
      state.result = syntheticSeedResult(state, i === 6)
      state.summary.resultId = state.result.id
      state.summary.status = 'completed'
      state.summary.nextAction = 'view_result'
    }
    return state
  })
}

function syntheticSeedResult(state: State, isZero: boolean): LearningResult {
  const answers = Object.fromEntries(
    state.test.questions.map((question) => [
      question.id,
      question.questionType === 'multiple_choice'
        ? isZero
          ? [1]
          : [0, 2]
        : question.questionType === 'short_answer'
          ? isZero
            ? '尚不能判断。'
            : '小动脉扩张使血流增加，通透性升高使液体渗出并形成水肿。'
          : isZero || question.position === 2
            ? 1
            : 0,
    ]),
  ) as Record<string, FinalTestAnswer>
  return {
    ...gradeDemoResult(state, answers),
    id: `e0000000-0000-4000-8000-${String(isZero ? 9 : 8).padStart(12, '0')}`,
  }
}

function upgradeSeededTests(states: State[]): void {
  const stages = ['active', 'active', 'waiting', 'active', 'ready', 'complete', 'complete', 'failed'] as const
  const testReceiptPrefixes = [
    'test-start:',
    'draft:',
    'grading-retry:',
    'teacher-save:',
    'teacher-changes:',
    'teacher-retry:',
    'teacher-release:',
  ]
  for (const state of states) {
    if (!state.summary.id.startsWith('10000000-0000-4000-8000-')) continue
    const seedIndex = Number(state.summary.id.slice(-12)) - 3
    if (!Number.isInteger(seedIndex) || seedIndex < 0 || seedIndex >= stages.length) continue
    if (state.test.formatVersion !== 'single_choice_v1' || state.test.questions.length !== 3) continue

    const replacement = createState(
      state.summary.id,
      state.summary.title,
      state.studentOpenid,
      state.summary.sourceKind,
      stages[seedIndex],
      state.summary.goalPointCodes,
      state.summary.scopeStatus,
      'mixed_v2',
    )
    const previousResult = state.result
    const syntheticResultId = `e0000000-0000-4000-8000-${String(seedIndex + 3).padStart(12, '0')}`
    const isSyntheticResult = Boolean(previousResult && previousResult.id === syntheticResultId)
    state.test = replacement.test
    state.gradingQuestions = replacement.gradingQuestions
    if (replacement.teacherTest) {
      const previousTeacherTest = state.teacherTest
      state.teacherTest = previousTeacherTest
        ? {
            ...replacement.teacherTest,
            classId: previousTeacherTest.classId,
            sessionId: previousTeacherTest.sessionId,
            studentId: previousTeacherTest.studentId,
            diagnosisSummary: previousTeacherTest.diagnosisSummary,
          }
        : replacement.teacherTest
    }
    if (previousResult && isSyntheticResult) {
      state.result = { ...syntheticSeedResult(state, seedIndex === 6), submittedAt: previousResult.submittedAt }
      state.summary.resultId = state.result.id
    } else {
      state.result = undefined
      state.summary.resultId = undefined
      state.tutor = undefined
      state.tutorReceipts = undefined
      state.summary.updatedAt = now()
    }
    state.submissions = {}
    state.detail.testSummary.generationState = replacement.detail.testSummary.generationState
    for (const key of Object.keys(state.receipts)) {
      if (testReceiptPrefixes.some((prefix) => key.startsWith(prefix))) delete state.receipts[key]
    }
    refreshTest(state)
  }
}

let cached: State[] | undefined
function resetT44Namespace(): State[] {
  cached = seeds()
  storage.write(storeKey, cached, stateSchema)
  storage.write(seedMarker, demoStateVersion, z.number().int())
  return cached
}
function all(): State[] {
  if (cached) return cached
  const parsed = stateSchema.safeParse(storage.readRaw(storeKey))
  const version = storage.readRaw(seedMarker)
  if (!parsed.success || (version !== demoStateVersion && version !== 4 && version !== 3)) return resetT44Namespace()
  cached = parsed.data
  if (version === 3 || version === 4) {
    upgradeSeededTests(cached)
    storage.write(storeKey, cached, stateSchema)
    storage.write(seedMarker, demoStateVersion, z.number().int())
  }
  for (const state of cached) {
    for (const caseValue of Object.values(state.cases)) {
      let phase = ROUTE_CASE_STAGES[0].phase as NonNullable<RouteCaseMessage['phase']>
      for (const message of caseValue.messages) {
        message.phase ??= phase
        if (message.role === 'assistant') {
          if (message.content.includes('进入机制解释')) phase = 'mechanism_explanation'
          if (message.content.includes('进入证据与判断')) phase = 'evidence_judgment'
        }
      }
    }
  }
  return cached
}
function persist() {
  storage.write(storeKey, all(), stateSchema)
}
function refresh(state: State) {
  state.summary.updatedAt = now()
  state.summary.progress = {
    completedSteps: state.detail.steps.filter((x) => x.status === 'completed').length,
    totalSteps: state.detail.steps.length,
  }
  state.summary.testSummary = clone(state.detail.testSummary)
  state.detail.summary = clone(state.summary)
  state.detail.canStartTest = state.summary.testSummary.canStart
  state.detail.testSummary = clone(state.summary.testSummary)
  state.detail.lockReasons = state.detail.canStartTest
    ? []
    : [state.summary.testSummary.lockReason || 'ROUTE_INCOMPLETE']
}
function projectSummary(state: State) {
  const summary = clone(state.summary)
  summary.progress = {
    completedSteps: state.detail.steps.filter((step) => step.status === 'completed').length,
    totalSteps: state.detail.steps.length,
  }
  return summary
}
function findRoute(routeId: string, openid = requireStudent().openid): State {
  const value = all().find((x) => x.summary.id === routeId && x.studentOpenid === openid)
  if (!value) return fail('RESOURCE_NOT_FOUND', '学习计划不存在或当前不可查看')
  return value
}
function findStep(stepId: string): { state: State; step: LearningRouteStep } {
  const state = all().find(
    (x) => x.studentOpenid === requireStudent().openid && x.detail.steps.some((step) => step.id === stepId),
  )
  if (!state) return fail('RESOURCE_NOT_FOUND', '学习步骤不存在或当前不可查看')
  const step = state.detail.steps.find((x) => x.id === stepId)!
  if (step.status === 'locked') return fail('STATE_CONFLICT', 'STEP_LOCKED')
  return { state, step }
}
function findCase(caseId: string): { state: State; value: RouteCaseRead } {
  const state = all().find((x) => x.studentOpenid === requireStudent().openid && x.cases[caseId])
  if (!state) return fail('RESOURCE_NOT_FOUND', '病例学习不存在或当前不可查看')
  const step = state.detail.steps.find((s) => s.id === state.cases[caseId].stepId)
  if (step?.status === 'locked') return fail('STATE_CONFLICT', 'STEP_LOCKED')
  return { state, value: state.cases[caseId] }
}
function fingerprint(value: unknown) {
  return JSON.stringify(value)
}
function repeat<T>(state: State, requestId: string, value: unknown, schema: z.ZodType<T>): T | undefined {
  const existing = state.receipts[requestId]
  if (!existing) return undefined
  if (existing.fingerprint !== fingerprint(value)) return fail('STATE_CONFLICT', 'IDEMPOTENCY_MISMATCH')
  const parsed = schema.safeParse(existing.value)
  if (!parsed.success) {
    resetT44Namespace()
    return fail('STATE_CONFLICT', 'DEMO_STATE_RESET')
  }
  return clone(parsed.data)
}
function remember(state: State, requestId: string, input: unknown, value: unknown) {
  state.receipts[requestId] = { fingerprint: fingerprint(input), value: clone(value) }
}
function refreshTest(state: State) {
  state.summary.progress = {
    completedSteps: state.detail.steps.filter((step) => step.status === 'completed').length,
    totalSteps: state.detail.steps.length,
  }
  const teacher = state.teacherTest
  state.test.reviewKind = teacher?.reviewKind || (state.summary.sourceKind === 'autonomous' ? 'ai_direct' : null)
  state.detail.testSummary.reviewState =
    teacher?.reviewState || (state.summary.sourceKind === 'autonomous' ? 'released' : 'pending_review')
  state.detail.testSummary.reviewKind = state.test.reviewKind
  state.detail.testSummary.generationState = teacher?.generationState || state.detail.testSummary.generationState
  state.detail.testSummary.questionCount = teacher?.questions.length || state.test.questions.length
  const routePublished = state.summary.generationState === 'published'
  const routeDone = state.detail.steps.length > 0 && state.detail.steps.every((s) => s.status === 'completed')
  const generated = state.detail.testSummary.generationState === 'ready'
  const released = state.summary.sourceKind === 'autonomous' || teacher?.reviewState === 'released'
  state.detail.testSummary.canStart = routePublished && routeDone && generated && released && !state.result
  state.detail.testSummary.lockReason = !routeDone
    ? 'ROUTE_INCOMPLETE'
    : !generated
      ? 'TEST_NOT_GENERATED'
      : released
        ? state.result
          ? 'ALREADY_SUBMITTED'
          : undefined
        : 'TEST_NOT_RELEASED'
  state.detail.testSummary.retryAllowed = routePublished && state.detail.testSummary.generationState === 'failed'
  state.summary.testSummary = clone(state.detail.testSummary)
  state.detail.canStartTest = state.detail.testSummary.canStart
  if (state.result) {
    state.summary.status = 'completed'
    state.summary.nextAction = 'view_result'
  } else if (!routePublished) {
    state.summary.status = state.summary.generationState === 'generation_failed' ? 'generation_failed' : 'generating'
    state.summary.nextAction = state.summary.retryAllowed ? 'retry_route' : 'wait_generation'
  } else if (!routeDone) {
    state.summary.status = 'learning'
    state.summary.nextAction = state.detail.steps.find((step) => step.status !== 'completed')?.kind || 'wait_generation'
  } else if (!generated) {
    state.summary.status = 'waiting_test_generation'
    state.summary.nextAction = state.detail.testSummary.retryAllowed ? 'retry_test' : 'wait_generation'
  } else if (!released) {
    state.summary.status = 'waiting_teacher'
    state.summary.nextAction = 'wait_teacher'
  } else {
    state.summary.status = state.test.attempt?.status === 'in_progress' ? 'testing' : 'ready_for_test'
    state.summary.nextAction = 'test'
  }
  state.detail.summary = clone(state.summary)
  state.detail.lockReasons = state.detail.canStartTest
    ? []
    : [state.detail.testSummary.lockReason || 'ROUTE_INCOMPLETE']
}
function ensureCaseResult(
  state: State,
  caseId: string,
  input: string,
  clientMessageId: string,
): RouteCaseMessageResult {
  const caseValue = state.cases[caseId]
  const previous = state.receipts[`case:${caseId}:${clientMessageId}`]
  if (previous) {
    if (previous.fingerprint !== fingerprint(input)) return fail('STATE_CONFLICT', 'IDEMPOTENCY_MISMATCH')
    const parsed = caseResultSchema.safeParse(previous.value)
    if (!parsed.success) {
      resetT44Namespace()
      return fail('STATE_CONFLICT', 'DEMO_STATE_RESET')
    }
    return { ...clone(parsed.data), phase: caseValue.phase, revision: caseValue.revision, status: caseValue.status }
  }
  if (caseValue.phase === 'completed') return fail('STATE_CONFLICT', 'CASE_COMPLETED')
  const expectedTerms: Record<string, string[]> = {
    pathology_recognition: ['红', '肿', '血管', '中性粒', '变化'],
    mechanism_explanation: ['扩张', '通透', '渗出', '机制', '血流'],
    evidence_judgment: ['证据', '水肿', '中性粒', '支持', '判断'],
    summary_reflection: ['总结', '反思', '不确定', '不足', '核对', '改进'],
  }
  const answer = input.trim()
  const enough =
    answer.length >= 24 &&
    (expectedTerms[caseValue.phase] || []).some((term) => answer.includes(term)) &&
    (caseValue.phase !== 'summary_reflection' ||
      (['血管', '渗出', '炎症', '病理'].some((term) => answer.includes(term)) &&
        ['改进', '查阅', '核对', '复习'].some((term) => answer.includes(term)) &&
        ['不确定', '不足', '遗漏', '混淆'].some((term) => answer.includes(term))))
  const phases = ROUTE_CASE_STAGES.map((stage) => stage.phase)
  const messagePhase = phases.find((phase) => phase === caseValue.phase)!
  let decision = 'stay'
  const missing = enough ? [] : ['请结合病例中的表现，补充关键病理变化与依据。']
  if (enough && caseValue.phase !== 'summary_reflection') decision = 'advance'
  if (enough && caseValue.phase === 'summary_reflection') decision = 'complete'
  const userRevision = caseValue.revision + 1
  const studentMessage: RouteCaseMessage = {
    id: uid(),
    role: 'student',
    content: answer,
    revision: userRevision,
    phase: messagePhase,
  }
  caseValue.messages.push(studentMessage)
  let reply = '可以继续结合病例事实，把病理变化、机制和判断证据联系起来。'
  if (enough) {
    if (decision === 'advance') {
      const nextStage = caseValue.stages[phases.indexOf(messagePhase) + 1]
      caseValue.phase = nextStage.phase
      caseValue.nextPrompt = nextStage.prompt
      caseValue.goals = clone(nextStage.goals)
      reply = `本阶段目标已达成，已解锁${ROUTE_CASE_STAGES[phases.indexOf(messagePhase) + 1].label}。你可以切换到下一阶段继续学习。`
    } else {
      caseValue.phase = 'completed'
      caseValue.status = 'completed'
      caseValue.goals = []
      caseValue.nextPrompt = ''
      reply = '你已完成病例分析与总结反思，可以返回计划继续。'
      const step = state.detail.steps.find((s) => s.id === caseValue.stepId)
      if (step) {
        step.status = 'completed'
        step.completedAt = now()
      }
      const nextStep = state.detail.steps.find((s) => s.position === (step?.position || 0) + 1)
      if (nextStep) nextStep.status = 'available'
      refreshTest(state)
    }
  }
  caseValue.revision += 1
  caseValue.messages.push({
    id: uid(),
    role: 'assistant',
    content: reply,
    revision: caseValue.revision,
    phase: messagePhase,
  })
  const result: RouteCaseMessageResult = {
    clientMessageId,
    requestRevision: userRevision,
    processingState: 'completed',
    retryAllowed: false,
    reply,
    phase: caseValue.phase,
    revision: caseValue.revision,
    decision,
    missingElements: missing,
    status: caseValue.status,
  }
  state.receipts[`case:${caseId}:${clientMessageId}`] = { fingerprint: fingerprint(input), value: clone(result) }
  refresh(state)
  persist()
  return clone(result)
}

function isTeacherOwner(state: State) {
  return state.summary.sourceKind === 'classroom' && Boolean(state.teacherTest)
}
function projectTeacherTest(state: State, test = state.teacherTest!): TeacherFinalTest {
  return {
    ...clone(test),
    currentScopeActive: isTeacherOwner(state) && state.summary.scopeStatus === 'active',
  }
}
function demoClassName(classId: number) {
  return classId === 1 ? '病理学演示班' : '病理学课堂'
}
function demoStudentName(state: State) {
  if (state.studentOpenid === 'demo_student_b') return '演示学生（二）'
  if (state.studentOpenid === '演示学生·周宁') return '演示学生（三）'
  return '演示学生'
}
function teacherTest(testId: string, active = false): State {
  requireTeacher()
  const state = all().find((x) => x.summary.testSummary.id === testId && isTeacherOwner(x))
  if (!state || !state.teacherTest) return fail('RESOURCE_NOT_FOUND', '课堂测试不存在')
  if (active && state.summary.scopeStatus !== 'active') return fail('STATE_CONFLICT', 'CLASSROOM_SCOPE_INACTIVE')
  return state
}

function validAnswer(questionType: FinalTestQuestionType, answer: FinalTestAnswer | undefined): boolean {
  if (questionType === 'single_choice') return Number.isInteger(answer) && Number(answer) >= 0 && Number(answer) <= 3
  if (questionType === 'multiple_choice')
    return (
      Array.isArray(answer) &&
      answer.length > 0 &&
      answer.length <= 4 &&
      answer.every((option) => Number.isInteger(option) && option >= 0 && option <= 3) &&
      new Set(answer).size === answer.length
    )
  return typeof answer === 'string' && answer.trim().length > 0 && answer.length <= 2000
}

function gradeDemoResult(state: State, answers: Record<string, FinalTestAnswer>): LearningResult {
  const teacherQuestions = state.gradingQuestions || state.teacherTest?.questions || []
  let objectiveCorrect = 0
  let score = 0
  const questions = state.test.questions.map((question, index) => {
    const key = teacherQuestions.find((item) => item.id === question.id) || teacherQuestions[index]
    const explanation = key?.explanation || '结合病例和资料中的病理变化与机制判断。'
    if (question.questionType === 'single_choice') {
      const correctOption = key?.questionType === 'single_choice' ? key.correctOption : 0
      const selectedOption = answers[question.id] as number
      const pointsPossible = state.test.formatVersion === 'mixed_v2' ? 15 : 100 / state.test.questions.length
      const pointsAwarded = selectedOption === correctOption ? pointsPossible : 0
      score += pointsAwarded
      if (pointsAwarded > 0) objectiveCorrect += 1
      return {
        ...question,
        selectedOption,
        correctOption,
        explanation,
        pointsAwarded,
        pointsPossible,
      }
    }
    if (question.questionType === 'multiple_choice') {
      const correctOptions = key?.questionType === 'multiple_choice' ? [...key.correctOptions] : [0, 2]
      const selectedOptions = [...(answers[question.id] as number[])].sort((a, b) => a - b)
      const canonicalCorrect = [...correctOptions].sort((a, b) => a - b)
      const pointsAwarded =
        selectedOptions.length === canonicalCorrect.length &&
        selectedOptions.every((option, i) => option === canonicalCorrect[i])
          ? 25
          : 0
      score += pointsAwarded
      if (pointsAwarded > 0) objectiveCorrect += 1
      return {
        ...question,
        selectedOptions,
        correctOptions,
        explanation,
        pointsAwarded,
        pointsPossible: state.test.formatVersion === 'mixed_v2' ? 25 : 100 / state.test.questions.length,
      }
    }
    const selectedText = answers[question.id] as string
    const rubric = key?.questionType === 'short_answer' ? key.rubric : demoRubric
    const matches: Record<string, RegExp> = {
      vascular_change: /小动脉|扩张|血流/,
      exudation: /通透性|渗出|水肿/,
      cellular_evidence: /中性粒|炎症细胞/,
    }
    const rubricResults: FinalTestRubricResult[] = rubric.map((criterion) => {
      const met = matches[criterion.criterionId]?.test(selectedText) ?? false
      return {
        criterionId: criterion.criterionId,
        earnedPoints: met ? criterion.maxPoints : 0,
        evidence: met ? `答复提到了“${criterion.description}”相关依据。` : `答复尚未说明“${criterion.description}”。`,
      }
    })
    const pointsAwarded = rubricResults.reduce((total, item) => total + item.earnedPoints, 0)
    score += pointsAwarded
    return {
      ...question,
      selectedText,
      referenceAnswer: key?.questionType === 'short_answer' ? key.referenceAnswer : '',
      rubricResults,
      gradingFeedback: rubricResults.map((item) => item.evidence).join(' '),
      explanation,
      pointsAwarded,
      pointsPossible: state.test.formatVersion === 'mixed_v2' ? 30 : 100 / state.test.questions.length,
    }
  })
  const submittedAt = now()
  return {
    id: uid(),
    routeId: state.summary.id,
    sourceKind: state.summary.sourceKind,
    goalPointCodes: state.summary.goalPointCodes,
    routeSummary: {
      title: state.summary.title,
      steps: state.detail.steps.map((step) => ({ title: step.title, kind: step.kind, completedAt: step.completedAt })),
    },
    correctCount: objectiveCorrect,
    questionCount: questions.length,
    score: Math.round(score * 10) / 10,
    submittedAt,
    questions,
    reviewKind: state.test.reviewKind,
    formatVersion: state.test.formatVersion,
  }
}

export async function ensureDemoLearningRouteForCompletion(input: {
  sessionId: string
  studentOpenid: string
  sourceKind: 'classroom' | 'autonomous'
  goalPointCodes: string[]
  diagnosisSummary?: Record<string, unknown>
}): Promise<{
  learningRouteId: string
  finalTestId: string
  routeGenerationState: string
  testGenerationState: string
}> {
  const routeGoals = [...new Set(input.goalPointCodes)]
  if (routeGoals.length !== 1 || input.goalPointCodes.length !== 1 || routeGoals.some((code) => !code.trim()))
    return fail('VALIDATION_ERROR', '学习路线需要 1 个有效知识点目标')
  const states = all()
  const existing = states.find(
    (x) => x.studentOpenid === input.studentOpenid && x.summary.sessionLocator === input.sessionId,
  )
  if (existing) {
    if (
      existing.summary.sourceKind !== input.sourceKind ||
      existing.summary.goalPointCodes.join('|') !== routeGoals.join('|')
    )
      return fail('STATE_CONFLICT', 'COMPLETION_INPUT_MISMATCH')
    return {
      learningRouteId: existing.summary.id,
      finalTestId: existing.test.id,
      routeGenerationState: existing.summary.generationState,
      testGenerationState: existing.detail.testSummary.generationState,
    }
  }
  const value = createState(
    uid(),
    '研讨后的学习计划',
    input.studentOpenid,
    input.sourceKind,
    'active',
    routeGoals,
    'active',
    'mixed_v2',
  )
  value.publishedAt ??= now()
  value.sourceSessionId = input.sessionId
  value.summary.sessionLocator = input.sessionId
  if (value.teacherTest) {
    value.teacherTest.classId = 1
    const sourceSession = /^demo-pbl-(\d+)$/.exec(input.sessionId)?.[1]
    const numericSession = /^\d+$/.test(input.sessionId) ? input.sessionId : sourceSession
    value.teacherTest.sessionId =
      numericSession && Number.isSafeInteger(Number(numericSession)) && Number(numericSession) > 0
        ? Number(numericSession)
        : 1
    value.teacherTest.studentId = input.studentOpenid === 'demo_student_b' ? 2 : 1
  }
  if (input.diagnosisSummary) value.detail.diagnosisSummary = clone(input.diagnosisSummary)
  value.detail.summary = clone(value.summary)
  states.unshift(value)
  persist()
  return {
    learningRouteId: value.summary.id,
    finalTestId: value.test.id,
    routeGenerationState: value.summary.generationState,
    testGenerationState: value.detail.testSummary.generationState,
  }
}

/** Idempotent, additive fixtures for the teacher PBL reference screen. */
export function ensureDemoPblReferenceRoutes(
  students: Array<{ name: string; index: number; studentId: number; openid: string; routeId: string }>,
) {
  const states = all()
  let added = false
  for (const student of students) {
    if (states.some((state) => state.summary.id === student.routeId)) continue
    const state = createState(
      student.routeId,
      '炎症：病理证据讨论',
      student.openid,
      'classroom',
      student.index === 7 ? 'complete' : 'active',
      [goals[0]],
    )
    state.sourceSessionId = 'demo-pbl-1'
    state.summary.sessionLocator = '炎症：病理证据讨论'
    state.teacherTest!.studentId = student.studentId
    state.teacherTest!.sessionId = 1
    const reading = Object.values(state.reading)[0]
    const caseView = Object.values(state.cases)[0]
    state.reading = {}
    state.cases = {}
    state.detail.steps = Array.from({ length: 7 }, (_, index) => {
      const stepId = `a5500000-0000-4000-8000-${String(student.studentId * 10 + index).padStart(12, '0')}`
      const completed = student.index === 7 || (student.index === 6 && index < 6)
      const step: LearningRouteStep = {
        id: stepId,
        position: index + 1,
        kind: index % 2 ? 'case' : 'reading',
        title: ['血管反应', '组织水肿', '渗出机制', '炎症细胞', '形态证据', '病例推理', '机制整合'][index],
        goalPointCodes: [goals[0]],
        status: completed ? 'completed' : index === 0 || student.index >= 6 ? 'available' : 'locked',
        completedAt: completed ? now() : undefined,
      }
      if (step.kind === 'reading')
        state.reading[stepId] = {
          ...clone(reading),
          step,
          readingProgress: { ...reading.readingProgress, accumulatedSeconds: completed ? 180 : 0 },
        }
      else {
        const caseId = `c5500000-0000-4000-8000-${String(student.studentId * 10 + index).padStart(12, '0')}`
        step.caseId = caseId
        state.cases[caseId] = { ...clone(caseView), id: caseId, stepId, status: completed ? 'completed' : 'available' }
      }
      return step
    })
    if (student.index < 6) {
      state.publishedAt = undefined
      state.summary.generationState = 'generating'
      state.summary.status = 'generating'
      state.summary.nextAction = 'wait_generation'
    }
    if (student.index === 7) {
      state.result = syntheticSeedResult(state, false)
      state.result.id = `e5500000-0000-4000-8000-${String(student.studentId).padStart(12, '0')}`
      state.summary.resultId = state.result.id
    }
    refresh(state)
    states.push(state)
    added = true
  }
  if (added) persist()
}

export async function readDemoTeacherClassroomRoutes(classId: number, sessionId?: number | string) {
  requireTeacher()
  return all().flatMap((state) => {
    const test = state.teacherTest
    const sessionMatches =
      sessionId == null ||
      (state.sourceSessionId != null
        ? String(state.sourceSessionId) === String(sessionId)
        : typeof sessionId === 'number'
          ? test?.sessionId === sessionId
          : state.summary.sessionLocator === String(sessionId))
    if (!test || test.classId !== classId || !sessionMatches) return []
    return [
      {
        routeId: state.summary.id,
        finalTestId: test.id,
        studentId: test.studentId,
        sessionId: test.sessionId,
        status: state.summary.status,
        resultId: state.result?.id,
        score: state.result?.score,
        correctCount: state.result?.correctCount,
        questionCount: state.result?.questionCount,
        questions:
          state.result?.formatVersion === 'single_choice_v1'
            ? state.result.questions
                .filter((question) => question.questionType === 'single_choice')
                .map((question) => ({
                  pointCode: question.pointCode,
                  selectedOption: question.selectedOption!,
                  correctOption: question.correctOption!,
                }))
            : undefined,
        completedAt: state.result?.submittedAt,
        updatedAt: state.summary.updatedAt,
        completedSteps:
          state.detail.steps.filter((step) => step.status === 'completed').length + (state.result ? 1 : 0),
        totalSteps: state.detail.steps.length + 1,
      },
    ]
  })
}

export type DemoTeacherInsightsQuestionFact = {
  questionType: FinalTestQuestionType
  pointCode: string
  selectedOption?: number
  correctOption?: number
  selectedOptions?: number[]
  correctOptions?: number[]
  pointsAwarded?: number
  pointsPossible?: number
}
export type DemoTeacherInsightsFact = {
  routeId: string
  title: string
  classId: number
  className: string
  sessionId: number | string
  studentId: number
  studentName: string
  publishedAt: string | null
  updatedAt: string
  stepProgress: { completedSteps: number; totalSteps: number }
  steps: Array<Pick<LearningRouteStep, 'id' | 'position' | 'kind' | 'status' | 'completedAt'>>
  accumulatedReadingSeconds: number
  test: {
    id: string
    generationState: string
    reviewState: string
    attemptStatus: string | null
    resultId: string | null
  }
  result?: {
    id: string
    formatVersion: 'single_choice_v1' | 'mixed_v2'
    score: number
    correctCount: number
    questionCount: number
    submittedAt: string
    questions: DemoTeacherInsightsQuestionFact[]
  }
}

/** Read-only, teacher-authorized Demo projection for aggregate classroom insights. */
export function readDemoTeacherInsightsFacts(): DemoTeacherInsightsFact[] {
  if (!requireTeacherReadScope()) return []
  return all()
    .filter(isTeacherOwner)
    .map((state) => {
      const test = state.teacherTest!
      const completedSteps = state.detail.steps.filter((step) => step.status === 'completed').length
      return {
        routeId: state.summary.id,
        title: state.summary.title,
        classId: test.classId,
        className: demoClassName(test.classId),
        sessionId: state.sourceSessionId ?? test.sessionId,
        studentId: test.studentId,
        studentName: demoStudentName(state),
        publishedAt: state.publishedAt ?? null,
        updatedAt: state.summary.updatedAt,
        stepProgress: { completedSteps, totalSteps: state.detail.steps.length },
        steps: state.detail.steps.map((step) => ({
          id: step.id,
          position: step.position,
          kind: step.kind,
          status: step.status,
          completedAt: step.completedAt,
        })),
        accumulatedReadingSeconds: Object.values(state.reading).reduce(
          (total, reading) => total + reading.readingProgress.accumulatedSeconds,
          0,
        ),
        test: {
          id: test.id,
          generationState: test.generationState === 'failed' ? 'generation_failed' : test.generationState,
          reviewState: test.reviewState,
          attemptStatus: state.test.attempt?.status ?? null,
          resultId: state.result?.id ?? null,
        },
        ...(state.result
          ? {
              result: {
                id: state.result.id,
                formatVersion: state.result.formatVersion,
                score: state.result.score,
                correctCount: state.result.correctCount,
                questionCount: state.result.questionCount,
                submittedAt: state.result.submittedAt,
                questions: state.result.questions.map((question) => ({
                  questionType: question.questionType,
                  pointCode: question.pointCode,
                  selectedOption: question.selectedOption,
                  correctOption: question.correctOption,
                  selectedOptions: question.selectedOptions ? [...question.selectedOptions] : undefined,
                  correctOptions: question.correctOptions ? [...question.correctOptions] : undefined,
                  pointsAwarded: question.pointsAwarded,
                  pointsPossible: question.pointsPossible,
                })),
              },
            }
          : {}),
      }
    })
}

export async function getDemoTeacherQuestionBankSource(sourceId: string) {
  requireTeacher()
  const state = all().find(
    (item) => item.teacherTest?.questions.some((question) => question.id === sourceId) && isTeacherOwner(item),
  )
  const question = state?.teacherTest?.questions.find((item) => item.id === sourceId)
  if (!state || !question) return fail('RESOURCE_NOT_FOUND', '课堂题目来源不存在')
  if (question.questionType !== 'single_choice') return fail('VALIDATION_ERROR', '当前题型不能作为单选题复制')
  return {
    sourceType: 'route_test_question' as const,
    sourceId,
    sourceDigest: question.sourceDigest || sourceDigest(question),
    taskType: 'retest' as const,
    pointCodes: [question.primaryPointCode],
    dimensionIds: [],
    title: '病理知识单选题',
    prompt: question.prompt,
    options: [...question.options],
    publicDefinition: { title: '病理知识单选题', prompt: question.prompt, options: [...question.options] },
    answer: { correct_option: question.correctOption },
    explanation: question.explanation,
    medicalReviewStatus: null,
  }
}

export const demoLearningRoutes: LearningRoutesPort = {
  async getLearningRoutes(status = 'active', limit = 20, offset = 0) {
    const user = requireStudent()
    const items = all()
      .filter((x) => x.studentOpenid === user.openid && (status === 'completed' ? Boolean(x.result) : !x.result))
      .map(projectSummary)
      .sort((a, b) => b.updatedAt.localeCompare(a.updatedAt) || b.id.localeCompare(a.id))
    return { items: clone(items.slice(offset, offset + Math.min(100, limit))), total: items.length, limit, offset }
  },
  async getLearningRoute(routeId) {
    const state = findRoute(routeId)
    return { ...clone(state.detail), summary: projectSummary(state) }
  },
  async retryLearningRouteGeneration(routeId, component, clientRequestId) {
    const state = findRoute(routeId)
    if (state.summary.sourceKind === 'classroom' && state.summary.scopeStatus !== 'active')
      return fail('STATE_CONFLICT', 'CLASSROOM_SCOPE_INACTIVE')
    const body = { component }
    const replay = repeat(state, `retry:${clientRequestId}`, body, generationReceiptSchema)
    if (replay) return replay
    if (component === 'route') {
      if (state.summary.generationState === 'published') return fail('STATE_CONFLICT', 'ALREADY_GENERATED')
      const reading = Object.values(state.reading)[0]
      const caseValue = Object.values(state.cases)[0]
      reading.step.status = 'available'
      state.detail.steps = [
        reading.step,
        {
          id: caseValue.stepId,
          position: 2,
          kind: 'case',
          title: '分析合成教学病例',
          goalPointCodes: state.summary.goalPointCodes,
          status: 'locked',
          caseId: caseValue.id,
        },
      ]
      state.summary.generationState = 'published'
      state.publishedAt ??= now()
      state.summary.status = 'learning'
      state.summary.nextAction = 'reading'
      state.detail.summary = clone(state.summary)
    } else {
      if (state.summary.generationState !== 'published') return fail('STATE_CONFLICT', 'ROUTE_NOT_PUBLISHED')
      if (state.test.questions.length && state.detail.testSummary.generationState === 'ready')
        return fail('STATE_CONFLICT', 'ALREADY_GENERATED')
      state.detail.testSummary.generationState = 'ready'
      state.detail.testSummary.retryAllowed = false
      state.detail.testSummary.questionCount = state.test.questions.length
      state.summary.testSummary = clone(state.detail.testSummary)
    }
    refreshTest(state)
    const receipt = {
      routeId,
      component,
      generationState: component === 'route' ? state.summary.generationState : state.detail.testSummary.generationState,
    }
    remember(state, `retry:${clientRequestId}`, body, receipt)
    refresh(state)
    persist()
    return clone(receipt)
  },
  async getLearningRouteStep(stepId) {
    const { state, step } = findStep(stepId)
    if (step.kind !== 'reading') return fail('STATE_CONFLICT', 'STEP_KIND_MISMATCH')
    return clone(state.reading[stepId])
  },
  async saveRouteReadingProgress(stepId, action, clientRequestId, leaseToken) {
    const { state, step } = findStep(stepId)
    if (step.kind !== 'reading') return fail('STATE_CONFLICT', 'STEP_KIND_MISMATCH')
    const reading = state.reading[stepId]
    const key = `reading:${clientRequestId}`
    const body = { stepId, action, leaseToken }
    const replay = repeat(state, key, body, readingReceiptSchema)
    if (replay) return replay
    const progress = reading.readingProgress
    const timestamp = Date.now()
    if (action === 'start') {
      progress.leaseToken = uid()
      progress.lastSeenAt = new Date(timestamp).toISOString()
      if (step.status === 'available') step.status = 'in_progress'
    } else {
      if (!leaseToken || leaseToken !== progress.leaseToken) return fail('STATE_CONFLICT', 'READING_LEASE_INVALID')
      if (progress.lastSeenAt) {
        const elapsed = timestamp - Date.parse(progress.lastSeenAt)
        if (elapsed >= 0 && elapsed <= 30_000) progress.accumulatedSeconds += Math.floor(elapsed / 1000)
      }
      progress.lastSeenAt = new Date(timestamp).toISOString()
      if (action === 'pause') progress.leaseToken = undefined
    }
    const saved = clone(progress)
    remember(state, key, body, saved)
    persist()
    return saved
  },
  async completeRouteReading(stepId, clientRequestId) {
    const { state, step } = findStep(stepId)
    if (step.kind !== 'reading') return fail('STATE_CONFLICT', 'STEP_KIND_MISMATCH')
    const body = { stepId }
    const key = `complete-reading:${clientRequestId}`
    const replay = repeat(state, key, body, detailSchema)
    if (replay) return replay
    step.status = 'completed'
    step.completedAt = step.completedAt || now()
    const next = state.detail.steps.find((x) => x.position === step.position + 1)
    if (next) next.status = 'available'
    refreshTest(state)
    remember(state, key, body, state.detail)
    persist()
    return clone(state.detail)
  },
  async getRouteCase(caseId) {
    return clone(findCase(caseId).value)
  },
  async sendRouteCaseMessage(caseId, content, clientMessageId, expectedRevision) {
    const { state, value } = findCase(caseId)
    if (state.receipts[`case:${caseId}:${clientMessageId}`])
      return ensureCaseResult(state, caseId, content, clientMessageId)
    if (value.phase === 'completed') return fail('STATE_CONFLICT', 'CASE_COMPLETED')
    if (value.revision !== expectedRevision) return fail('STATE_CONFLICT', 'VERSION_CONFLICT')
    return ensureCaseResult(state, caseId, content, clientMessageId)
  },
  async startFinalTest(testId, clientRequestId) {
    const state = findRoute(all().find((x) => x.test.id === testId)?.summary.id || '')
    refreshTest(state)
    if (!state.detail.canStartTest) return fail('STATE_CONFLICT', state.detail.lockReasons[0] || 'TEST_NOT_RELEASED')
    if (state.result) return fail('STATE_CONFLICT', 'ALREADY_SUBMITTED')
    const body = { testId }
    const key = `test-start:${clientRequestId}`
    const replay = repeat(state, key, body, studentTestSchema)
    if (replay) return replay
    if (!state.test.attempt) state.test.attempt = { id: uid(), status: 'in_progress', version: 1, answers: {} }
    refreshTest(state)
    remember(state, key, body, state.test)
    persist()
    return clone(state.test)
  },
  async getFinalTest(routeId) {
    const state = findRoute(routeId)
    refreshTest(state)
    if (!state.detail.canStartTest && !state.test.attempt)
      return fail('STATE_CONFLICT', state.detail.lockReasons[0] || 'TEST_NOT_RELEASED')
    return clone(state.test)
  },
  async saveFinalTestDraft(testId, clientRequestId, expectedVersion, releasedDigest, answers) {
    const state = findRoute(all().find((x) => x.test.id === testId)?.summary.id || '')
    const attempt = state.test.attempt
    const body = { testId, expectedVersion, releasedDigest, answers }
    const key = `draft:${clientRequestId}`
    const replay = repeat(state, key, body, attemptSchema)
    if (replay) return replay
    if (state.result) return fail('STATE_CONFLICT', 'ALREADY_SUBMITTED')
    if (
      !attempt ||
      attempt.status !== 'in_progress' ||
      attempt.version !== expectedVersion ||
      state.test.releasedDigest !== releasedDigest
    )
      return fail('STATE_CONFLICT', 'VERSION_CONFLICT')
    if (
      Object.entries(answers).some(([id, answer]) => {
        const question = state.test.questions.find((item) => item.id === id)
        return !question || !validAnswer(question.questionType, answer)
      })
    )
      return fail('VALIDATION_ERROR', '答卷包含无效题目或选项')
    attempt.answers = clone(answers)
    attempt.version += 1
    attempt.savedAt = now()
    remember(state, key, body, attempt)
    persist()
    return clone(attempt)
  },
  async submitFinalTest(testId, clientSubmissionId, expectedVersion, releasedDigest, answers) {
    const state = findRoute(all().find((x) => x.test.id === testId)?.summary.id || '')
    const body = { testId, expectedVersion, releasedDigest, answers }
    const payload = fingerprint(body)
    const submitted = state.submissions[clientSubmissionId]
    if (submitted) {
      if (submitted.fingerprint !== payload) return fail('STATE_CONFLICT', 'IDEMPOTENCY_MISMATCH')
      return clone(state.result!)
    }
    const attempt = state.test.attempt
    if (
      !attempt ||
      attempt.status !== 'in_progress' ||
      attempt.version !== expectedVersion ||
      state.test.releasedDigest !== releasedDigest
    )
      return fail('STATE_CONFLICT', 'VERSION_CONFLICT')
    if (
      Object.keys(answers).length !== state.test.questions.length ||
      state.test.questions.some((question) => !validAnswer(question.questionType, answers[question.id]))
    )
      return fail('VALIDATION_ERROR', '请完成全部题目')
    const result = gradeDemoResult(state, answers)
    state.result = result
    state.summary.updatedAt = result.submittedAt
    state.summary.resultId = result.id
    state.summary.status = 'completed'
    state.summary.nextAction = 'view_result'
    state.test.attempt = {
      ...attempt,
      status: 'submitted',
      version: attempt.version + 1,
      answers: clone(answers),
      submittedAt: result.submittedAt,
    }
    state.submissions[clientSubmissionId] = { fingerprint: payload, resultId: result.id }
    refreshTest(state)
    state.summary.resultId = result.id
    state.summary.status = 'completed'
    state.summary.nextAction = 'view_result'
    persist()
    return clone(result)
  },
  async getFinalTestGrading(testId) {
    const state = findRoute(all().find((item) => item.test.id === testId)?.summary.id || '')
    if (!state.test.attempt || state.test.attempt.status === 'in_progress')
      return fail('STATE_CONFLICT', 'SUBMISSION_REQUIRED')
    const status: FinalTestGradingStatus = {
      status: state.result ? 'completed' : 'grading',
      testId,
      routeId: state.summary.id,
      resultId: state.result?.id,
      retryAllowed: false,
    }
    return clone(status)
  },
  async retryFinalTestGrading(testId, clientRequestId) {
    const state = findRoute(all().find((item) => item.test.id === testId)?.summary.id || '')
    const body = { testId }
    const key = `grading-retry:${clientRequestId}`
    const replay = repeat(state, key, body, gradingStatusSchema)
    if (replay) return replay
    if (!state.test.attempt || state.test.attempt.status === 'in_progress')
      return fail('STATE_CONFLICT', 'SUBMISSION_REQUIRED')
    const status: FinalTestGradingStatus = {
      status: state.result ? 'completed' : 'grading',
      testId,
      routeId: state.summary.id,
      resultId: state.result?.id,
      retryAllowed: false,
    }
    remember(state, key, body, status)
    persist()
    return clone(status)
  },
  async getLearningRouteResult(routeId) {
    const state = findRoute(routeId)
    if (!state.result) return fail('RESOURCE_NOT_FOUND', '学习结果尚不可用')
    return clone(state.result)
  },
  async getLearningResultTutor(resultId) {
    const user = requireStudent()
    const state = all().find((item) => item.studentOpenid === user.openid && item.result?.id === resultId)
    if (!state?.result) return fail('RESOURCE_NOT_FOUND', '学习结果不存在')
    state.tutor ||= { resultId, revision: 0, processingState: 'idle', messages: [] }
    persist()
    return clone(state.tutor)
  },
  async sendLearningResultTutorMessage(resultId, clientMessageId, questionId, expectedRevision, content) {
    const user = requireStudent()
    const state = all().find((item) => item.studentOpenid === user.openid && item.result?.id === resultId)
    if (!state?.result) return fail('RESOURCE_NOT_FOUND', '学习结果不存在')
    const body = { questionId, expectedRevision, content }
    const fingerprintValue = fingerprint(body)
    const previous = state.tutorReceipts?.[clientMessageId]
    if (previous) {
      if (previous.fingerprint !== fingerprintValue) return fail('STATE_CONFLICT', 'IDEMPOTENCY_MISMATCH')
      return clone(previous.thread)
    }
    if (!content.trim() || content.length > 2000) return fail('VALIDATION_ERROR', '请输入有效的学习问题')
    const question = state.result.questions.find((item) => item.id === questionId)
    if (!question) return fail('VALIDATION_ERROR', '题目不属于本次结果')
    const thread = (state.tutor ||= { resultId, revision: 0, processingState: 'idle', messages: [] })
    if (thread.revision !== expectedRevision) return fail('STATE_CONFLICT', 'VERSION_CONFLICT')
    const studentMessage = {
      id: uid(),
      role: 'student' as const,
      questionId,
      content,
      sequence: thread.messages.length + 1,
      createdAt: now(),
    }
    const priorQuestions = thread.messages
      .filter((message) => message.role === 'student')
      .map((message) => state.result!.questions.find((item) => item.id === message.questionId)?.position)
      .filter((position): position is number => position !== undefined)
    const mentionsHistory = /比较|对比|联系|前面|之前|其他题|另一题/.test(content)
    const memory = priorQuestions.length ? `此前你在第 ${priorQuestions.join('、')} 题也提出过问题。` : ''
    const assistantContent = mentionsHistory
      ? `${memory}第 ${question.position} 题的关键依据是：${question.explanation}`
      : `第 ${question.position} 题：${question.explanation}${question.gradingFeedback ? ` ${question.gradingFeedback}` : ''}`
    const assistantMessage = {
      id: uid(),
      role: 'assistant' as const,
      questionId,
      content: assistantContent,
      sequence: studentMessage.sequence + 1,
      createdAt: now(),
    }
    thread.messages.push(studentMessage, assistantMessage)
    thread.revision += 2
    const saved = clone(thread)
    state.tutorReceipts ||= {}
    state.tutorReceipts[clientMessageId] = { fingerprint: fingerprintValue, thread: saved }
    persist()
    return saved
  },
  async getTeacherFinalTestReviewQueue(
    filters: TeacherFinalTestReviewQueueFilters = {},
  ): Promise<TeacherFinalTestReviewQueuePage> {
    const ownsDemoClass = requireTeacherReadScope()
    const asOf = now()
    const asOfTime = Date.parse(asOf)
    const limit = Math.max(1, Math.min(100, Math.trunc(filters.limit ?? 20)))
    const offset = Math.max(0, Math.trunc(filters.offset ?? 0))
    const counts: TeacherFinalTestReviewQueuePage['counts'] = {
      pendingReview: 0,
      needsChanges: 0,
      generationFailed: 0,
    }
    if (!ownsDemoClass) {
      if (filters.classId != null) return fail('RESOURCE_NOT_FOUND', '班级不存在')
      return { items: [], counts, total: 0, limit, offset, asOf }
    }
    if (filters.classId != null && filters.classId !== 1) return fail('RESOURCE_NOT_FOUND', '班级不存在')
    const candidates = all().flatMap((state): TeacherFinalTestReviewQueueItem[] => {
      const test = state.teacherTest
      if (
        !test ||
        !isTeacherOwner(state) ||
        state.summary.scopeStatus !== 'active' ||
        state.summary.generationState !== 'published' ||
        state.summary.status === 'testing' ||
        state.summary.status === 'completed' ||
        state.summary.resultId ||
        state.result ||
        state.test.attempt != null ||
        (filters.classId != null && test.classId !== filters.classId) ||
        (filters.sessionId != null && String(state.sourceSessionId ?? test.sessionId) !== String(filters.sessionId))
      )
        return []

      const reviewState = test.reviewState
      if (reviewState !== 'pending_review' && reviewState !== 'needs_changes') return []
      const failed =
        test.generationState === 'failed' ||
        test.generationState === 'generation_failed' ||
        state.detail.testSummary.generationState === 'failed' ||
        state.detail.testSummary.generationState === 'generation_failed'
      const ready = test.generationState === 'ready' && state.detail.testSummary.generationState === 'ready'
      const claimExpiresAt = state.detail.testSummary.claimExpiresAt || state.summary.testSummary.claimExpiresAt
      const claimExpiry = claimExpiresAt ? Date.parse(claimExpiresAt) : Number.NaN
      const retryClaimAvailable = !claimExpiresAt || !Number.isFinite(claimExpiry) || claimExpiry <= asOfTime
      const canReview = ready
      const canRetry = failed && retryClaimAvailable
      if (!canReview && !canRetry) return []

      const kind: TeacherFinalTestReviewQueueKind = canRetry ? 'generation_failed' : reviewState
      const countKey =
        kind === 'pending_review' ? 'pendingReview' : kind === 'needs_changes' ? 'needsChanges' : 'generationFailed'
      counts[countKey] += 1
      return [
        {
          id: test.id,
          routeId: state.summary.id,
          title: test.title,
          classId: test.classId,
          className: demoClassName(test.classId),
          sessionId: state.sourceSessionId ?? test.sessionId,
          studentId: test.studentId,
          studentName: demoStudentName(state),
          generationState: canRetry ? 'generation_failed' : 'ready',
          reviewState,
          updatedAt: state.summary.updatedAt,
          canReview,
          canRetry,
          actionReason: canRetry ? 'GENERATION_FAILED' : 'REVIEW_READY',
        },
      ]
    })
    candidates.sort((left, right) => right.updatedAt.localeCompare(left.updatedAt) || right.id.localeCompare(left.id))
    const filtered = filters.kind
      ? candidates.filter((item) =>
          filters.kind === 'generation_failed' ? item.canRetry : item.canReview && item.reviewState === filters.kind,
        )
      : candidates
    return {
      items: clone(filtered.slice(offset, offset + limit)),
      counts,
      total: filtered.length,
      limit,
      offset,
      asOf,
    }
  },
  async getTeacherFinalTest(testId) {
    const state = teacherTest(testId)
    return projectTeacherTest(state)
  },
  async saveTeacherFinalTest(testId, clientRequestId, expectedVersion, questions, feedbackDraft) {
    const state = teacherTest(testId, true)
    const value = state.teacherTest!
    const body = { expectedVersion, questions, feedbackDraft }
    const key = `teacher-save:${clientRequestId}`
    const replay = repeat(state, key, body, teacherTestSchema)
    if (replay) return projectTeacherTest(state, replay)
    if (value.reviewState === 'released') return fail('STATE_CONFLICT', 'TEST_ALREADY_RELEASED')
    if (value.generationState !== 'ready') return fail('STATE_CONFLICT', 'TEST_NOT_GENERATED')
    if (value.version !== expectedVersion) return fail('STATE_CONFLICT', 'VERSION_CONFLICT')
    const seen = new Set<string>()
    const existing = new Set(value.questions.map((question) => question.id))
    const cover = new Set<string>()
    const prompts = new Set<string>()
    const mixedTypes: FinalTestQuestionType[] = [
      'single_choice',
      'single_choice',
      'single_choice',
      'multiple_choice',
      'short_answer',
    ]
    const invalidQuestion = (question: EditableTeacherFinalTestQuestion, index: number) => {
      if (
        question.position !== index + 1 ||
        !question.prompt.trim() ||
        question.prompt.length > 2000 ||
        !question.explanation.trim() ||
        question.explanation.length > 2000 ||
        !value.goalPointCodes.includes(question.primaryPointCode)
      )
        return true
      if (question.questionType !== 'short_answer') {
        if (
          question.options.length !== 4 ||
          new Set(question.options.map((option) => option.trim().toLocaleLowerCase())).size !== 4 ||
          question.options.some((option) => !option.trim() || option.length > 500)
        )
          return true
      }
      if (question.questionType === 'single_choice')
        return !Number.isInteger(question.correctOption) || question.correctOption < 0 || question.correctOption > 3
      if (question.questionType === 'multiple_choice')
        return (
          question.correctOptions.length < 1 ||
          question.correctOptions.length > 4 ||
          question.correctOptions.some((option) => !Number.isInteger(option) || option < 0 || option > 3) ||
          new Set(question.correctOptions).size !== question.correctOptions.length
        )
      return (
        !question.referenceAnswer.trim() ||
        question.referenceAnswer.length > 2000 ||
        question.rubric.length !== 3 ||
        question.rubric.some(
          (criterion) => !criterion.criterionId.trim() || !criterion.description.trim() || criterion.maxPoints !== 10,
        ) ||
        new Set(question.rubric.map((criterion) => criterion.criterionId)).size !== question.rubric.length
      )
    }
    if (
      questions.length < 1 ||
      questions.length > 12 ||
      (value.formatVersion === 'mixed_v2' &&
        (questions.length !== mixedTypes.length ||
          questions.some((question, index) => question.questionType !== mixedTypes[index]))) ||
      questions.some(invalidQuestion)
    )
      return fail('VALIDATION_ERROR', '题目、选项、答案或目标覆盖不完整')
    for (const q of questions) {
      if (q.id && (seen.has(q.id) || !existing.has(q.id))) return fail('VALIDATION_ERROR', '题目身份无效')
      if (prompts.has(q.prompt.trim().toLocaleLowerCase())) return fail('VALIDATION_ERROR', '题目重复')
      if (q.id) seen.add(q.id)
      prompts.add(q.prompt.trim().toLocaleLowerCase())
      cover.add(q.primaryPointCode)
    }
    if (value.goalPointCodes.some((goal) => !cover.has(goal)))
      return fail('VALIDATION_ERROR', '每个主要目标至少需要一道题')
    const normalized = questions.map((q, index) => ({ ...q, id: q.id || uid(), position: index + 1 }))
    value.questions = clone(normalized.map((question) => ({ ...question, sourceDigest: sourceDigest(question) })))
    state.gradingQuestions = clone(value.questions)
    value.feedbackDraft = feedbackDraft
    value.version += 1
    value.draftDigest = digest(normalized)
    value.reviewState = 'pending_review'
    value.reviewKind = null
    state.detail.testSummary.reviewState = 'pending_review'
    state.detail.testSummary.reviewKind = null
    const saved = projectTeacherTest(state, value)
    remember(state, key, body, saved)
    refreshTest(state)
    persist()
    return clone(saved)
  },
  async requestTeacherTestChanges(testId, clientRequestId, expectedVersion, note) {
    const state = teacherTest(testId, true)
    const value = state.teacherTest!
    const body = { expectedVersion, note }
    const key = `teacher-changes:${clientRequestId}`
    const replay = repeat(state, key, body, teacherTestSchema)
    if (replay) return projectTeacherTest(state, replay)
    if (value.generationState !== 'ready') return fail('STATE_CONFLICT', 'TEST_NOT_GENERATED')
    if (value.version !== expectedVersion) return fail('STATE_CONFLICT', 'VERSION_CONFLICT')
    if (value.reviewState === 'released') return fail('STATE_CONFLICT', 'TEST_ALREADY_RELEASED')
    value.reviewState = 'needs_changes'
    value.feedbackDraft = note || ''
    value.version += 1
    state.detail.testSummary.reviewState = 'needs_changes'
    const saved = projectTeacherTest(state, value)
    remember(state, key, body, saved)
    refreshTest(state)
    persist()
    return clone(saved)
  },
  async retryTeacherTestGeneration(testId, clientRequestId) {
    const state = teacherTest(testId, true)
    const value = state.teacherTest!
    const body = { testId }
    const key = `teacher-retry:${clientRequestId}`
    const replay = repeat(state, key, body, generationReceiptSchema)
    if (replay) return replay
    if (value.generationState === 'ready') return fail('STATE_CONFLICT', 'ALREADY_GENERATED')
    value.generationState = 'ready'
    const generated =
      value.formatVersion === 'mixed_v2'
        ? mixedQuestionSet(state.summary.id, value.goalPointCodes)
        : questionSet(state.summary.id, value.goalPointCodes)
    value.questions = generated.map((question) => {
      const teacherQuestion = teacherQuestionFor(question, uid())
      return { ...teacherQuestion, sourceDigest: sourceDigest(teacherQuestion) } as TeacherFinalTestQuestion
    })
    state.gradingQuestions = clone(value.questions)
    value.version += 1
    value.draftDigest = digest(value.questions)
    refreshTest(state)
    const receipt = { routeId: state.summary.id, component: 'test' as const, generationState: 'ready' }
    remember(state, key, body, receipt)
    persist()
    return clone(receipt)
  },
  async releaseTeacherFinalTest(testId, clientRequestId, expectedVersion, draftDigest, feedback) {
    const state = teacherTest(testId, true)
    const value = state.teacherTest!
    const body = { expectedVersion, draftDigest, feedback }
    const key = `teacher-release:${clientRequestId}`
    const replay = repeat(state, key, body, releaseReceiptSchema)
    if (replay) return replay
    if (value.reviewState === 'released') return fail('STATE_CONFLICT', 'ALREADY_RELEASED')
    if (value.generationState !== 'ready') return fail('STATE_CONFLICT', 'TEST_NOT_GENERATED')
    if (value.version !== expectedVersion || value.draftDigest !== draftDigest)
      return fail('STATE_CONFLICT', 'VERSION_CONFLICT')
    if (
      value.questions.length < 1 ||
      value.goalPointCodes.some((goal) => !value.questions.some((q) => q.primaryPointCode === goal))
    )
      return fail('VALIDATION_ERROR', '最终测试未覆盖全部主要目标')
    value.reviewState = 'released'
    value.reviewKind = 'teacher'
    const releasedAt = now()
    value.releasedAt = releasedAt
    value.feedbackDraft = feedback || value.feedbackDraft
    state.test.reviewKind = 'teacher'
    state.test.formatVersion = value.formatVersion
    state.test.releasedVersion = value.version
    state.test.releasedDigest = value.draftDigest
    state.test.questions = value.questions.map((q) => ({
      id: q.id || uid(),
      position: q.position,
      pointCode: q.primaryPointCode,
      prompt: q.prompt,
      questionType: q.questionType,
      options: q.questionType === 'short_answer' ? [] : q.options,
    }))
    state.gradingQuestions = clone(value.questions)
    refreshTest(state)
    const receipt = { testId, releasedVersion: value.version, releasedDigest: value.draftDigest, releasedAt }
    remember(state, key, body, receipt)
    persist()
    return clone(receipt)
  },
  async getTeacherRouteResult(resultId) {
    requireTeacher()
    const value = all().find((x) => x.result?.id === resultId && x.summary.sourceKind === 'classroom')
    if (!value?.result || !value.teacherTest) return fail('RESOURCE_NOT_FOUND', '课堂学习结果不存在')
    return {
      ...clone(value.result),
      studentId: value.teacherTest.studentId,
      classId: value.teacherTest.classId,
      sessionId: value.teacherTest.sessionId,
    }
  },
}

// Bridge used by Demo PBL completion: creating a route is idempotent by student and session.
export function ensureDemoRouteCompletion(input: {
  sessionId: string
  studentOpenid: string
  sourceKind: 'classroom' | 'autonomous'
  goalPointCodes: string[]
  diagnosisSummary?: Record<string, unknown>
}) {
  return ensureDemoLearningRouteForCompletion(input)
}

export type DemoStudentLearningInsightsRoute = {
  id: string
  sessionLocator: string
  title: string
  goalPointCodes: string[]
  status: string
  progressLabel: string
  completedSteps: number
  totalSteps: number
  updatedAt: string
  accumulatedReadingSeconds: number
  result?: {
    score: number
    submittedAt: string
    goalPointCodes: string[]
    questions: Array<{
      pointCode: string
      earned: number
      possible: number
    }>
  }
}

/** Minimal current-user projection for the Demo learning insights bridge. */
export function readDemoStudentLearningInsightsRoutes(): DemoStudentLearningInsightsRoute[] {
  const current = actor()
  if (current.role !== 'student') fail('ROLE_REQUIRED', '学生身份不可用')
  const openid = current.openid
  const phaseLabels: Record<string, string> = {
    pathology_recognition: '病理识别',
    mechanism_explanation: '机制解释',
    evidence_judgment: '证据判断',
    summary_reflection: '总结反思',
  }
  const progressLabelFor = (state: State) => {
    if (state.result) return '最终测试已完成'
    if (state.test.attempt && state.test.attempt.status !== 'in_progress') return '正在评分'
    if (state.summary.status === 'learning') {
      const currentStep = state.detail.steps.find((step) => step.status !== 'completed')
      if (currentStep?.kind === 'reading') return '正在阅读'
      if (currentStep?.kind === 'case') {
        const phase = currentStep.caseId ? state.cases[currentStep.caseId]?.phase : undefined
        return phaseLabels[phase || ''] ? `病例学习·${phaseLabels[phase || '']}` : '病例学习中'
      }
      return '学习路线进行中'
    }
    if (state.summary.status === 'generation_failed') return '路线生成失败'
    if (state.summary.status === 'generating') return '路线生成中'
    if (state.summary.status === 'waiting_test_generation')
      return state.detail.testSummary.generationState === 'failed' ? '测试生成失败' : '等待测试生成'
    if (state.summary.status === 'waiting_teacher') return '等待教师审核'
    if (state.summary.status === 'testing') return '最终测试进行中'
    if (state.summary.status === 'ready_for_test') return '等待开始测试'
    return '学习路线进行中'
  }
  return all()
    .filter((state) => state.studentOpenid === openid)
    .map((state) => {
      const activityDates = [
        state.summary.updatedAt,
        ...Object.values(state.reading).map((reading) => reading.readingProgress.lastSeenAt),
        ...state.detail.steps.map((step) => step.completedAt),
        state.result?.submittedAt,
      ].filter((value): value is string => typeof value === 'string' && Number.isFinite(Date.parse(value)))
      const updatedAt = activityDates.reduce(
        (latest, value) => (Date.parse(value) > Date.parse(latest) ? value : latest),
        activityDates[0] || state.summary.updatedAt,
      )
      return {
        id: state.summary.id,
        sessionLocator: state.summary.sessionLocator,
        title: state.summary.title,
        goalPointCodes: [...state.summary.goalPointCodes],
        status: state.summary.status,
        progressLabel: progressLabelFor(state),
        completedSteps: state.detail.steps.filter((step) => step.status === 'completed').length,
        totalSteps: state.detail.steps.length,
        updatedAt,
        accumulatedReadingSeconds: Object.values(state.reading).reduce(
          (total, reading) => total + reading.readingProgress.accumulatedSeconds,
          0,
        ),
        result: state.result
          ? {
              score: state.result.score,
              submittedAt: state.result.submittedAt,
              goalPointCodes: [...state.result.goalPointCodes],
              questions: state.result.questions.flatMap((question) => {
                if (question.pointsAwarded != null && question.pointsPossible != null && question.pointsPossible > 0)
                  return [
                    {
                      pointCode: question.pointCode,
                      earned: question.pointsAwarded,
                      possible: question.pointsPossible,
                    },
                  ]
                if (
                  question.questionType === 'single_choice' &&
                  question.selectedOption != null &&
                  question.correctOption != null
                )
                  return [
                    {
                      pointCode: question.pointCode,
                      earned: question.selectedOption === question.correctOption ? 1 : 0,
                      possible: 1,
                    },
                  ]
                if (
                  question.questionType === 'multiple_choice' &&
                  question.selectedOptions &&
                  question.correctOptions
                ) {
                  const selected = [...question.selectedOptions].sort((a, b) => a - b)
                  const correct = [...question.correctOptions].sort((a, b) => a - b)
                  const isCorrect =
                    selected.length === correct.length && selected.every((value, index) => value === correct[index])
                  return [{ pointCode: question.pointCode, earned: isCorrect ? 1 : 0, possible: 1 }]
                }
                return []
              }),
            }
          : undefined,
      }
    })
}
