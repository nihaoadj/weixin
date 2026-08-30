import type { Problem } from './domain'
import type { CaseDraftGenerateResult } from './case'

export interface MedicalReviewEntry {
  id: string | number
  problemId?: number
  reviewerId?: number
  reviewerOpenid?: string
  reviewerName?: string
  decision: 'approved' | 'rejected'
  comment: string
  problemVersion: number
  caseDigest: string
  createdAt: string
}

export interface MedicalReviewView extends Problem {
  caseDefinition: CaseDraftGenerateResult['caseDefinition']
  rubric: CaseDraftGenerateResult['rubric']
  currentDigest: string
  authorNickname?: string
  reviews: MedicalReviewEntry[]
}

export type MedicalReviewRecord = Omit<MedicalReviewView, 'status'> & Pick<import('./records').Problem, 'status'>
