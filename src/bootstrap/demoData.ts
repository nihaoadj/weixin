import { z } from 'zod'
import { createDemoConversations, createDemoReports } from '@/features/qa/infrastructure/demoSeeds'
import { resetProblems } from '@/features/content/infrastructure/demoProblemStore'
import { conversationSchema, reportSchema, storage, storageKeys } from '@/platform/storage/storage'

export function ensureDemoData(): void {
  if (!Array.isArray(storage.readRaw(storageKeys.problems))) resetProblems()

  const previous = storage.read(`${storageKeys.conversations}:demo_student`, z.array(conversationSchema), [])
  const fixtures = createDemoConversations()
  const missing = fixtures.filter(
    (fixture) => !previous.some((conversation) => conversation.conversationId === fixture.conversationId),
  )
  if (missing.length) {
    storage.write(
      storage.scopedKey(storageKeys.conversations, 'demo_student'),
      [...missing, ...previous].slice(0, 10),
      z.array(conversationSchema),
    )
  }

  const reports = storage.read(storageKeys.reports, z.array(reportSchema), [])
  for (const fixture of createDemoReports()) {
    if (!reports.some((report) => report.conversationId === fixture.conversationId)) reports.push(fixture)
  }
  storage.write(storageKeys.reports, reports, z.array(reportSchema))
}
