import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import * as identity from '@/features/identity/public'
import * as learning from '@/features/learning/public'
import { readDemoStudentLearningInsightsRoutes } from '@/features/learning/infrastructure/demoLearningRoutes'
import * as pbl from '@/features/pbl/public'

const createdAt = new Date(0).toISOString()
const student = (openid: string) => ({ openid, role: 'student' as const, nickName: openid, avatarUrl: '', createdAt })

describe('Demo student learning insights wiring', () => {
  beforeEach(() => {
    vi.stubEnv('VITE_APP_MODE', 'demo')
  })

  afterEach(() => vi.unstubAllEnvs())

  it('reads real current-user seed state and isolates private dialogue records', async () => {
    identity.saveSession(student('demo_student'))
    const initial = await learning.getStudentLearningInsights()
    const routes = readDemoStudentLearningInsightsRoutes()
    expect(initial.summary.dashboard).toMatchObject({
      dataBasis: 'synthetic_demo',
      studyDurationBasis: 'recorded_reading',
    })
    expect(routes.length).toBeGreaterThan(0)
    expect(routes.every((route) => typeof route.progressLabel === 'string' && route.progressLabel.length > 0)).toBe(
      true,
    )
    for (const route of routes) {
      expect(Object.keys(route).sort()).toEqual(
        [
          'id',
          'sessionLocator',
          'title',
          'goalPointCodes',
          'status',
          'progressLabel',
          'completedSteps',
          'totalSteps',
          'updatedAt',
          'accumulatedReadingSeconds',
          'result',
        ].sort(),
      )
      for (const question of route.result?.questions || [])
        expect(Object.keys(question).sort()).toEqual(['earned', 'pointCode', 'possible'])
    }
    expect(initial.items.map((item) => item.id)).toContain('demo-t44-autonomous')
    expect(initial.summary.dashboard.testedKnowledgeCount).toBeGreaterThan(0)

    identity.saveSession(student('demo_student_b'))
    const privateDialogue = await pbl.createLearningDialogue({
      clientSessionId: 'insights-private-isolation',
      interactionStyle: 'guided',
      goalPointCodes: ['pathology.inflammation.acute'],
    })
    const secondStudentPage = await learning.getStudentLearningInsights()
    expect(secondStudentPage.items.map((item) => item.id)).toContain(privateDialogue.session.id)

    identity.saveSession(student('demo_student'))
    const firstStudentPage = await learning.getStudentLearningInsights()
    expect(firstStudentPage.items.map((item) => item.id)).not.toContain(privateDialogue.session.id)
    expect(firstStudentPage.items.map((item) => item.id)).toContain('demo-t44-autonomous')
  })
})
