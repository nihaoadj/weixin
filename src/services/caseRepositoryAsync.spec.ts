import { afterEach, describe, expect, it, vi } from 'vitest'
import { saveSession } from './repository'
import {
  cloneCaseVersionAsync,
  completeCaseAttemptAsync,
  generateCaseDraftAsync,
  getDemoCaseProblemsAsync,
  getCaseAssessmentAsync,
  getCaseAttemptAsync,
  getCaseAuthoringAsync,
  getCaseAttemptsAsync,
  getGuidedCasesAsync,
  getMedicalReviewViewAsync,
  publishGuidedCaseAsync,
  saveGuidedCaseAsync,
  sendPatientMessageAsync,
  startCaseAttemptAsync,
  submitCaseStageAsync,
  submitGuidedCaseForReviewAsync,
  getMedicalReviewQueueAsync,
  decideGuidedCaseReviewAsync,
} from './caseRepositoryAsync'

describe('Demo case adapter', () => {
  afterEach(() => vi.unstubAllEnvs())
  it('keeps authoring, attempt and assessment flows available offline', async () => {
    saveSession({
      openid: 'async-demo',
      role: 'teacher',
      nickName: '教师',
      avatarUrl: '',
      createdAt: new Date(0).toISOString(),
    })
    const draft = await generateCaseDraftAsync({
      topic: '社区获得性肺炎',
      learnerLevel: '本科',
      learningObjectives: ['推理'],
    })
    const saved = await saveGuidedCaseAsync(draft)
    expect(await getCaseAuthoringAsync(saved.id)).toBeTruthy()
    expect((await getGuidedCasesAsync()).some((item) => item.id === saved.id)).toBe(true)

    await expect(publishGuidedCaseAsync(saved.id)).rejects.toThrow('先通过医学审核')
    expect((await submitGuidedCaseForReviewAsync(saved.id))?.medicalReviewStatus).toBe('pending')
    saveSession({
      openid: 'demo_reviewer',
      role: 'teacher',
      nickName: '审核专家',
      avatarUrl: '',
      permissions: ['medical_review'],
      createdAt: new Date(0).toISOString(),
    })
    expect((await getMedicalReviewQueueAsync()).some((item) => item.id === saved.id)).toBe(true)
    await decideGuidedCaseReviewAsync(saved.id, 'approved', '')
    saveSession({
      openid: 'async-demo',
      role: 'teacher',
      nickName: '教师',
      avatarUrl: '',
      createdAt: new Date(0).toISOString(),
    })
    expect(await publishGuidedCaseAsync(saved.id)).toMatchObject({ id: saved.id, status: '已发布' })
    const clone = await cloneCaseVersionAsync(saved.id)
    expect(clone.id).not.toBe(saved.id)

    saveSession({
      openid: 'async-student',
      role: 'student',
      nickName: '学生',
      avatarUrl: '',
      createdAt: new Date(0).toISOString(),
    })
    const attempt = await startCaseAttemptAsync('cap-undergraduate-showcase')
    expect(await getCaseAttemptAsync(attempt.id)).toBeTruthy()
    await sendPatientMessageAsync(attempt.id, '发热多久')
    await submitCaseStageAsync(attempt.id, { stageId: 'history', summary: '发热', keyFindings: ['发热'] })
    await submitCaseStageAsync(attempt.id, { stageId: 'problem_representation', summary: '发热咳嗽' })
    await submitCaseStageAsync(attempt.id, {
      stageId: 'differential',
      items: [
        { diagnosis: '肺炎', supportingEvidence: ['发热'], opposingEvidence: [] },
        { diagnosis: '病毒感染', supportingEvidence: [], opposingEvidence: [] },
      ],
    })
    await submitCaseStageAsync(attempt.id, {
      stageId: 'tests',
      items: [{ testName: '影像', rationale: '评估', priority: 'necessary' }],
    })
    await submitCaseStageAsync(attempt.id, {
      stageId: 'management',
      items: [{ action: '评估氧合', rationale: '安全' }],
      safetyConsiderations: ['过敏'],
    })
    const report = await completeCaseAttemptAsync(attempt.id)
    expect(report.totalScore).toBeGreaterThanOrEqual(0)
    expect(await getCaseAssessmentAsync(attempt.id)).toMatchObject({ attemptId: attempt.id })
    expect((await getCaseAttemptsAsync()).some((item) => item.id === attempt.id)).toBe(true)
  })

  it('keeps each Demo case facts, version and rubric isolated', async () => {
    saveSession({
      openid: 'demo-student-isolation',
      role: 'student',
      nickName: '学生',
      avatarUrl: '',
      createdAt: new Date(0).toISOString(),
    })
    const attempt = await startCaseAttemptAsync('acute-chest-pain-undergraduate-showcase')
    expect(attempt.problemVersion).toBe(1)
    expect(attempt.opening.chiefComplaint).toContain('胸痛')
    const response = await sendPatientMessageAsync(attempt.id, '请问心电图结果')
    expect(response.content).toContain('缺血性')
    expect(response.content).not.toContain('黄色黏痰')
  })

  it('maps all API adapter calls without loading Demo facts', async () => {
    vi.stubEnv('VITE_APP_MODE', 'api')
    vi.stubEnv('VITE_API_BASE_URL', 'https://api.example.com')
    vi.mocked(uni.request).mockImplementation((options) => {
      const path = String(options.url)
      const response = path.endsWith('/problems')
        ? [{ id: 7, type: '病例分析', title: '病例', target: 'all', status: 'published', content_type: 'guided_case' }]
        : path.includes('/review-queue')
          ? []
          : path.includes('/medical-review-view')
            ? {
                id: 7,
                title: '病例',
                status: 'draft',
                content_type: 'guided_case',
                case_definition: {},
                rubric: {},
                reviews: [],
              }
            : { id: 7, problem_id: 7, status: 'completed', current_stage: 'history', dimensions: [], total_score: 0 }
      options.success?.({ statusCode: 200, data: response, header: {}, cookies: [], errMsg: 'request:ok' })
      return undefined as never
    })
    const draft = await generateCaseDraftAsync({ topic: '主题', learnerLevel: '本科', learningObjectives: ['目标'] })
    await getCaseAttemptsAsync()
    await getDemoCaseProblemsAsync()
    await getGuidedCasesAsync()
    await getCaseAuthoringAsync('7')
    await cloneCaseVersionAsync('7')
    await publishGuidedCaseAsync('7')
    await submitGuidedCaseForReviewAsync('7')
    await getMedicalReviewQueueAsync()
    await getMedicalReviewViewAsync('7')
    await decideGuidedCaseReviewAsync('7', 'approved', '')
    await getCaseAttemptAsync('7')
    await startCaseAttemptAsync('7', '6')
    await sendPatientMessageAsync('7', '发热')
    await submitCaseStageAsync('7', { stageId: 'problem_representation', summary: '发热' })
    await completeCaseAttemptAsync('7')
    await getCaseAssessmentAsync('7')
    const saved = await saveGuidedCaseAsync(draft, '7', { slug: 'case-v1' })
    expect(saved).toBeTruthy()
  })
})
