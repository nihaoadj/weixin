import { describe, expect, it } from 'vitest'
import { demoCaseCatalog } from '@/features/content/infrastructure/demoCaseContentStore'
import { saveSession } from '@/features/identity/public'
import { demoLearningRepository } from './demoLearningRepository'
import { DemoTrainingRepository } from '@/features/training/infrastructure/demoTrainingRepository'

const student = (openid: string) =>
  saveSession({
    role: 'student',
    openid,
    nickName: '病例学习学生',
    avatarUrl: '',
    createdAt: new Date(0).toISOString(),
    classIds: ['demo_class_1'],
  })

describe('Demo independent case and review adapters', () => {
  it('keeps independent case attempts working while manual review writes are retired', async () => {
    const training = new DemoTrainingRepository({ findCaseDraft: demoCaseCatalog })
    student('demo-independent-case-review-owner')

    const attempt = await training.startCaseAttemptAsync('pathology.inflammation-showcase')
    expect(attempt).toMatchObject({
      problemId: 'pathology.inflammation-showcase',
      status: 'in_progress',
      currentStage: 'history',
    })
    await expect(training.getCaseAttemptAsync(attempt.id)).resolves.toMatchObject({
      id: attempt.id,
      opening: attempt.opening,
    })

    const reviewInput = {
      pointCode: 'pathology.inflammation.acute',
      sourceType: 'independent_case_attempt',
      sourceId: attempt.id,
      note: '回顾本病例中的形态证据。',
    }
    await expect(demoLearningRepository.captureManualReviewItem(reviewInput)).rejects.toMatchObject({
      code: 'RETIRED_FLOW',
      statusCode: 409,
    })
    await expect(demoLearningRepository.dismissReviewItem(1)).rejects.toMatchObject({
      code: 'RETIRED_FLOW',
      statusCode: 409,
    })
    await expect(demoLearningRepository.getReviewDashboard()).resolves.toEqual({
      dueCount: 0,
      weakPointCodes: [],
      items: [],
    })
    student('demo-independent-case-review-other')
    await expect(demoLearningRepository.getReviewDashboard()).resolves.toMatchObject({ items: [] })
    await expect(training.getCaseAttemptAsync(attempt.id)).resolves.toBeUndefined()
    student('demo-independent-case-review-owner')
    await expect(training.getCaseAttemptAsync(attempt.id)).resolves.toMatchObject({ id: attempt.id })
  })
})
