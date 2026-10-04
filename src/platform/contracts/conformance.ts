import type { z } from 'zod'
import type { components } from '@/data/contracts/openapi.generated'
import {
  apiConversationSchema,
  apiConversationSummaryPageSchema,
  apiReportSchema,
  apiReportSummaryPageSchema,
  apiProblemSchema,
  apiQuestionThreadSchema,
  apiStudentQuestionPageSchema,
} from './core'
import { apiLoginResponseSchema } from './auth'
import {
  apiCaseDraftSchema,
  apiCaseAuthoringSchema,
  apiCaseAttemptSchema,
  apiCaseAttemptSummarySchema,
  apiCaseAssessmentSchema,
  apiPatientMessageSchema,
  apiStageSubmissionSchema,
  apiMedicalReviewViewSchema,
} from './case'
import {
  apiLearningTaskSchema,
  apiLearningPlanSchema,
  apiLearningProfileSchema,
  apiLearningTaskAttemptSchema,
  apiLearningTaskStartSchema,
  apiNotificationPageSchema,
} from './learning'
import { apiTeacherClassSchema } from './teacher'
import { teacherContentActionSummarySchema } from './contentActions'
import {
  routePageSchema,
  routeDetailSchema,
  readingStepSchema,
  routeCaseSchema,
  routeCaseMessageResultSchema,
  studentFinalTestSchema,
  teacherFinalTestSchema,
  learningResultSchema,
  teacherLearningResultReadSchema,
  learningRouteGenerationSchema,
  finalTestReleaseSchema,
} from './learningRoutes'

// Compile-time output compatibility: backend DTO changes must also update runtime validators.
type ContractSchema<T> = z.ZodType<T, unknown>

apiConversationSchema satisfies ContractSchema<components['schemas']['ConversationRead']>
apiConversationSummaryPageSchema satisfies ContractSchema<components['schemas']['ConversationSummaryPage']>
apiReportSchema satisfies ContractSchema<components['schemas']['ReportRead']>
apiReportSummaryPageSchema satisfies ContractSchema<components['schemas']['ReportSummaryPage']>
apiProblemSchema satisfies ContractSchema<components['schemas']['ProblemRead']>
apiQuestionThreadSchema satisfies ContractSchema<components['schemas']['QuestionThreadRead']>
apiStudentQuestionPageSchema.shape.items satisfies ContractSchema<components['schemas']['StudentQuestionRead'][]>
apiLoginResponseSchema satisfies ContractSchema<components['schemas']['LoginResponse']>
apiCaseDraftSchema satisfies ContractSchema<components['schemas']['CaseDraftGenerateResponse']>
apiCaseAuthoringSchema satisfies ContractSchema<components['schemas']['ProblemAuthoringRead']>
apiCaseAttemptSchema satisfies ContractSchema<components['schemas']['CaseAttemptRead']>
apiCaseAttemptSummarySchema satisfies ContractSchema<components['schemas']['CaseAttemptSummaryRead']>
apiCaseAssessmentSchema satisfies ContractSchema<components['schemas']['CaseAssessmentRead']>
apiPatientMessageSchema satisfies ContractSchema<components['schemas']['PatientMessageRead']>
apiStageSubmissionSchema satisfies ContractSchema<components['schemas']['StageSubmissionRead']>
apiMedicalReviewViewSchema satisfies ContractSchema<components['schemas']['MedicalReviewViewRead']>
apiLearningTaskSchema satisfies ContractSchema<components['schemas']['LearningTaskPublic']>
apiLearningPlanSchema satisfies ContractSchema<components['schemas']['LearningPlanRead']>
apiLearningProfileSchema satisfies ContractSchema<components['schemas']['LearningProfileRead']>
apiLearningTaskAttemptSchema satisfies ContractSchema<components['schemas']['LearningTaskAttemptRead']>
apiLearningTaskStartSchema satisfies ContractSchema<components['schemas']['LearningTaskStartRead']>
apiNotificationPageSchema satisfies ContractSchema<components['schemas']['NotificationListRead']>
apiTeacherClassSchema satisfies ContractSchema<components['schemas']['ClassRead']>
teacherContentActionSummarySchema satisfies ContractSchema<components['schemas']['TeacherContentActionSummary']>
routePageSchema satisfies ContractSchema<components['schemas']['RoutePage']>
routeDetailSchema satisfies ContractSchema<components['schemas']['RouteDetail']>
readingStepSchema satisfies ContractSchema<components['schemas']['ReadingStep']>
routeCaseSchema satisfies ContractSchema<components['schemas']['CaseRead']>
routeCaseMessageResultSchema satisfies ContractSchema<components['schemas']['CaseMessageResult']>
studentFinalTestSchema satisfies ContractSchema<components['schemas']['StudentTest']>
teacherFinalTestSchema satisfies ContractSchema<components['schemas']['TeacherTest']>
learningResultSchema satisfies ContractSchema<components['schemas']['LearningResult']>
teacherLearningResultReadSchema satisfies ContractSchema<components['schemas']['TeacherLearningResult']>
learningRouteGenerationSchema satisfies ContractSchema<components['schemas']['RetryReceipt']>
finalTestReleaseSchema satisfies ContractSchema<components['schemas']['ReleaseReceipt']>
