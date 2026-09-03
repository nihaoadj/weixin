import * as local from './demoCaseStore'
import type { CaseCatalogPort, CaseRepository } from '@/features/training/domain/ports'
import type { StageAnswer } from '@/types/case'

export class DemoTrainingRepository implements CaseRepository {
  constructor(catalog: CaseCatalogPort) {
    local.configureDemoCaseCatalog(catalog)
  }

  async getCaseAttemptsAsync() {
    return local.demoAttempts()
  }

  async getCaseAttemptAsync(id: string) {
    return local.demoFind(id)
  }

  async startCaseAttemptAsync(problemId: string, retryOfId?: string) {
    return local.demoStart(problemId, retryOfId)
  }

  async sendPatientMessageAsync(id: string, content: string) {
    const attempt = local.demoMessage(id, content)
    return attempt.messages[attempt.messages.length - 1]
  }

  async submitCaseStageAsync(id: string, answer: StageAnswer) {
    local.demoSubmit(id, answer)
  }

  async completeCaseAttemptAsync(id: string) {
    return local.demoComplete(id)
  }

  async getCaseAssessmentAsync(id: string) {
    return local.demoAssessments().find((item) => item.attemptId === id)
  }
}
