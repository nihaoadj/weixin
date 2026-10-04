import { configureRuntimeMode, getRuntimeMode, type RuntimeMode } from '@/platform/runtime'
import { ApiQaRepository } from '@/features/qa/infrastructure/apiQaRepository'
import { DemoQaRepository } from '@/features/qa/infrastructure/demoQaRepository'
import { ApiReportRepository } from '@/features/reports/infrastructure/apiReportRepository'
import { DemoReportRepository } from '@/features/reports/infrastructure/demoReportRepository'
import { ApiContentRepository } from '@/features/content/infrastructure/apiContentRepository'
import {
  DemoContentRepository,
  configureDemoTeacherQuestionBankSource,
} from '@/features/content/infrastructure/demoContentRepository'
import { readDemoKnowledgeCatalog } from '@/features/content/infrastructure/demoKnowledgeCatalog'
import { demoCaseCatalog, configureDemoCaseBeforeChange } from '@/features/content/infrastructure/demoCaseContentStore'
import { freezeExistingDemoCaseAttempts } from '@/features/training/infrastructure/demoCaseStore'
import { ensureDemoData } from '@/bootstrap/demoData'
import { demoTeacherInsightsSamples } from '@/bootstrap/demoTeacherInsightsSamples'
import { ApiTrainingRepository } from '@/features/training/infrastructure/apiTrainingRepository'
import { DemoTrainingRepository } from '@/features/training/infrastructure/demoTrainingRepository'
import { apiLearningRepository } from '@/features/learning/infrastructure/apiLearningRepository'
import { apiLearningRoutes } from '@/features/learning/infrastructure/apiLearningRoutes'
import { ApiStudentLearningInsightsRepository } from '@/features/learning/infrastructure/apiStudentLearningInsights'
import {
  demoLearningRoutes,
  ensureDemoRouteCompletion,
  getDemoTeacherQuestionBankSource,
  readDemoStudentLearningInsightsRoutes,
  readDemoTeacherClassroomRoutes,
  ensureDemoPblReferenceRoutes,
  ensureDemoInsightsRoutes,
  readDemoTeacherInsightsFacts,
} from '@/features/learning/infrastructure/demoLearningRoutes'
import { DemoStudentLearningInsightsRepository } from '@/features/learning/infrastructure/demoStudentLearningInsights'
import {
  configureDemoStudyDialogues,
  configureDemoKnowledgeCatalog,
  demoLearningRepository,
} from '@/features/learning/infrastructure/demoLearningRepository'
import {
  configureDemoLearningRouteCompletion,
  configureDemoClassroomRouteStateReader,
} from '@/features/pbl/infrastructure/demoPblRepository'
import { apiClassroomRepository } from '@/features/classroom/infrastructure/apiClassroomRepository'
import {
  demoClassroomRepository,
  configureDemoReferenceStudents,
  configureDemoInsightsStudents,
} from '@/features/classroom/infrastructure/demoClassroomRepository'
import { apiAnalyticsRepository } from '@/features/analytics/infrastructure/apiAnalyticsRepository'
import { demoAnalyticsRepository } from '@/features/analytics/infrastructure/demoAnalyticsRepository'
import { configureDemoTeacherInsightsFacts } from '@/features/analytics/infrastructure/demoTeacherInsights'
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
import type { LearningRoutesPort } from '@/features/learning/domain/learningRoutesPort'
import type { StudentLearningInsightsPort } from '@/features/learning/domain/studentLearningInsights'
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
  learningRoutes: LearningRoutesPort
  studentInsights: StudentLearningInsightsPort
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
  const classroom: ClassroomRepository = mode === 'api' ? apiClassroomRepository : demoClassroomRepository
  let qa: QaRepository
  let reports: ReportRepository
  if (mode === 'api') {
    qa = new ApiQaRepository()
    reports = new ApiReportRepository()
  } else {
    qa = new DemoQaRepository(content)
    reports = new DemoReportRepository()
  }
  const demoTraining = mode === 'demo' ? new DemoTrainingRepository({ findCaseDraft: demoCaseCatalog }) : undefined
  if (mode === 'demo') configureDemoCaseBeforeChange(freezeExistingDemoCaseAttempts)
  const training: CaseRepository = mode === 'api' ? new ApiTrainingRepository() : demoTraining!
  const analytics: AnalyticsRepository = mode === 'api' ? apiAnalyticsRepository : demoAnalyticsRepository
  if (mode === 'demo') {
    configureDemoClassroomRouteStateReader(readDemoTeacherClassroomRoutes)
  }
  const demoPbl = mode === 'demo' ? new DemoPblRepository(content) : undefined
  const pbl: PblRepository = mode === 'api' ? new ApiPblRepository() : demoPbl!
  if (mode === 'demo') {
    configureDemoTeacherInsightsFacts({
      readRoutes: readDemoTeacherInsightsFacts,
      readDiagnoses: () => demoPbl!.teacherInsightsRecords(),
      readDiscussions: () => demoPbl!.teacherDiscussionRecords(),
      readScope: async () => {
        const user = session.getSession()
        if (user?.role !== 'teacher' || user.openid !== 'demo_teacher') return { classes: [], students: [] }
        const classes = await classroom.getTeacherClasses()
        const students = new Map<number, { id: number; name: string; classIds: number[] }>()
        for (const item of classes) {
          for (const student of await classroom.getClassStudents(item.id)) {
            const existing = students.get(student.id)
            if (existing) existing.classIds.push(item.id)
            else students.set(student.id, { id: student.id, name: student.nickname, classIds: [item.id] })
          }
        }
        return { classes, students: [...students.values()] }
      },
    })
  }
  // 微信开发者工具热更新时可能暂时保留旧的 Demo 学习模块。此时仍应让应用启动，
  // 而不是因新 wiring 与旧模块的短暂版本不一致卡在启动页。重新完整编译后会正常装配。
  if (mode === 'demo' && typeof configureDemoStudyDialogues === 'function') {
    configureDemoStudyDialogues(pbl)
  }
  if (mode === 'demo') configureDemoKnowledgeCatalog(readDemoKnowledgeCatalog)
  const learning: LearningRepository = mode === 'api' ? apiLearningRepository : demoLearningRepository
  const learningRoutes: LearningRoutesPort = mode === 'api' ? apiLearningRoutes : demoLearningRoutes
  const studentInsights: StudentLearningInsightsPort =
    mode === 'api'
      ? new ApiStudentLearningInsightsRepository()
      : new DemoStudentLearningInsightsRepository({
          readDialogues: () => demoPbl!.studentInsightsRecords(),
          readRoutes: async () => readDemoStudentLearningInsightsRoutes(),
          readKnowledgeCatalog: () => learning.getKnowledgeCatalog(),
        })
  if (mode === 'demo') configureDemoLearningRouteCompletion(ensureDemoRouteCompletion)
  if (mode === 'demo' && content instanceof DemoContentRepository) {
    configureDemoTeacherQuestionBankSource({ getTeacherQuestionBankSource: getDemoTeacherQuestionBankSource })
  }

  services = {
    mode,
    session,
    qa,
    reports,
    content,
    training,
    learning,
    learningRoutes,
    studentInsights,
    classroom,
    analytics,
    medicalAssistant: createMedicalAssistant(mode, { api: apiMedicalAssistant, demo: demoMedicalAssistant }),
    pbl,
    ensureDemoData:
      mode === 'demo'
        ? () => {
            ensureDemoData()
            if (content instanceof DemoContentRepository) content.ensureDemoContentSamples()
            const referenceStudents = demoPbl!.ensureReferenceStudents()
            ensureDemoPblReferenceRoutes(referenceStudents)
            configureDemoReferenceStudents(referenceStudents)
            demoPbl!.ensureInsightsSamples(demoTeacherInsightsSamples)
            ensureDemoInsightsRoutes(demoTeacherInsightsSamples)
            configureDemoInsightsStudents(demoTeacherInsightsSamples)
          }
        : () => undefined,
  }
  servicesMode = mode
  return services
}
