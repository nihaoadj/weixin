import type { TeacherWorkspace } from './teacher'

export type TeacherSwipeDirection = 'left' | 'right'
let entry: { workspace: TeacherWorkspace; direction: TeacherSwipeDirection; time: number } | undefined

/** A gesture handoff only, never persisted as a page preference. */
export function prepareTeacherSwipeEntry(workspace: TeacherWorkspace, direction: TeacherSwipeDirection) {
  entry = { workspace, direction, time: Date.now() }
}
export function takeTeacherSwipeEntry(workspace: TeacherWorkspace): TeacherSwipeDirection | undefined {
  const pending = entry
  entry = undefined
  if (pending?.workspace === workspace && Date.now() - pending.time <= 1200) return pending.direction
}
export function clearTeacherSwipeEntry() {
  entry = undefined
}
