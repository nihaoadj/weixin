import { z } from 'zod'
import { storage, storageKeys } from '@/data/storage'

export function getStartupLogs(): number[] {
  return storage.read(storageKeys.logs, z.array(z.number().finite()), [])
}
