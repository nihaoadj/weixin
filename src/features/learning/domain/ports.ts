import type { KnowledgePoint, KnowledgeMapPoint } from '@/types/knowledge'
import type { StudyPathState } from '@/types/study'

/** Knowledge catalog, map, and dialogue-linked study entry retained alongside T44 routes. */
export interface LearningRepository {
  getStudyPath(pointCode: string): Promise<StudyPathState>
  startStudyPath(input: {
    pointCode: string
    clientId: string
    interactionStyle: 'guided' | 'direct'
  }): Promise<StudyPathState>
  getKnowledgeCatalog(): Promise<KnowledgePoint[]>
  getKnowledgeMap(): Promise<KnowledgeMapPoint[]>
}
