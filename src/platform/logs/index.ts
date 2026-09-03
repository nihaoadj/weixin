import { z } from 'zod'
import { storage, storageKeys } from '@/platform/storage/storage'

const startupLogsSchema = z.array(z.number().finite())

export function getStartupLogs(): number[] {
  return storage.read(storageKeys.logs, startupLogsSchema, [])
}

export function recordStartupLog(now = Date.now()): void {
  const logs = getStartupLogs()
  storage.write(storageKeys.logs, [now, ...logs].slice(0, 50), startupLogsSchema)
}
