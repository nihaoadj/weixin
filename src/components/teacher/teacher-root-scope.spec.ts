import { flushPromises, mount } from '@vue/test-utils'
import { defineComponent } from 'vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import TeacherPblRoot from '@/features/pbl/presentation/TeacherPblScreen.vue'
import {
  readTeacherClassPreference,
  saveTeacherClassPreference,
  readTeacherPblPreference,
  saveTeacherPblPreference,
} from '@/platform/navigation/teacherPreferences'
import { useTeacherRootScope } from './useTeacherRootScope'
import type { TeacherWorkspace } from '@/platform/navigation/teacher'

const lifecycle = vi.hoisted(() => ({
  loads: [] as Array<(query?: Record<string, string>) => void>,
  shows: [] as Array<() => unknown>,
}))
const auth = vi.hoisted(() => ({
  session: { role: 'teacher', openid: 'teacher-a' },
}))
const api = vi.hoisted(() => ({
  getTeacherClasses: vi.fn(),
  requireRole: vi.fn(),
  refreshWorkspace: vi.fn(),
  pblWorkspaceMounts: 0,
}))

vi.mock('@dcloudio/uni-app', () => ({
  onLoad: (hook: (query?: Record<string, string>) => void) => lifecycle.loads.push(hook),
  onShow: (hook: () => unknown) => lifecycle.shows.push(hook),
}))
vi.mock('@/features/classroom/public', () => ({ getTeacherClasses: api.getTeacherClasses }))
vi.mock('@/features/identity/public', () => ({
  getSession: () => auth.session,
  requireRole: api.requireRole,
}))
vi.mock('@/features/pbl/presentation/TeacherPblClassrooms.vue', () => ({
  default: {
    name: 'TeacherPblClassroomsProbe',
    setup(_props: unknown, { expose }: { expose: (value: unknown) => void }) {
      api.pblWorkspaceMounts += 1
      expose({ refresh: api.refreshWorkspace })
      return () => null
    },
  },
}))

const classes = [
  { id: 1, name: '炎症班' },
  { id: 2, name: '肿瘤班' },
  { id: 3, name: '循环班' },
]

function mountScope(workspace: TeacherWorkspace) {
  let scope!: ReturnType<typeof useTeacherRootScope>
  const wrapper = mount(
    defineComponent({
      setup() {
        scope = useTeacherRootScope(workspace)
        return () => null
      },
    }),
  )
  return { scope, wrapper }
}

function mountPblRoot() {
  return mount(TeacherPblRoot, {
    global: {
      stubs: {
        TeacherPageFrame: { template: '<main><slot /></main>' },
        MedState: {
          props: ['title', 'description'],
          template: '<section class="scope-error"><span>{{ title }}</span><span>{{ description }}</span></section>',
        },
      },
    },
  })
}

function currentShow() {
  return lifecycle.shows[lifecycle.shows.length - 1]
}

