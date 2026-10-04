import { beforeEach, describe, expect, it, vi } from 'vitest'
import { readTeacherContentPreference, saveTeacherContentPreference } from './teacherPreferences'

const state = vi.hoisted(() => ({ values: new Map<string, unknown>() }))
vi.mock('@/platform/storage/storage', () => ({
  storage: {
    readRaw: (key: string) => state.values.get(key),
    write: (key: string, value: unknown) => state.values.set(key, value),
  },
}))
beforeEach(() => state.values.clear())

describe('T63 teacher content preferences', () => {
  it.each(['questions', 'knowledge-cards'])(
    'normalizes legacy %s without carrying old search or lifecycle',
    (resource) => {
      state.values.set('teacher:t53:teacher-1:content:scope', { resource, keyword: '旧问题', status: 'pending' })
      expect(readTeacherContentPreference('teacher-1')).toEqual({ resource: 'cases' })
    },
  )
  it('preserves personal bank filters and isolates each teacher', () => {
    saveTeacherContentPreference('teacher-1', { resource: 'question-bank', keyword: '炎症', status: 'archived' })
    expect(readTeacherContentPreference('teacher-1')).toEqual({
      resource: 'question-bank',
      keyword: '炎症',
    })
    expect(readTeacherContentPreference('teacher-2')).toBeUndefined()
  })
  it('ignores malformed stored data', () => {
    state.values.set('teacher:t53:teacher-1:content:scope', { resource: 'unexpected' })
    expect(readTeacherContentPreference('teacher-1')).toBeUndefined()
  })
})
