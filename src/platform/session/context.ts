import type { SessionUser } from '@/types/records'

export type SessionReader = () => SessionUser | null

let reader: SessionReader = () => null

export function configureSessionReader(nextReader: SessionReader): void {
  reader = nextReader
}

export function getSessionContext(): SessionUser | null {
  return reader()
}
