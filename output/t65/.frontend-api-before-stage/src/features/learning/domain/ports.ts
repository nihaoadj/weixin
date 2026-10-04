import type {
  KnowledgePoint,
  KnowledgeMapPoint,
  RecallReveal,
  ReviewCard,
  ReviewDashboard,
  ReviewGrade,
  ReviewItem,
} from '@/types/knowledge'
import type { StudyPathState } from '@/types/study'

/** Autonomous knowledge learning and review capability retained alongside T44 routes. */
export interface LearningRepository {
  getStudyPath(pointCode: string): Promise<StudyPathState>
  startStudyPath(input: {
    pointCode: string
    clientId: string
    interactionStyle: 'guided' | 'direct'
  }): Promise<StudyPathState>
  getKnowledgeCatalog(): Promise<KnowledgePoint[]>
  getKnowledgeMap(): Promise<KnowledgeMapPoint[]>
  createExitQuiz(topicCodes: string[]): Promise<ReviewCard[]>
  getReviewDashboard(): Promise<ReviewDashboard>
  getDueReviewQueue(): Promise<ReviewCard[]>
  gradeObjectiveCard(
    cardCode: string,
    selectedOption: number,
    confidence: 'low' | 'medium' | 'high',
  ): Promise<ReviewGrade>
  revealRecallCard(cardId: number): Promise<RecallReveal>
  rateRecallCard(cardId: number, rating: 'again' | 'hard' | 'good' | 'easy'): Promise<ReviewGrade>
  captureManualReviewItem(input: {
    pointCode: string
    sourceType: string
    sourceId: string
    note?: string
  }): Promise<ReviewItem>
  dismissReviewItem(id: number): Promise<void>
}
