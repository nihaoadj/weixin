import { z } from 'zod'
import { reportSchema, storage, storageKeys } from '@/platform/storage/storage'
import { getSessionContext } from '@/platform/session/context'
import type { Report } from '@/types/domain'

function getAllReports(): Report[] {
  return storage.read(storageKeys.reports, z.array(reportSchema), [])
}

/** Seeded legacy reports are retained for student history and never mutated. */
export function getReports(): Report[] {
  const session = getSessionContext()
  if (!session || session.role !== 'student') return []
  return getAllReports().filter((report) => report.studentId === session.openid)
}
