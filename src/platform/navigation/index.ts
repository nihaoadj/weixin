import type { UserRole } from '@/types/domain'

/**
 * 全站路由清单：页面跳转一律引用这里的常量，
 * 禁止在页面中手写字符串路径，避免路径漂移与参数未编码问题。
 */
export const ROUTES = {
  index: '/pages/index/index',
  login: '/pages/login/login',
  logs: '/pages/logs/logs',
  // 学生端主导航
  studentChat: '/pages/student/chat/chat',
  studentCases: '/pages/student/question/question',
  studentLearning: '/pages/student/learning/index',
  studentInsights: '/pages/student/insights/index',
  studentPbl: '/pages/student/pbl/pbl',
  studentHistory: '/pages/student/history/history',
  // 学生端二级页面
  studentCaseTraining: '/pages/student/case-training/case-training',
  studentCaseReport: '/pages/student/case-report/case-report',
  studentQuestionDetail: '/pages/student/question-detail/question-detail',
  studentLearningPlan: '/pages/student/learning/plan',
  studentLearningDrill: '/pages/student/learning/drill',
  studentLearningReview: '/pages/student/learning/review',
  studentKnowledgeLoop: '/pages/student/learning/knowledge-loop',
  studentInsightDetail: '/pages/student/insights/detail',
  studentReport: '/pages/report/report',
  // 教师端
  teacherWorkspace: '/pages/teacher/index/index',
  teacherLegacyReports: '/pages/teacher/list/list',
  teacherReportDetail: '/pages/teacher/detail/detail',
  teacherProblemEdit: '/pages/teacher/problem-edit/problem-edit',
  teacherCaseEdit: '/pages/teacher/case-edit/case-edit',
  teacherProblemDetail: '/pages/teacher/problem-detail/problem-detail',
  teacherProblemStats: '/pages/teacher/problem-stats/problem-stats',
  teacherAnalytics: '/pages/teacher/analytics/index',
  teacherAnalyticsCaseDetail: '/pages/teacher/analytics/case-detail',
  teacherAnalyticsStudentDetail: '/pages/teacher/analytics/student-detail',
  teacherReviewList: '/pages/teacher/medical-review/review-list',
  teacherReviewDetail: '/pages/teacher/medical-review/review-detail',
  teacherClasses: '/pages/teacher/classes/classes',
  teacherKnowledgeCards: '/pages/teacher/knowledge-cards/knowledge-cards',
} as const

export type StudentPrimaryRoute =
  typeof ROUTES.studentChat | typeof ROUTES.studentLearning | typeof ROUTES.studentInsights | typeof ROUTES.studentPbl

type NavigationParams = Record<string, string | number | null | undefined>
type BackPressSource = 'backbutton' | 'navigateBack'

export function roleHome(role: UserRole | null | undefined): string {
  if (role === 'student') return ROUTES.studentPbl
  if (role === 'teacher') return ROUTES.teacherWorkspace
  return ROUTES.login
}

export function withQuery(path: string, params: NavigationParams): string {
  const query = Object.entries(params)
    .filter(([, value]) => value !== undefined && value !== null && value !== '')
    .map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(String(value))}`)
    .join('&')
  return query ? `${path}?${query}` : path
}

function currentRoute(): string {
  try {
    const pages = getCurrentPages()
    const current = pages[pages.length - 1]
    return current?.route ? `/${current.route}` : ''
  } catch {
    return ''
  }
}

function pageStackDepth(): number {
  try {
    return getCurrentPages().length
  } catch {
    return 0
  }
}

function navigationError(title = '页面未能打开，请重试'): void {
  uni.showToast({ title, icon: 'none' })
}

const pendingRootTargets = new Set<string>()

function relaunch(url: string): void {
  if (pendingRootTargets.has(url)) return
  pendingRootTargets.add(url)
  const release = () => pendingRootTargets.delete(url)
  const fail = () => {
    release()
    navigationError()
  }
  try {
    uni.reLaunch({ url, success: release, fail, complete: release })
  } catch {
    fail()
  }
}

/** 主导航切换：清理旧业务栈，避免 tab 间残留可返回的半截历史。 */
export function goPrimary(url: StudentPrimaryRoute): void {
  if (currentRoute() === url) return
  relaunch(url)
}

const pendingDetails = new Set<string>()

/** 进入二级页面；只合并尚未完成的同目标跳转，不人为延迟转场。 */
export function goDetail(path: string, params: NavigationParams = {}): void {
  const url = withQuery(path, params)
  if (pendingDetails.has(url)) return
  pendingDetails.add(url)
  const release = () => pendingDetails.delete(url)
  const fail = () => {
    release()
    navigationError()
  }
  try {
    // 微信沿用原生转场；animationType/Duration 仅对 App 生效，不伪装为跨端配置。
    uni.navigateTo({ url, success: release, fail, complete: release })
  } catch {
    fail()
  }
}

/** 替换当前页（流程页串联）：redirectTo + 参数编码。 */
const pendingReplacements = new Set<string>()

export function goReplace(path: string, params: NavigationParams = {}): void {
  const url = withQuery(path, params)
  if (pendingReplacements.has(url)) return
  pendingReplacements.add(url)
  const release = () => pendingReplacements.delete(url)
  const fail = () => {
    release()
    navigationError()
  }
  try {
    uni.redirectTo({ url, success: release, fail, complete: release })
  } catch {
    fail()
  }
}

export function relaunchForRole(role: UserRole | null | undefined): void {
  relaunch(roleHome(role))
}

/** 重启到指定页面：reLaunch + 参数编码（切换工作台 tab 等场景）。 */
export function relaunchTo(path: string, params: NavigationParams = {}): void {
  relaunch(withQuery(path, params))
}

let backPending = false

/**
 * 优先返回现有页面栈；直接打开、栈不足或返回失败时，重启到明确的业务入口。
 * fallbackPath 必须来自 ROUTES，调用页据自身上下文选择，而不是一律退回角色首页。
 */
export function backOrRoute(fallbackPath: string, params: NavigationParams = {}, delta = 1): void {
  const safeDelta = Number.isInteger(delta) && delta > 0 ? delta : 1
  const fallbackUrl = withQuery(fallbackPath, params)
  if (pageStackDepth() > safeDelta) {
    if (backPending) return
    backPending = true
    const release = () => {
      backPending = false
    }
    const fail = () => {
      release()
      relaunch(fallbackUrl)
    }
    try {
      uni.navigateBack({ delta: safeDelta, success: release, fail, complete: release })
    } catch {
      fail()
    }
    return
  }
  relaunch(fallbackUrl)
}

/** 原生标题栏/实体返回键的页面钩子；navigateBack 自身触发时必须放行，避免递归。 */
export function handleBackPress(
  from: BackPressSource,
  fallbackPath: string,
  params: NavigationParams = {},
  delta = 1,
): boolean {
  if (from === 'navigateBack') return false
  backOrRoute(fallbackPath, params, delta)
  return true
}

export function backOrHome(role: UserRole | null | undefined, delta = 1): void {
  backOrRoute(roleHome(role), {}, delta)
}
