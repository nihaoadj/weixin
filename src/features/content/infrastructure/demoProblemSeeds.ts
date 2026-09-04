import type { Problem } from '@/types/domain'
import { showcaseDraft, additionalShowcaseDrafts } from './demoSeeds'
import catalog from './pathologyCatalog.generated.json'
export function createDemoProblems(): Problem[] {
  return Object.entries({ 'pathology.cell-injury-showcase': showcaseDraft, ...additionalShowcaseDrafts }).map(
    ([id, draft]) => ({
      id,
      slug: id,
      type: '病例分析',
      title: draft.title,
      description: draft.description,
      target: 'all',
      status: '已发布',
      time: new Date(0).toISOString(),
      contentType: 'guided_case',
      specialty: '病理学',
      difficulty: 'basic',
      estimatedMinutes: 15,
      version: 1,
      medicalReviewStatus: 'approved',
      opening: draft.caseDefinition.opening,
      knowledgePointCodes: catalog.filter((p) => p.case_slug === id).map((p) => p.code),
    }),
  )
}
