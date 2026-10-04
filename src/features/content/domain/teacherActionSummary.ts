export type TeacherContentActionSummary = {
  casesDraft: number
  casesRejected: number
  casesApproved: number
  questionsDraft: number
  questionsRejected: number
  cardsDraft: number
  cardsRejected: number
  medicalCasesPending: number | null
  medicalCardsPending: number | null
  asOf: string
}
