import { configureRuntimeMode, getRuntimeMode, type RuntimeMode } from '@/platform/runtime'
import { ApiQaRepository } from '@/features/qa/infrastructure/apiQaRepository'
import { DemoQaRepository } from '@/features/qa/infrastructure/demoQaRepository'
import { ApiReportRepository } from '@/features/reports/infrastructure/apiReportRepository'
import { DemoReportRepository } from '@/features/reports/infrastructure/demoReportRepository'
import { ApiContentRepository } from '@/features/content/infrastructure/apiContentRepository'
import { DemoContentRepository } from '@/features/content/infrastructure/demoContentRepository'
import { demoCaseCatalog } from '@/features/content/infrastructure/demoCaseContentStore'
import { ensureDemoData } from '@/bootstrap/demoData'
import { ApiTrainingRepository } from '@/features/training/infrastructure/apiTrainingRepository'
import { DemoTrainingRepository } from '@/features/training/infrastructure/demoTrainingRepository'
import { apiLearningRepository } from '@/features/learning/infrastructure/apiLearningRepository'
import {
  configureDemoStudyDialogues,
  configureDemoTeacherFeedback,
  demoLearningRepository,
} from '@/features/learning/infrastructure/demoLearningRepository'
import { apiClassroomRepository } from '@/features/classroom/infrastructure/apiClassroomRepository'
import { demoClassroomRepository } from '@/features/classroom/infrastructure/demoClassroomRepository'
import { apiAnalyticsRepository } from '@/features/analytics/infrastructure/apiAnalyticsRepository'
import { demoAnalyticsRepository } from '@/features/analytics/infrastructure/demoAnalyticsRepository'
import { configureSessionService } from '@/features/identity/application/session'
import { createSessionDependencies } from '@/features/identity/infrastructure/sessionDependencies'
import type { SessionPort } from '@/features/identity/domain/ports'
import { configureSessionReader } from '@/platform/session/context'
import { createMedicalAssistant, type MedicalAssistantPort } from '@/features/qa/application/medicalAssistant'
import { apiMedicalAssistant } from '@/features/qa/infrastructure/apiMedicalAssistant'
import { demoMedicalAssistant } from '@/features/qa/infrastructure/demoMedicalAssistant'
import type { QaRepository } from '@/features/qa/domain/ports'
import type { ReportRepository } from '@/features/reports/domain/ports'
import type { ContentRepository } from '@/features/content/domain/ports'
import type { CaseRepository } from '@/features/training/domain/ports'
import type { LearningRepository } from '@/features/learning/domain/ports'
import type { ClassroomRepository } from '@/features/classroom/domain/ports'
import type { AnalyticsRepository } from '@/features/analytics/domain/ports'
import type { PblRepository } from '@/features/pbl/domain/ports'
import { ApiPblRepository } from '@/features/pbl/infrastructure/apiPblRepository'
import { DemoPblRepository } from '@/features/pbl/infrastructure/demoPblRepository'

export interface ApplicationServices {
  mode: RuntimeMode
  session: SessionPort
  qa: QaRepository
  reports: ReportRepository
  content: ContentRepository
  training: CaseRepository
  learning: LearningRepository
  classroom: ClassroomRepository
  analytics: AnalyticsRepository
  medicalAssistant: MedicalAssistantPort
  pbl: PblRepository
  ensureDemoData(): void
}

let services: ApplicationServices | undefined
let servicesMode: RuntimeMode | undefined

/**
 * The only runtime composition root. All feature public entries consume this object;
 * adapters never choose API versus Demo themselves.
 */
export function getApplicationServices(): ApplicationServices {
  const mode = getRuntimeMode()
  if (services && servicesMode === mode) return services

  configureRuntimeMode(mode)
  const session = configureSessionService(createSessionDependencies(mode))
  configureSessionReader(() => session.getSession())
  const content: ContentRepository = mode === 'api' ? new ApiContentRepository() : new DemoContentRepository()
  let qa: QaRepository
  let reports: ReportRepository
  if (mode === 'api') {
    qa = new ApiQaRepository()
    reports = new ApiReportRepository()
  } else {
    const demoReportsRef: { current?: ReportRepository } = {}
    qa = new DemoQaRepository(content, {
      getReports: () => demoReportsRef.current?.getReports() || Promise.resolve([]),
    })
    const demoReports = new DemoReportRepository(qa)
    demoReportsRef.current = demoReports
    reports = demoReports
  }
  const training: CaseRepository =
    mode === 'api' ? new ApiTrainingRepository() : new DemoTrainingRepository({ findCaseDraft: demoCaseCatalog })
  const classroom: ClassroomRepository = mode === 'api' ? apiClassroomRepository : demoClassroomRepository
  const analytics: AnalyticsRepository = mode === 'api' ? apiAnalyticsRepository : demoAnalyticsRepository
  const demoPbl = mode === 'demo' ? new DemoPblRepository(content) : undefined
  const pbl: PblRepository = mode === 'api' ? new ApiPblRepository() : demoPbl!
  // 微信开发者工具热更新时可能暂时保留旧的 Demo 学习模块。此时仍应让应用启动，
  // 而不是因新 wiring 与旧模块的短暂版本不一致卡在启动页。重新完整编译后会正常装配。
  if (mode === 'demo' && typeof configureDemoStudyDialogues === 'function') {
    configureDemoStudyDialogues(pbl)
  }
  if (mode === 'demo' && demoPbl && typeof configureDemoTeacherFeedback === 'function') {
    configureDemoTeacherFeedback(demoPbl)
  }
  const learning: LearningRepository = mode === 'api' ? apiLearningRepository : demoLearningRepository

  services = {
    mode,
    session,
    qa,
    reports,
    content,
    training,
    learning,
    classroom,
    analytics,
    medicalAssistant: createMedicalAssistant(mode, { api: apiMedicalAssistant, demo: demoMedicalAssistant }),
    pbl,
    ensureDemoData: mode === 'demo' ? ensureDemoData : () => undefined,
  }
  servicesMode = mode
  return services
}
