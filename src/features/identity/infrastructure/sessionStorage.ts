import { z, type ZodType } from 'zod'
import {
  conversationSchema,
  reportSchema,
  sessionSchema,
  STORAGE_SCHEMA_VERSION,
  storage,
  storageKeys,
  questionThreadSchema,
} from '@/platform/storage/storage'
import type { SessionStoragePort } from '@/features/identity/domain/ports'
import type { Report as LegacyReport } from '@/types/domain'
import type { SessionUser } from '@/types/records'

type ReportDraftRecord = LegacyReport

function readArray<T>(key: string, itemSchema: ZodType<T>): T[] {
  return storage.read(key, z.array(itemSchema), [])
}

function writeArray<T>(key: string, value: T[], itemSchema: ZodType<T>): void {
  storage.write(key, value, z.array(itemSchema))
}

function userScopedKey(baseKey: string, userId: string): string {
  return storage.scopedKey(baseKey, userId)
}

function migrateLegacyStudentData(user: SessionUser): void {
  const currentVersion = Number(storage.readRaw(storageKeys.schemaVersion) || 0)
  if (currentVersion >= STORAGE_SCHEMA_VERSION) return

  const privateCollections = [
    [storageKeys.conversations, conversationSchema],
    [storageKeys.answeredQuestions, z.string()],
    [storageKeys.questionThreads, questionThreadSchema],
  ] as const
  for (const [legacyKey, itemSchema] of privateCollections) {
    const legacyValue = storage.readRaw(legacyKey)
    const scopedKey = userScopedKey(legacyKey, user.openid)
    const parsed = z.array(itemSchema).safeParse(legacyValue)
    if (parsed.success) {
      const existing = z.array(itemSchema).safeParse(storage.readRaw(scopedKey))
      if (!existing.success || existing.data.length === 0) {
        storage.write(scopedKey, parsed.data, z.array(itemSchema))
        storage.remove(legacyKey)
      }
    }
  }

  const rawReports = z.array(z.record(z.string(), z.unknown())).safeParse(storage.readRaw(storageKeys.reports))
  if (rawReports.success) {
    const scopedConversationKey = userScopedKey(storageKeys.conversations, user.openid)
    const ownConversationIds = new Set(
      readArray(scopedConversationKey, conversationSchema).map((item) => item.conversationId),
    )
    const migrated: ReportDraftRecord[] = []
    for (const report of rawReports.data) {
      const studentId =
        report.studentId ||
        (typeof report.conversationId === 'string' && ownConversationIds.has(report.conversationId)
          ? user.openid
          : undefined)
      const parsed = reportSchema.safeParse({
        ...report,
        studentId,
        studentName: report.studentName || user.nickName,
        status: report.status || '草稿',
      })
      if (parsed.success) migrated.push(parsed.data)
    }
    if (migrated.length > 0) writeArray(storageKeys.reports, migrated, reportSchema)
  }
  storage.write(storageKeys.schemaVersion, STORAGE_SCHEMA_VERSION, z.number().int())
}

export function createSessionStorage(mode: 'demo' | 'api'): SessionStoragePort {
  return {
    readSession(): SessionUser | null {
      return storage.read<SessionUser | null>(storageKeys.user, sessionSchema.nullable(), null)
    },
    writeSession(user: SessionUser): void {
      if (mode === 'demo' && user.role === 'student') migrateLegacyStudentData(user)
      storage.write(storageKeys.user, user, sessionSchema)
      storage.write(storageKeys.role, user.role, z.enum(['student', 'teacher']))
      storage.write(storageKeys.openid, user.openid, z.string().min(1))
    },
    clearSession(): void {
      storage.remove(storageKeys.user)
      storage.remove(storageKeys.role)
      storage.remove(storageKeys.openid)
      storage.remove(storageKeys.apiToken)
    },
  }
}
