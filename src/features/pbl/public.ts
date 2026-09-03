import { getApplicationServices } from '@/bootstrap/wiring'
import type { PblRepository } from './domain/ports'
export type { PblDiagnostic, PblSession, PblSuggestion } from './domain/ports'
const pbl = (): PblRepository => getApplicationServices().pbl
export const getActivePblSessions = () => pbl().active()
export const getPblParticipation = (id: string) => pbl().participation(id)
export const sendPblMessage = (id: string, content: string) =>
  pbl().message(id, content, `${Date.now()}-${Math.random().toString(36).slice(2)}`)
export const getTeacherPblDiagnostics = () => pbl().diagnostics()
export const editPblSuggestion = (item: import('./domain/ports').PblSuggestion, reject = false) =>
  pbl().editSuggestion(item, reject)
export const adoptPblSuggestion = (id: string) => pbl().adopt(id)
