import type { UserRole } from '@/types/domain'

export const ROUTES = {
  index: '/pages/index/index',
  login: '/pages/login/login',
  studentChat: '/pages/student/chat/chat',
  studentCases: '/pages/student/question/question',
  studentLearning: '/pages/student/learning/index',
  studentHistory: '/pages/student/history/history',
  teacherWorkspace: '/pages/teacher/index/index',
  teacherLegacyReports: '/pages/teacher/list/list',
} as const

export type StudentPrimaryRoute =
  typeof ROUTES.studentChat | typeof ROUTES.studentCases | typeof ROUTES.studentLearning | typeof ROUTES.studentHistory

export function roleHome(role: UserRole | null | undefined): string {
  if (role === 'student') return ROUTES.studentChat
  if (role === 'teacher') return ROUTES.teacherWorkspace
  return ROUTES.login
}

export function withQuery(path: string, params: Record<string, string | number | null | undefined>): string {
  const query = Object.entries(params)
    .filter(([, value]) => value !== undefined && value !== null && value !== '')
    .map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(String(value))}`)
    .join('&')
  return query ? `${path}?${query}` : path
}

function currentRoute(): string {
  const pages = getCurrentPages()
  const current = pages[pages.length - 1]
  return current?.route ? `/${current.route}` : ''
}

export function goPrimary(url: StudentPrimaryRoute): void {
  if (currentRoute() === url) return
  uni.redirectTo({ url })
}

export function goDetail(path: string, params: Record<string, string | number | null | undefined> = {}): void {
  uni.navigateTo({ url: withQuery(path, params) })
}

export function relaunchForRole(role: UserRole | null | undefined): void {
  uni.reLaunch({ url: roleHome(role) })
}

export function backOrHome(role: UserRole | null | undefined, delta = 1): void {
  if (getCurrentPages().length > delta) {
    uni.navigateBack({ delta, fail: () => relaunchForRole(role) })
    return
  }
  relaunchForRole(role)
}
