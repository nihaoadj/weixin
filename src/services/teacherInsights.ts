import { toProblemView, optional } from '@/data/mappers/presentation'
import { isApiMode } from '@/config/runtime'
import { apiTeacherRepository } from '@/data/adapters/apiTeacherRepository'
import { demoTeacherRepository } from '@/data/adapters/demoTeacherRepository'
import type { TeacherRepository } from '@/data/repositories/teacher'
export type {
  AnalyticsCase,
  AnalyticsDimension,
  AnalyticsOverview,
  AnalyticsStudent,
  TeacherClass,
  TeacherStudent,
} from '@/types/teacher'
const repository: TeacherRepository = isApiMode() ? apiTeacherRepository : demoTeacherRepository
export const getTeacherClasses = repository.getTeacherClasses.bind(repository)
export const createTeacherClass = repository.createTeacherClass.bind(repository)
export const updateTeacherClass = repository.updateTeacherClass.bind(repository)
export const getClassStudents = repository.getClassStudents.bind(repository)
export const addStudentToClass = repository.addStudentToClass.bind(repository)
export const removeStudentFromClass = repository.removeStudentFromClass.bind(repository)
export const getAnalyticsOverview = repository.getAnalyticsOverview.bind(repository)
export const getReviewQueue = async (...args: Parameters<TeacherRepository['getReviewQueue']>) =>
  (await repository.getReviewQueue(...args)).map(toProblemView)
export const getReviewView = async (...args: Parameters<TeacherRepository['getReviewView']>) =>
  optional(await repository.getReviewView(...args), toProblemView)
export const getAnalyticsCase = repository.getAnalyticsCase.bind(repository)
export const getAnalyticsStudent = repository.getAnalyticsStudent.bind(repository)
export const submitMedicalReview = async (...args: Parameters<TeacherRepository['submitMedicalReview']>) =>
  toProblemView(await repository.submitMedicalReview(...args))
export const submitCaseForMedicalReview = async (
  ...args: Parameters<TeacherRepository['submitCaseForMedicalReview']>
) => toProblemView(await repository.submitCaseForMedicalReview(...args))
