import { getCurrentInstance, inject, nextTick, onMounted, onUnmounted, watch, type InjectionKey, type Ref } from 'vue'
import { onLoad, onShow } from '@dcloudio/uni-app'
import type { TeacherInsightsPanel, TeacherSessionId, TeacherWorkspace } from '@/platform/navigation/teacher'

export type InsightsSelection = { classId?: number; sessionId?: TeacherSessionId; dateFrom?: string; dateTo?: string }
export interface TeacherScreenContext {
  active: Ref<boolean>
  show: Ref<number>
  query: Record<string, string | undefined>
  panel?: TeacherInsightsPanel
  insights: Ref<InsightsSelection | undefined>
  position: Readonly<Ref<number>>
  selectPanel: (panel: TeacherInsightsPanel) => void
  block: (blocked: boolean) => void
  ready: () => void
}
export const teacherScreenKey: InjectionKey<TeacherScreenContext> = Symbol('teacher-screen')
export const teacherNavigationKey: InjectionKey<(workspace: TeacherWorkspace) => void> = Symbol('teacher-navigation')
export const useTeacherScreenContext = () => inject(teacherScreenKey, undefined)
export function useTeacherScreenNextTick() {
  const instance = getCurrentInstance()
  return () =>
    new Promise<void>((resolve) => {
      if (instance?.proxy) instance.proxy.$nextTick(resolve)
      else void nextTick(resolve)
    })
}
export function useTeacherScreenLoad(callback: (query?: Record<string, string | undefined>) => void) {
  const context = useTeacherScreenContext()
  if (context) onMounted(() => callback(context.query))
  else onLoad(callback)
}
export function useTeacherScreenShow(callback: () => unknown) {
  const context = useTeacherScreenContext()
  if (!context) {
    onShow(callback)
    return
  }
  let pending = false
  let disposed = false
  onUnmounted(() => {
    disposed = true
  })
  async function refresh() {
    if (pending) return
    pending = true
    try {
      await callback()
    } finally {
      pending = false
      if (!disposed) context?.ready()
    }
  }
  onMounted(refresh)
  watch(context.show, () => {
    if (context.active.value) void refresh()
  })
}
