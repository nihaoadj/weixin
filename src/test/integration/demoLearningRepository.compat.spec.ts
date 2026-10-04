import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  configureDemoStudyDialogues,
  configureDemoKnowledgeCatalog,
  demoLearningRepository,
} from '@/features/learning/infrastructure/demoLearningRepository'

import { readDemoKnowledgeCatalog } from '@/features/content/infrastructure/demoKnowledgeCatalog'

beforeEach(() => configureDemoKnowledgeCatalog(readDemoKnowledgeCatalog))

vi.mock('@/platform/session/context', () => ({
  getSessionContext: () => ({ openid: 't39-demo-student' }),
}))

afterEach(() => vi.unstubAllGlobals())

describe('Demo learning on the WeChat base library', () => {
  it('uses the catalog reader supplied by the composition root', async () => {
    const catalog = readDemoKnowledgeCatalog().slice(0, 1)
    const readCatalog = vi.fn(() => catalog)
    configureDemoKnowledgeCatalog(readCatalog)

    expect(await demoLearningRepository.getKnowledgeCatalog()).toEqual(catalog)
    expect(readCatalog).toHaveBeenCalledTimes(1)
  })

  it('starts and reloads a study path without structuredClone while isolating returned state', async () => {
    vi.stubGlobal('structuredClone', undefined)
    configureDemoStudyDialogues({
      createDialogue: async () => ({
        session: { id: 't39-dialogue' },
        participation: { currentPhase: 'problem_framing' },
      }),
      dialogues: async () => ({
        items: [{ id: 't39-dialogue', goalPointCodes: ['pathology.cell-injury.adaptation'], phase: 'problem_framing' }],
        total: 1,
        limit: 100,
        offset: 0,
      }),
      dialogue: async () => ({ participation: { currentPhase: 'problem_framing' } }),
    })

    const started = await demoLearningRepository.startStudyPath({
      pointCode: 'pathology.cell-injury.adaptation',
      clientId: 't39-client',
      interactionStyle: 'guided',
    })
    expect(started.activeSession?.sessionId).toBe('t39-dialogue')
    started.material.objective = 'changed by caller'
    started.sessions[0]!.sessionId = 'caller-change'

    const reloaded = await demoLearningRepository.getStudyPath('pathology.cell-injury.adaptation')
    expect(reloaded.material.objective).not.toBe('changed by caller')
    expect(reloaded.sessions[0]?.sessionId).toBe('t39-dialogue')
  })
})
