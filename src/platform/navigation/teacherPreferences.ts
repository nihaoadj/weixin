import { z } from 'zod'
import { storage } from '@/platform/storage/storage'
import type {
  TeacherContentResource,
  TeacherContentStatus,
  TeacherWorkspace,
  TeacherPblSection,
  TeacherReviewKind,
} from './teacher'

const scopePreference = z.object({ classId: z.number().int().positive().optional() }).strict()
const key = (identity: string, workspace: TeacherWorkspace) =>
  `teacher:t53:${encodeURIComponent(identity)}:${workspace}:scope`

export function readTeacherClassPreference(identity: string, workspace: TeacherWorkspace): number | undefined {
  const parsed = scopePreference.safeParse(storage.readRaw(key(identity, workspace)))
  return parsed.success ? parsed.data.classId : undefined
}

export function saveTeacherClassPreference(identity: string, workspace: TeacherWorkspace, classId?: number): void {
  storage.write(key(identity, workspace), { classId }, scopePreference)
}

export interface TeacherContentPreference {
  resource?: TeacherContentResource
  keyword?: string
  status?: TeacherContentStatus
}
const contentPreference = z
  .object({
    resource: z.enum(['cases', 'questions', 'knowledge-cards', 'question-bank']).optional(),
    keyword: z.string().max(100).optional(),
    status: z
      .enum(['all', 'draft', 'pending', 'published', 'approved', 'rejected', 'disabled', 'active', 'archived'])
      .optional(),
  })
  .strict()

export function readTeacherContentPreference(identity: string): TeacherContentPreference | undefined {
  const parsed = contentPreference.safeParse(storage.readRaw(key(identity, 'content')))
  if (!parsed.success) return undefined
  if (parsed.data.resource === 'questions' || parsed.data.resource === 'knowledge-cards') {
    return { resource: 'cases' }
  }
  const { resource, keyword } = parsed.data
  return { ...(resource ? { resource } : {}), ...(keyword ? { keyword } : {}) }
}

export function saveTeacherContentPreference(identity: string, value: TeacherContentPreference): void {
  const { resource, keyword } = value
  storage.write(key(identity, 'content'), { resource, keyword }, contentPreference)
}

export interface TeacherPblPreference {
  section?: TeacherPblSection
  reviewKind?: TeacherReviewKind
  sessionId?: number | string
}
const pblPreference = z
  .object({
    section: z.enum(['classrooms', 'diagnostics']).optional(),
    reviewKind: z.enum(['pending_review', 'needs_changes', 'generation_failed']).optional(),
    sessionId: z.union([z.number().int().positive(), z.string().regex(/^demo-(?:pbl-[1-9]\d*|[1-9]\d*)$/)]).optional(),
  })
  .strict()
export function readTeacherPblPreference(identity: string): TeacherPblPreference | undefined {
  const parsed = pblPreference.safeParse(storage.readRaw(`${key(identity, 'pbl')}:filters`))
  return parsed.success ? parsed.data : undefined
}
export function saveTeacherPblPreference(identity: string, value: TeacherPblPreference): void {
  storage.write(`${key(identity, 'pbl')}:filters`, value, pblPreference)
}

const insightsPreference = z
  .object({
    panel: z.enum(['overview', 'progress', 'knowledge', 'students']).optional(),
    sessionId: pblPreference.shape.sessionId,
    dateFrom: z
      .string()
      .regex(/^\d{4}-\d{2}-\d{2}$/)
      .optional(),
    dateTo: z
      .string()
      .regex(/^\d{4}-\d{2}-\d{2}$/)
      .optional(),
  })
  .strict()
export type TeacherInsightsPreference = z.infer<typeof insightsPreference>
export function readTeacherInsightsPreference(identity: string): TeacherInsightsPreference | undefined {
  const parsed = insightsPreference.safeParse(storage.readRaw(`${key(identity, 'insights')}:filters`))
  return parsed.success ? parsed.data : undefined
}
export function saveTeacherInsightsPreference(identity: string, value: TeacherInsightsPreference): void {
  storage.write(`${key(identity, 'insights')}:filters`, value, insightsPreference)
}
