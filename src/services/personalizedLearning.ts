import { isApiMode } from '@/config/runtime'
import { apiLearningRepository } from '@/data/adapters/apiLearningRepository'
import { demoLearningRepository } from '@/data/adapters/demoLearningRepository'
import type { LearningRepository } from '@/data/repositories/learning'

const repository: LearningRepository = isApiMode() ? apiLearningRepository : demoLearningRepository
export const getLearningProfile = repository.getLearningProfile.bind(repository)
export const createLearningPlan = repository.createLearningPlan.bind(repository)
export const getCurrentLearningPlan = repository.getCurrentLearningPlan.bind(repository)
export const getLearningPlan = repository.getLearningPlan.bind(repository)
export const startLearningTask = repository.startLearningTask.bind(repository)
export const getLearningTaskAttempt = repository.getLearningTaskAttempt.bind(repository)
export const submitLearningTaskAttempt = repository.submitLearningTaskAttempt.bind(repository)
export const completeLearningPlan = repository.completeLearningPlan.bind(repository)
export const getLearningNotifications = repository.getLearningNotifications.bind(repository)
export const markLearningNotificationsRead = repository.markLearningNotificationsRead.bind(repository)
