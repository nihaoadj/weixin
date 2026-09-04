import { apiProblemSchema } from '@/platform/contracts/core'
import type { ApiProblem } from '@/platform/contracts/core'
import type { Problem } from '@/types/records'
import { AppError } from '@/types/errors'
import { problemLabels } from '@/shared/mappers/status'

export function toProblem(dto: ApiProblem): Problem {
  const problem = apiProblemSchema.parse(dto)
  const status = problem.status as keyof typeof problemLabels
  if (!(status in problemLabels)) throw new AppError('题目状态不符合领域契约', { code: 'CONTRACT_ERROR' })
  return {
    id: String(problem.id),
    type: problem.type,
    title: problem.title,
    description: problem.description || '',
    target: problem.target,
    targetIds: problem.target_ids || [],
    targetLabel: problem.target_label,
    status,
    time: problem.created_at,
    publishTime: problem.published_at || undefined,
    answerCount: problem.answer_count || 0,
    contentType: problem.content_type,
    slug: problem.slug || undefined,
    specialty: problem.specialty || undefined,
    difficulty: problem.difficulty,
    estimatedMinutes: problem.estimated_minutes,
    version: problem.version,
    parentProblemId: problem.parent_problem_id ?? undefined,
    authorId: problem.author_id ?? undefined,
    medicalReviewStatus: problem.medical_review_status,
    capabilityTags: problem.capability_tags || [],
    knowledgePointCodes: problem.knowledge_point_codes,
    opening: problem.opening
      ? {
          setting: problem.opening.setting,
          patientIntro: problem.opening.patient_intro,
          chiefComplaint: problem.opening.chief_complaint,
        }
      : undefined,
  }
}

export function problemPayload(problem: Problem) {
  return {
    type: problem.type,
    title: problem.title,
    description: problem.description,
    target: problem.target,
    target_label: problem.targetLabel || problem.className || '全体学生',
    target_ids: problem.target === 'all' ? [] : problem.targetIds || [],
    status: problem.status,
  }
}
