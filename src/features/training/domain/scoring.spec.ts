import { describe, expect, it } from 'vitest'
import { showcaseDraft } from '@/features/content/infrastructure/demoSeeds'
import type { CaseAttempt } from '@/types/case'
import { scoreDemoCase } from '@/features/training/domain/scoring'

const attempt = (answer: unknown, stageId: CaseAttempt['currentStage'] = 'management'): CaseAttempt => ({
  id: 'attempt-1',
  problemId: 'cap-undergraduate-showcase',
  problemVersion: 1,
  status: 'completed',
  currentStage: stageId,
  opening: showcaseDraft.caseDefinition.opening,
  messages: [{ id: 'm1', role: 'user', content: '患者发热，氧合下降。', createdAt: new Date(0).toISOString() }],
  submissions: [
    {
      id: 's1',
      stageId: 'management',
      answer: answer as never,
      feedback: '',
      createdAt: new Date(0).toISOString(),
    },
  ],
  assessmentReady: false,
  startedAt: new Date(0).toISOString(),
})

describe('deterministic Demo case scoring', () => {
  it('uses criterion hits, source evidence and critical cap', () => {
    const draft = structuredClone(showcaseDraft)
    const managementRubric = draft.rubric.dimensions.find((item) => item.id === 'management_safety')!
    managementRubric.criteria.push({
      id: 'management-extra',
      label: '处置依据',
      keywords: ['复查'],
      feedback: '补充复查计划。',
      critical: false,
    })
    const dimensions = scoreDemoCase(
      attempt({ stageId: 'management', items: [{ action: '观察', rationale: '评估氧合' }] }),
      draft,
    )
    const management = dimensions.find((item) => item.dimensionId === 'management_safety')!
    expect(management.score).toBe(50)
    expect(management.evidence.some((item) => item.includes('评估氧合'))).toBe(true)
    expect(management.evidence).not.toContain('氧合')
  })

  it('is repeatable for the same structured input', () => {
    const input = attempt({ stageId: 'management', items: [{ action: '评估氧合', rationale: '发热肺炎' }] })
    expect(scoreDemoCase(input, showcaseDraft)).toEqual(scoreDemoCase(input, showcaseDraft))
  })
})