describe('teacher root class scope', () => {
  it('isolates saved PBL queue filters from other teachers and class preferences', () => {
    saveTeacherPblPreference('teacher-a', {
      section: 'diagnostics',
      reviewKind: 'generation_failed',
      sessionId: 'demo-pbl-1',
    })
    saveTeacherPblPreference('teacher-b', { section: 'classrooms' })
    saveTeacherClassPreference('teacher-a', 'insights', 3)
    expect(readTeacherPblPreference('teacher-a')).toEqual({
      section: 'diagnostics',
      reviewKind: 'generation_failed',
      sessionId: 'demo-pbl-1',
    })
    expect(readTeacherPblPreference('teacher-b')).toEqual({ section: 'classrooms' })
    expect(readTeacherClassPreference('teacher-a', 'insights')).toBe(3)
  })
  beforeEach(() => {
    vi.clearAllMocks()
    lifecycle.loads.length = 0
    lifecycle.shows.length = 0
    api.pblWorkspaceMounts = 0
    auth.session = { role: 'teacher', openid: 'teacher-a' }
    api.getTeacherClasses.mockResolvedValue(classes)
  })

  it('keeps PBL and insights class preferences independent and isolated by teacher identity', async () => {
    saveTeacherClassPreference('teacher-a', 'pbl', 2)
    saveTeacherClassPreference('teacher-a', 'insights', 1)
    saveTeacherClassPreference('teacher-b', 'pbl', 1)
    saveTeacherClassPreference('teacher-b', 'insights', 3)

    const pbl = mountScope('pbl')
    const insights = mountScope('insights')
    await Promise.all([pbl.scope.refreshScope(), insights.scope.refreshScope()])

    expect(pbl.scope.classId.value).toBe(2)
    expect(insights.scope.classId.value).toBe(1)
    expect(pbl.scope.scopeAllowed.value).toBe(true)
    expect(insights.scope.scopeAllowed.value).toBe(true)

    pbl.scope.selectClass(3)
    expect(readTeacherClassPreference('teacher-a', 'pbl')).toBe(3)
    expect(readTeacherClassPreference('teacher-a', 'insights')).toBe(1)

    auth.session = { role: 'teacher', openid: 'teacher-b' }
    await Promise.all([pbl.scope.refreshScope(), insights.scope.refreshScope()])
    expect(pbl.scope.classId.value).toBe(1)
    expect(insights.scope.classId.value).toBe(3)

    pbl.wrapper.unmount()
    insights.wrapper.unmount()
  })

  it('does not mount or load the PBL workspace for a requested class outside teacher ownership', async () => {
    const wrapper = mountPblRoot()
    lifecycle.loads[lifecycle.loads.length - 1]?.({ classId: '99' })
    await Promise.resolve(currentShow()?.())
    await flushPromises()

    expect(api.getTeacherClasses).toHaveBeenCalledTimes(1)
    expect(wrapper.text()).toContain('该班级不在当前教师范围内')
    expect(api.pblWorkspaceMounts).toBe(0)
    expect(api.refreshWorkspace).not.toHaveBeenCalled()
  })

  it('keeps the PBL root on classrooms when an old queue preference exists', async () => {
    saveTeacherPblPreference('teacher-a', {
      section: 'diagnostics',
      reviewKind: 'needs_changes',
      sessionId: 'demo-pbl-1',
    })
    const wrapper = mountPblRoot()
    lifecycle.loads[lifecycle.loads.length - 1]?.({})
    await Promise.resolve(currentShow()?.())
    await flushPromises()
    expect(api.pblWorkspaceMounts).toBe(1)
    expect(wrapper.text()).not.toContain('测试待处理')
    expect(wrapper.findComponent({ name: 'TeacherPblClassroomsProbe' }).attributes('session-id')).toBeUndefined()
    wrapper.unmount()
  })

  it('replaces a directly opened old queue link without loading the classroom workspace', async () => {
    const wrapper = mountPblRoot()
    lifecycle.loads[lifecycle.loads.length - 1]?.({ section: 'diagnostics', classId: '1', reviewKind: 'needs_changes' })
    await Promise.resolve(currentShow()?.())
    await flushPromises()
    expect(uni.redirectTo).toHaveBeenCalledWith(
      expect.objectContaining({ url: '/pages/teacher/pbl/test-queue?classId=1&reviewKind=needs_changes' }),
    )
    expect(api.getTeacherClasses).not.toHaveBeenCalled()
    expect(api.pblWorkspaceMounts).toBe(0)
    wrapper.unmount()
  })

  it('keeps the newest class-scope response when two reads finish out of order', async () => {
    let resolveOld!: (value: typeof classes) => void
    api.getTeacherClasses
      .mockReturnValueOnce(new Promise((resolve) => (resolveOld = resolve)))
      .mockResolvedValueOnce([classes[1]])

    const { scope, wrapper } = mountScope('pbl')
    const oldRequest = scope.refreshScope()
    const newRequest = scope.refreshScope()
    await newRequest
    expect(scope.classes.value).toEqual([classes[1]])
    expect(scope.scopeAllowed.value).toBe(true)

    resolveOld([classes[0]])
    await oldRequest
    expect(scope.classes.value).toEqual([classes[1]])
    expect(scope.scopeAllowed.value).toBe(true)
    wrapper.unmount()
  })
})
