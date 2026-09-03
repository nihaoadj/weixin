import type { AnalyticsRepository } from '@/features/analytics/domain/ports'
import type { AnalyticsCase, AnalyticsKnowledge, AnalyticsOverview, AnalyticsStudent } from '@/types/teacher'

export const demoAnalyticsRepository: AnalyticsRepository = {
  async getAnalyticsOverview(classId?: number, dateFrom?: string, dateTo?: string): Promise<AnalyticsOverview> {
    return {
      scope: { classId: classId || null, className: null, dateFrom: dateFrom || '', dateTo: dateTo || '' },
      studentCount: 0,
      publishedCaseCount: 0,
      eligiblePairs: 0,
      startedPairs: 0,
      completedPairs: 0,
      completionRate: null,
      currentAverageScore: null,
      averageImprovement: null,
      dimensions: [],
      weakDimensions: [],
      cases: [],
      students: [],
    }
  },
  async getAnalyticsCase(problemId: number): Promise<AnalyticsCase> {
    return {
      problem: { id: problemId, title: '', version: 1 },
      eligiblePairs: 0,
      startedPairs: 0,
      completedPairs: 0,
      completionRate: null,
      currentAverageScore: null,
      averageImprovement: null,
      averageDurationMinutes: null,
      dimensions: [],
      distribution: {},
      students: [],
    }
  },
  async getAnalyticsStudent(studentId: number): Promise<AnalyticsStudent> {
    return {
      student: { id: studentId, nickname: '' },
      assigned: 0,
      started: 0,
      completed: 0,
      completionRate: null,
      currentAverageScore: null,
      averageImprovement: null,
      dimensions: [],
      cases: [],
      timeline: [],
      learningPlan: null,
      practiceMastery: {},
    }
  },
  async getAnalyticsKnowledge(classId: number): Promise<AnalyticsKnowledge> {
    return {
      classId,
      className: '',
      participantCount: 0,
      dueBacklog: 0,
      objectiveCorrectRate: null,
      weakPoints: [],
      rankingsSuppressed: true,
    }
  },
}
