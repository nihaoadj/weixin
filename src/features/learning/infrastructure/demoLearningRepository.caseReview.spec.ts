import { describe, expect, it } from 'vitest'
import { demoCaseCatalog } from '@/features/content/infrastructure/demoCaseContentStore'
import { saveSession } from '@/features/identity/public'
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

describe('Demo independent case adapter', () => {
  it('keeps independent case attempts and ownership isolated', async () => {
    const training = new DemoTrainingRepository({ findCaseDraft: demoCaseCatalog })
    student('demo-independent-case-owner')

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

    student('demo-independent-case-other')
    await expect(training.getCaseAttemptAsync(attempt.id)).resolves.toBeUndefined()
    student('demo-independent-case-owner')
    await expect(training.getCaseAttemptAsync(attempt.id)).resolves.toMatchObject({ id: attempt.id })
  })
})
