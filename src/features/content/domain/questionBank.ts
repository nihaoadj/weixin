export type TeacherQuestionBankTaskType = 'retest' | 'knowledge_review' | 'discussion' | 'micro_drill'
export type TeacherQuestionBankStatus = 'active' | 'archived'

export interface TeacherQuestionBankContent {
  taskType: TeacherQuestionBankTaskType
  title: string
  prompt: string
  options: string[]
  answer: Record<string, unknown>
  explanation: string
  pointCodes: string[]
  dimensionIds: string[]
}

export interface TeacherQuestionBankSource extends TeacherQuestionBankContent {
  sourceType: 'route_test_question'
  sourceId: string
  sourceDigest: string
}

export interface TeacherQuestionBankItem extends TeacherQuestionBankContent {
  id: number
  version: number
  status: TeacherQuestionBankStatus
  medicalReviewStatus: string | null
  updatedAt: string
}

export interface TeacherQuestionBankPage {
  items: TeacherQuestionBankItem[]
  total: number
  limit: number
  offset: number
}

export interface TeacherQuestionBankFilters {
  status?: TeacherQuestionBankStatus
  pointCode?: string
  taskType?: TeacherQuestionBankTaskType
  query?: string
  limit?: number
  offset?: number
}

export interface TeacherQuestionBankImportInput extends TeacherQuestionBankSource {
  clientRequestId: string
  deidentified: true
}
