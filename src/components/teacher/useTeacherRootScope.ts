import { ref } from 'vue'
import { getTeacherClasses } from '@/features/classroom/public'
import { getSession, requireRole } from '@/features/identity/public'
import { readTeacherClassPreference, saveTeacherClassPreference } from '@/platform/navigation/teacherPreferences'
import type { TeacherWorkspace } from '@/platform/navigation/teacher'

/** Each root owns its instance; only a user's lightweight selection is persisted. */
export function useTeacherRootScope(workspace: TeacherWorkspace) {
  const classes = ref<Array<{ id: number; name: string; status?: 'active' | 'archived' }>>([])
  const classId = ref<number>()
  const loading = ref(false)
  const error = ref('')
  const accessDenied = ref(false)
  const identityGeneration = ref(0)
  const scopeAllowed = ref(false)
  let requestedClassId: number | undefined
  let identity: string | undefined
  let request = 0

  function setInitialClass(value?: number) {
    requestedClassId = value
  }
  function selectClass(value?: number) {
    if (value !== undefined && !classes.value.some((item) => item.id === value)) return
    classId.value = value
    requestedClassId = undefined
    if (identity) saveTeacherClassPreference(identity, workspace, value)
  }
  async function refreshScope() {
    const token = ++request
    const user = getSession()
    if (!user || user.role !== 'teacher') {
      identity = undefined
      identityGeneration.value += 1
      classes.value = []
      classId.value = undefined
      scopeAllowed.value = false
      accessDenied.value = true
      loading.value = false
      requireRole('teacher')
      return false
    }
    if (identity !== user.openid) {
      identity = user.openid
      identityGeneration.value += 1
      classes.value = []
      classId.value = undefined
      scopeAllowed.value = false
      classId.value = readTeacherClassPreference(identity, workspace)
    }
    accessDenied.value = false
    loading.value = true
    error.value = ''
    const currentIdentity = identity
    const current = () =>
      token === request && getSession()?.openid === currentIdentity && getSession()?.role === 'teacher'
    try {
      const result = await getTeacherClasses()
      if (!current()) return false
      classes.value = result.map((item) => {
        const status: 'active' | 'archived' | undefined =
          item.status === 'active' || item.status === 'archived' ? item.status : undefined
        return { id: item.id, name: item.name, ...(status ? { status } : {}) }
      })
      if (requestedClassId !== undefined) {
        if (!classes.value.some((item) => item.id === requestedClassId)) {
          error.value = '该班级不在当前教师范围内'
          scopeAllowed.value = false
          return false
        }
        selectClass(requestedClassId)
      } else if (classId.value !== undefined && !classes.value.some((item) => item.id === classId.value)) {
        selectClass(undefined)
      }
      scopeAllowed.value = true
      return true
    } catch (reason) {
      if (!current()) return false
      error.value = reason instanceof Error ? reason.message : '班级范围读取失败'
      scopeAllowed.value = false
      return false
    } finally {
      if (current()) loading.value = false
    }
  }
  return {
    classes,
    classId,
    loading,
    error,
    accessDenied,
    identityGeneration,
    scopeAllowed,
    setInitialClass,
    selectClass,
    refreshScope,
  }
}
