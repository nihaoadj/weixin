import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const demoStorageKeys = ['pbl:t44-demo', 'learningRoutes:t44-demo', 'learningRoutes:t44-demo:seed-version']
let resetDemoModules: (() => void) | undefined

beforeEach(() => {
  for (const key of demoStorageKeys) uni.removeStorageSync(key)
})

afterEach(() => {
  resetDemoModules?.()
  resetDemoModules = undefined
  for (const key of demoStorageKeys) uni.removeStorageSync(key)
})

async function seedReferenceClassroom() {
  vi.resetModules()
  const [pbl, learning, sessionContext, content, classroom] = await Promise.all([
    import('./demoPblRepository'),
    import('@/features/learning/infrastructure/demoLearningRoutes'),
    import('@/platform/session/context'),
    import('@/features/content/infrastructure/demoContentRepository'),
    import('@/features/classroom/infrastructure/demoClassroomRepository'),
  ])
  const teacher = {
    openid: 'demo_teacher',
    role: 'teacher' as const,
    nickName: '演示教师',
    avatarUrl: '',
    createdAt: new Date(0).toISOString(),
  }
  sessionContext.configureSessionReader(() => teacher)
  const repository = new pbl.DemoPblRepository(new content.DemoContentRepository())
  const students = repository.ensureReferenceStudents()
  learning.ensureDemoPblReferenceRoutes(students)
  pbl.configureDemoClassroomRouteStateReader(learning.readDemoTeacherClassroomRoutes)
  classroom.configureDemoReferenceStudents(students)
  resetDemoModules = () => {
    pbl.configureDemoClassroomRouteStateReader(async () => [])
    classroom.configureDemoReferenceStudents([])
    sessionContext.configureSessionReader(() => null)
  }
  return { pbl, learning, repository, students, classroom: classroom.demoClassroomRepository }
}

describe('T55 additive Demo PBL reference seed', () => {
  it('creates eight readable completed students and preserves an edited test on reseed', async () => {
    const { pbl, learning, repository, students, classroom } = await seedReferenceClassroom()
    const referenceIds = new Set(students.map((student) => student.studentId))
    expect(students).toHaveLength(8)

    const roster = await classroom.getClassStudents(1)
    const seededRoster = roster.filter((student) => referenceIds.has(student.id))
    expect(seededRoster).toHaveLength(8)
    expect(new Set(seededRoster.map((student) => student.id)).size).toBe(8)

    const dashboard = await repository.dashboard('1', 'demo-pbl-1')
    const completedReferenceStudents = dashboard.students.filter(
      (student) => referenceIds.has(Number(student.studentId)) && student.currentPhase === 'completed',
    )
    expect(completedReferenceStudents).toHaveLength(8)
    expect(completedReferenceStudents.every((student) => student.phaseStatus === 'completed')).toBe(true)
    expect(completedReferenceStudents.every((student) => student.snapshotId && student.finalTestId)).toBe(true)

    const referenceStudentsById = new Map(
      completedReferenceStudents.map((student) => [Number(student.studentId), student]),
    )
    for (const student of students) {
      const dashboardStudent = referenceStudentsById.get(student.studentId)!
      const linked = await repository.workItem(dashboardStudent.snapshotId!)
      expect(linked.diagnostic).toMatchObject({
        id: dashboardStudent.snapshotId,
        studentId: String(student.studentId),
        sessionId: 'demo-pbl-1',
        diagnosticStatus: 'ready',
      })
      expect(linked.workItem).toMatchObject({
        snapshotId: dashboardStudent.snapshotId,
        learningRouteId: student.routeId,
        finalTestId: student.finalTestId,
      })
      const test = await learning.demoLearningRoutes.getTeacherFinalTest(dashboardStudent.finalTestId!)
      expect(test).toMatchObject({
        id: student.finalTestId,
        routeId: student.routeId,
        classId: 1,
        sessionId: 1,
        studentId: student.studentId,
      })
    }

    const routeFacts = await learning.readDemoTeacherClassroomRoutes(1, 'demo-pbl-1')
    const referenceRoutes = routeFacts.filter((route) => referenceIds.has(route.studentId))
    expect(referenceRoutes).toHaveLength(8)
    const publishedStatuses = new Set([
      'published',
      'in_progress',
      'learning',
      'waiting_test_generation',
      'waiting_teacher',
      'ready_for_test',
      'testing',
      'grading',
      'completed',
    ])
    expect(referenceRoutes.filter((route) => publishedStatuses.has(route.status))).toHaveLength(2)
    expect(referenceRoutes.filter((route) => !publishedStatuses.has(route.status))).toHaveLength(6)

    const progressByStudent = new Map(
      dashboard.students
        .filter((student) => referenceIds.has(Number(student.studentId)))
        .map((student) => [Number(student.studentId), student.taskProgress]),
    )
    expect(progressByStudent.get(5501)).toEqual({ completed: 0, total: 8 })
    expect(progressByStudent.get(5507)).toEqual({ completed: 6, total: 8 })
    expect(progressByStudent.get(5508)).toEqual({ completed: 8, total: 8 })

    const editableStudent = students.find((student) => student.studentId === 5507)!
    const beforeEdit = await learning.demoLearningRoutes.getTeacherFinalTest(editableStudent.finalTestId)
    const editedExplanation = '教师已修改的参考测试说明，应在重复初始化后保留。'
    const editedQuestions = beforeEdit.questions.map((question, index) =>
      index === 0 ? { ...question, explanation: editedExplanation } : question,
    )
    const saved = await learning.demoLearningRoutes.saveTeacherFinalTest(
      editableStudent.finalTestId,
      't55-reference-seed-edit',
      beforeEdit.version,
      editedQuestions,
      '教师补充意见',
    )

    const repeatedStudents = repository.ensureReferenceStudents()
    learning.ensureDemoPblReferenceRoutes(repeatedStudents)
    pbl.configureDemoClassroomRouteStateReader(learning.readDemoTeacherClassroomRoutes)
    const reloadedRepository = new pbl.DemoPblRepository(
      new (await import('@/features/content/infrastructure/demoContentRepository')).DemoContentRepository(),
    )
    const reloaded = await reloadedRepository.dashboard('1', 'demo-pbl-1')
    const reloadedReferenceStudents = reloaded.students.filter((student) => referenceIds.has(Number(student.studentId)))
    expect(repeatedStudents).toHaveLength(8)
    expect(reloadedReferenceStudents).toHaveLength(8)
    expect(new Set(reloadedReferenceStudents.map((student) => student.studentId)).size).toBe(8)

    const diagnostics = await reloadedRepository.diagnostics({ classId: '1', sessionId: 'demo-pbl-1' })
    const referenceDiagnostics = diagnostics.items.filter((item) => referenceIds.has(Number(item.studentId)))
    expect(referenceDiagnostics).toHaveLength(8)
    expect(new Set(referenceDiagnostics.map((item) => item.id)).size).toBe(8)
    const afterReseed = await learning.demoLearningRoutes.getTeacherFinalTest(editableStudent.finalTestId)
    expect(afterReseed.version).toBe(saved.version)
    expect(afterReseed.feedbackDraft).toBe('教师补充意见')
    expect(afterReseed.questions).toHaveLength(beforeEdit.questions.length)
    expect(afterReseed.questions[0].explanation).toBe(editedExplanation)
  })
})
