import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const teacher = {
  role: 'teacher' as const,
  openid: 'demo_teacher',
  nickName: '演示教师',
  avatarUrl: '',
  createdAt: new Date(0).toISOString(),
}

describe('T56 additive Demo teacher insights seed', () => {
  beforeEach(() => {
    vi.stubEnv('VITE_APP_MODE', 'demo')
  })

  afterEach(() => {
    vi.unstubAllEnvs()
    vi.resetModules()
  })

  it('seeds isolated class insights, readable results and preserves saved route progress on reseed', async () => {
    vi.resetModules()
    vi.stubEnv('VITE_APP_MODE', 'demo')
    const [{ getApplicationServices }, { demoTeacherInsightsSamples }] = await Promise.all([
      import('./wiring'),
      import('./demoTeacherInsightsSamples'),
    ])
    const services = getApplicationServices()
    await services.session.saveSession(teacher)

    expect(services.mode).toBe('demo')
    expect(await services.classroom.getTeacherClasses()).toEqual([
      { id: 1, name: '病理学演示班', code: 'demo_class_1', status: 'active', teacherId: 1 },
    ])
    expect(await services.classroom.getClassStudents(2)).toEqual([])
    await expect(services.analytics.getTeacherInsightsOverview({ classId: 2 })).rejects.toMatchObject({
      code: 'RESOURCE_NOT_FOUND',
    })
    await expect(services.learningRoutes.getTeacherFinalTestReviewQueue({ classId: 2 })).rejects.toMatchObject({
      code: 'RESOURCE_NOT_FOUND',
    })

    services.ensureDemoData()

    const classes = await services.classroom.getTeacherClasses()
    expect(classes.map((item) => item.id)).toEqual([1, 2])
    const class2Roster = await services.classroom.getClassStudents(2)
    expect(class2Roster).toHaveLength(12)
    expect(new Set(class2Roster.map((student) => student.id)).size).toBe(12)
    expect(class2Roster.map((student) => student.id).sort((a, b) => a - b)).toEqual(
      Array.from({ length: 12 }, (_, index) => 5601 + index),
    )

    const dateFilters = {
      classId: 2,
      dateFrom: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10),
      dateTo: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString().slice(0, 10),
    }
    const overview = await services.analytics.getTeacherInsightsOverview(dateFilters)
    expect(overview.scope.classId).toBe(2)
    expect(overview.studentCount).toBe(12)
    expect(overview.cohort).toMatchObject({ publishedRoutes: 15, completedTests: 12, completionRate: 80 })
    const class2ReviewQueue = await services.learningRoutes.getTeacherFinalTestReviewQueue({ classId: 2 })
    expect(class2ReviewQueue).toMatchObject({
      items: [],
      total: 0,
      counts: { pendingReview: 0, needsChanges: 0, generationFailed: 0 },
    })

    const rosterPage = await services.analytics.getTeacherInsightsStudents(dateFilters, 100, 0)
    expect(rosterPage.total).toBe(12)
    expect(rosterPage.items.map((student) => student.studentId).sort((a, b) => a - b)).toEqual(
      Array.from({ length: 12 }, (_, index) => 5601 + index),
    )
    expect(rosterPage.items.every((student) => student.classIds.includes(2))).toBe(true)

    const knowledge = await services.analytics.getTeacherInsightsKnowledge(dateFilters)
    expect(knowledge.resultCount).toBe(12)
    expect(knowledge.items.map((item) => item.pointCode).sort()).toEqual([
      'pathology.inflammation.acute',
      'pathology.inflammation.chronic',
      'pathology.inflammation.leukocytes',
      'pathology.inflammation.mediators',
      'pathology.inflammation.vascular',
    ])
    expect(
      knowledge.items.every(
        (item) =>
          item.objectiveCount > 0 && item.shortAnswerCount > 0 && item.pointsPossible > 0 && item.pointsAwarded > 0,
      ),
    ).toBe(true)

    const diagnoses = await services.analytics.getTeacherInsightsDiagnostics(dateFilters, 100, 0)
    expect(diagnoses.total).toBe(12)
    expect(diagnoses.items).toHaveLength(12)
    expect(diagnoses.knowledgeGaps).toEqual([
      expect.objectContaining({
        code: 'pathology.inflammation.vascular',
        studentCount: 2,
        diagnosisCount: 2,
      }),
    ])
    expect(diagnoses.reasoningIssues).toEqual([
      expect.objectContaining({ code: 'evidence_reasoning', studentCount: 1, diagnosisCount: 1 }),
    ])

    const pblSessions = await services.pbl.teacherSessions({ classId: '2' })
    expect(pblSessions.total).toBe(5)
    expect(pblSessions.items).toHaveLength(5)
    expect(new Set(pblSessions.items.map((session) => session.id)).size).toBe(5)
    expect(new Set(demoTeacherInsightsSamples.map((sample) => sample.sessionId)).size).toBe(5)
    for (const session of pblSessions.items) {
      const sample = demoTeacherInsightsSamples.find((item) => item.sessionId === session.id)
      expect(sample).toBeDefined()
      const sessionKnowledge = await services.analytics.getTeacherInsightsKnowledge({
        ...dateFilters,
        sessionId: session.id,
      })
      expect(sessionKnowledge.items.map((item) => item.pointCode)).toEqual([sample!.pointCode])
      expect(sessionKnowledge.resultCount).toBe(
        demoTeacherInsightsSamples.filter((item) => item.sessionId === session.id).length,
      )
    }

    const studentDetail = await services.analytics.getTeacherInsightsStudent(5601, dateFilters)
    expect(studentDetail.results).toHaveLength(1)
    const result = await services.learningRoutes.getTeacherRouteResult(studentDetail.results[0]!.resultId)
    expect(result).toMatchObject({ studentId: 5601, classId: 2, questionCount: 5, formatVersion: 'mixed_v2' })
    expect(result.questions).toHaveLength(5)
    expect(result.questions.map((question) => question.questionType)).toEqual([
      'single_choice',
      'single_choice',
      'single_choice',
      'multiple_choice',
      'short_answer',
    ])
    expect(
      result.questions.every((question) => question.prompt.trim().length > 0 && question.explanation.trim().length > 0),
    ).toBe(true)
    expect(result.questions.slice(0, 3).every((question) => question.selectedOption !== undefined)).toBe(true)
    expect(result.questions[3]!.selectedOptions).toEqual([1])
    expect(result.questions[3]!.correctOptions).toEqual([0, 2])
    expect(result.questions[3]!.pointsAwarded).toBe(0)
    expect(result.questions[4]!.selectedText).toContain('小动脉扩张')

    const class1Roster = await services.classroom.getClassStudents(1)
    expect(class1Roster).toHaveLength(10)
    expect(class1Roster.map((student) => student.id)).toEqual(
      expect.arrayContaining([1, 2, ...Array.from({ length: 8 }, (_, index) => 5501 + index)]),
    )
    expect(class1Roster.some((student) => student.id >= 5601 && student.id <= 5612)).toBe(false)
    const class1Insights = await services.analytics.getTeacherInsightsStudents({ ...dateFilters, classId: 1 }, 100, 0)
    expect(class1Insights.items.some((student) => student.studentId >= 5601 && student.studentId <= 5612)).toBe(false)
    const class1Dashboard = await services.pbl.dashboard('1', 'demo-pbl-1')
    expect(
      class1Dashboard.students.filter(
        (student) => Number(student.studentId) >= 5501 && Number(student.studentId) <= 5508,
      ),
    ).toHaveLength(8)
    expect(class1Dashboard.students.some((student) => Number(student.studentId) >= 5601)).toBe(false)

    const readCompletedResults = async () => {
      const studentDetails = await Promise.all(
        Array.from({ length: 12 }, (_, index) =>
          services.analytics.getTeacherInsightsStudent(5601 + index, dateFilters),
        ),
      )
      const resultReads = studentDetails.flatMap((detail) =>
        detail.results.map((item) => services.learningRoutes.getTeacherRouteResult(item.resultId)),
      )
      return Promise.all(resultReads)
    }
    const completedResultsBeforeReseed = await readCompletedResults()
    expect(completedResultsBeforeReseed).toHaveLength(12)

    const sampleWithPendingRoute = demoTeacherInsightsSamples.find((sample) => sample.studentId === 5607)!
    await services.session.saveSession({
      role: 'student',
      openid: sampleWithPendingRoute.openid,
      nickName: sampleWithPendingRoute.name,
      avatarUrl: '',
      createdAt: new Date(0).toISOString(),
      classIds: ['demo_insights_2'],
    })
    const pendingRouteId = `56000000-0000-4000-8000-${String(100000 + sampleWithPendingRoute.studentId).padStart(12, '0')}`
    const pendingRoute = await services.learningRoutes.getLearningRoute(pendingRouteId)
    const readingStep = pendingRoute.steps.find((step) => step.kind === 'reading')
    expect(readingStep).toBeDefined()
    const savedProgress = await services.learningRoutes.saveRouteReadingProgress(
      readingStep!.id,
      'start',
      't56-saved-pending-route-progress',
    )
    expect(savedProgress.leaseToken).toBeTruthy()

    await services.session.saveSession(teacher)
    services.ensureDemoData()
    const repeatedOverview = await services.analytics.getTeacherInsightsOverview(dateFilters)
    const repeatedStudents = await services.analytics.getTeacherInsightsStudents(dateFilters, 100, 0)
    const repeatedRoutes = await services.analytics.getTeacherInsightsKnowledge(dateFilters)
    const repeatedDiagnoses = await services.analytics.getTeacherInsightsDiagnostics(dateFilters, 100, 0)
    const completedResultsAfterReseed = await readCompletedResults()
    expect(repeatedOverview.cohort).toMatchObject({ publishedRoutes: 15, completedTests: 12, completionRate: 80 })
    expect(repeatedStudents.total).toBe(12)
    expect(new Set(repeatedStudents.items.map((student) => student.studentId)).size).toBe(12)
    expect(repeatedRoutes.items).toHaveLength(5)
    expect(repeatedDiagnoses.total).toBe(12)
    expect(completedResultsAfterReseed).toEqual(completedResultsBeforeReseed)

    await services.session.saveSession({
      role: 'student',
      openid: sampleWithPendingRoute.openid,
      nickName: sampleWithPendingRoute.name,
      avatarUrl: '',
      createdAt: new Date(0).toISOString(),
      classIds: ['demo_insights_2'],
    })
    const persistedReading = await services.learningRoutes.getLearningRouteStep(readingStep!.id)
    expect(persistedReading.readingProgress).toMatchObject({
      leaseToken: savedProgress.leaseToken,
      lastSeenAt: savedProgress.lastSeenAt,
    })
  })
})
