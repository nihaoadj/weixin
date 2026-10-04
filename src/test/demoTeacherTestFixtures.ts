import type { TeacherFinalTest } from '@/features/learning/domain/finalTests'

type DemoReader = Pick<
  typeof import('@/features/learning/infrastructure/demoLearningRoutes'),
  'readDemoTeacherClassroomRoutes' | 'demoLearningRoutes'
>

/** Test setup uses the retained PBL projection and authorized detail, never a retired UI list. */
export async function readTeacherTestFixtures(demo: DemoReader, classId: number, sessionId?: number | string) {
  const routes = await demo.readDemoTeacherClassroomRoutes(classId, sessionId)
  const items: TeacherFinalTest[] = await Promise.all(
    routes.map((route) => demo.demoLearningRoutes.getTeacherFinalTest(route.finalTestId)),
  )
  return { items }
}
