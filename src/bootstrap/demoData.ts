import { z } from 'zod'
import { createDemoConversations, createDemoReports } from '@/features/qa/infrastructure/demoSeeds'
import { getProblems, saveProblems, resetProblems } from '@/features/content/infrastructure/demoProblemStore'
import { createDemoProblems } from '@/features/content/infrastructure/demoProblemSeeds'
import { conversationSchema, reportSchema, storage, storageKeys } from '@/platform/storage/storage'

export function ensureDemoData(): void {
  migratePathologyDemo()
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
    const index = reports.findIndex((report) => report.conversationId === fixture.conversationId)
    if (index < 0) {
      reports.push(fixture)
      continue
    }
    // Seed maintenance: demo fixtures stored before T29 lack the class
    // attribution; refresh only the known fixture identity, never user data.
    const stored = reports[index]
    if (stored.id === fixture.id && (!stored.classId || !stored.className)) {
      reports[index] = { ...fixture, createdAt: stored.createdAt, updatedAt: stored.updatedAt }
    }
  }
  storage.write(storageKeys.reports, reports, z.array(reportSchema))
}

// This bootstrap runs only in Demo wiring. Unknown/custom records are preserved.
function migratePathologyDemo() {
  const marker = 'demoPathologySchemaVersion'
  if (storage.readRaw(marker) === 4) return
  const oldProblems = new Set([
    '1',
    '2',
    '3',
    '4',
    '5',
    '6',
    'cap-undergraduate-showcase',
    'acute-chest-pain-undergraduate-showcase',
    'right-lower-quadrant-pain-undergraduate-showcase',
    'demo-pending-chest-pain',
    'demo-question-001',
  ])
  const oldPrefixes = ['cardio.', 'digestive.', 'endocrine.', 'hematology.', 'renal.', 'respiratory.']
  const stripCodes = (codes: unknown) =>
    Array.isArray(codes)
      ? codes.filter((code) => typeof code !== 'string' || !oldPrefixes.some((prefix) => code.startsWith(prefix)))
      : codes
  const removedAttempts = new Set<string>()
  const records = z.array(z.record(z.string(), z.unknown()))
  const keys = storage
    .keys()
    .filter((key) =>
      [
        storageKeys.caseAttempts,
        storageKeys.conversations,
        storageKeys.reports,
        storageKeys.questionThreads,
        storageKeys.guidedDrafts,
      ].some((base) => key === base || key.startsWith(`${base}:`)),
    )
  for (const key of keys) {
    const original = storage.readRaw(key),
      parsed = records.safeParse(original)
    if (!parsed.success) continue
    const updated = parsed.data
      .filter((item) => {
        const isPbl =
          item.sourceType === 'pbl_suggestion' || item.pblSource || String(item.id || '').startsWith('demo-pbl-')
        if (isPbl) return true
        const oldAttempt = key.startsWith(storageKeys.caseAttempts) && oldProblems.has(String(item.problemId))
        if (oldAttempt) removedAttempts.add(String(item.id))
        return (
          !oldAttempt &&
          !(item.conversationId === 'demo-conversation-001') &&
          !(key.startsWith(storageKeys.questionThreads) && oldProblems.has(String(item.questionId)))
        )
      })
      .map((item) => ({
        ...item,
        ...(item.topicCodes ? { topicCodes: stripCodes(item.topicCodes) } : {}),
        ...(item.reviewTopicCodes ? { reviewTopicCodes: stripCodes(item.reviewTopicCodes) } : {}),
      }))
    storage.write(`${key}:pre-pathology-v4`, original, z.unknown())
    storage.write(key, updated, records)
  }
  for (const key of storage
    .keys()
    .filter((key) => key === storageKeys.caseAssessments || key.startsWith(`${storageKeys.caseAssessments}:`))) {
    const parsed = records.safeParse(storage.readRaw(key))
    if (parsed.success)
      storage.write(
        key,
        parsed.data.filter((item) => !removedAttempts.has(String(item.attemptId))),
        records,
      )
  }
  const existing = getProblems()
    .filter((item) => !oldProblems.has(item.id))
    .map((item) => ({ ...item, knowledgePointCodes: stripCodes(item.knowledgePointCodes) as string[] | undefined }))
  saveProblems([...existing, ...createDemoProblems().filter((seed) => !existing.some((item) => item.id === seed.id))])
  storage.write(marker, 4, z.number())
}
