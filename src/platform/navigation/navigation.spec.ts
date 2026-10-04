import { beforeEach, describe, expect, it, vi } from 'vitest'
import pagesConfig from '../../pages.json'
import {
  backOrHome,
  backOrRoute,
  goDetail,
  goPrimary,
  goReplace,
  handleBackPress,
  relaunchTo,
  roleHome,
  ROUTES,
  withQuery,
} from '@/platform/navigation'

describe('navigation semantics', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(getCurrentPages).mockReturnValue([])
    vi.mocked(uni.navigateTo).mockImplementation((options) => {
      options?.complete?.({ errMsg: 'navigateTo:ok' })
    })
    vi.mocked(uni.navigateBack).mockImplementation((options) => {
      options?.complete?.({ errMsg: 'navigateBack:ok' })
    })
    vi.mocked(uni.redirectTo).mockImplementation((options) => {
      options?.complete?.({ errMsg: 'redirectTo:ok' })
    })
    vi.mocked(uni.reLaunch).mockImplementation((options) => {
      options?.complete?.({ errMsg: 'reLaunch:ok' })
    })
  })

  it('maps each session role to one canonical home', () => {
    expect(roleHome('student')).toBe(ROUTES.studentPbl)
    expect(roleHome('teacher')).toBe(ROUTES.teacherPbl)
    expect(roleHome(null)).toBe(ROUTES.login)
  })

  it('keeps active routes and explicit compatibility pages exactly aligned with pages.json paths', () => {
    const compatibilityPages = [
      '/pages/teacher/pbl-progress/pbl-progress',
      '/pages/teacher/learning/result',
      '/pages/teacher/list/list',
      '/pages/teacher/analytics/index',
      '/pages/teacher/analytics/student-detail',
      '/pages/teacher/medical-review/review-list',
      '/pages/teacher/medical-review/review-detail',
      '/pages/teacher/classes/classes',
      '/pages/teacher/knowledge-cards/knowledge-cards',
    ]
    const declared = [...Object.values(ROUTES), ...compatibilityPages].sort()
    const configured = pagesConfig.pages.map((page) => `/${page.path}`).sort()
    expect(declared).toEqual(configured)
  })

  it('encodes detail parameters and omits empty values', () => {
    expect(withQuery('/detail', { id: '病例 1/2', empty: '', page: 2 })).toBe(
      '/detail?id=%E7%97%85%E4%BE%8B%201%2F2&page=2',
    )
    goDetail('/detail', { id: 'a&b' })
    expect(uni.navigateTo).toHaveBeenCalledWith(expect.objectContaining({ url: '/detail?id=a%26b' }))
  })

  it('starts immediately and merges repeated taps only while the same navigation is pending', () => {
    vi.mocked(uni.navigateTo).mockImplementation(() => {})
    goDetail('/motion-detail', { id: 1 })
    goDetail('/motion-detail', { id: 1 })
    expect(uni.navigateTo).toHaveBeenCalledTimes(1)
    const options = vi.mocked(uni.navigateTo).mock.calls[0][0]!
    options.complete?.({ errMsg: 'navigateTo:ok' })
    goDetail('/motion-detail', { id: 1 })
    expect(uni.navigateTo).toHaveBeenCalledTimes(2)
    options.complete?.({ errMsg: 'navigateTo:ok' })
  })

  it('allows a failed navigation to be retried and does not expose the target in a toast', () => {
    vi.mocked(uni.navigateTo).mockImplementation((options) => options?.fail?.({ errMsg: 'navigateTo:fail' }))
    goDetail('/unavailable-detail')
    goDetail('/unavailable-detail')
    expect(uni.navigateTo).toHaveBeenCalledTimes(2)
    expect(uni.showToast).toHaveBeenCalledWith({ title: '页面未能打开，请重试', icon: 'none' })
  })

  it('replaces the current page with encoded params for chained flows', () => {
    goReplace(ROUTES.studentCaseReport, { attemptId: 42 })
    expect(uni.redirectTo).toHaveBeenCalledWith(
      expect.objectContaining({ url: '/pages/student/case-report/case-report?attemptId=42' }),
    )

    goReplace(ROUTES.studentCaseTraining)
    expect(uni.redirectTo).toHaveBeenCalledWith(
      expect.objectContaining({ url: '/pages/student/case-training/case-training' }),
    )
  })

  it('merges repeated replacement and back transitions while native navigation is pending', () => {
    vi.mocked(uni.redirectTo).mockImplementation(() => {})
    goReplace(ROUTES.studentCaseReport, { attemptId: 42 })
    goReplace(ROUTES.studentCaseReport, { attemptId: 42 })
    expect(uni.redirectTo).toHaveBeenCalledTimes(1)
    vi.mocked(uni.redirectTo).mock.calls[0][0]?.complete?.({ errMsg: 'redirectTo:ok' })

    vi.mocked(getCurrentPages).mockReturnValue([{}, {}] as never)
    vi.mocked(uni.navigateBack).mockImplementation(() => {})
    backOrRoute(ROUTES.studentCases)
    backOrRoute(ROUTES.studentCases)
    expect(uni.navigateBack).toHaveBeenCalledTimes(1)
    vi.mocked(uni.navigateBack).mock.calls[0][0]?.complete?.({ errMsg: 'navigateBack:ok' })
  })

  it('relaunches with encoded params for tab switching', () => {
    relaunchTo(ROUTES.teacherWorkspace, { tab: 'problems' })
    expect(uni.reLaunch).toHaveBeenCalledWith(
      expect.objectContaining({ url: '/pages/teacher/index/index?tab=problems' }),
    )
  })

  it('does not redirect when the selected primary page is already active', () => {
    vi.mocked(getCurrentPages).mockReturnValue([{ route: 'pages/student/pbl/pbl' }] as never)
    goPrimary(ROUTES.studentPbl)
    expect(uni.redirectTo).not.toHaveBeenCalled()
    expect(uni.reLaunch).not.toHaveBeenCalled()
  })

  it('treats primary navigation as an atomic tab switch', () => {
    vi.mocked(getCurrentPages).mockReturnValue([{ route: 'pages/student/chat/chat' }] as never)
    goPrimary(ROUTES.studentLearning)
    expect(uni.reLaunch).toHaveBeenCalledWith(expect.objectContaining({ url: ROUTES.studentLearning }))
    expect(uni.redirectTo).not.toHaveBeenCalled()
  })

  it('returns through the stack and falls back to the role home', () => {
    vi.mocked(getCurrentPages).mockReturnValue([{}, {}] as never)
    backOrHome('teacher')
    expect(uni.navigateBack).toHaveBeenCalledWith(expect.objectContaining({ delta: 1 }))

    vi.mocked(getCurrentPages).mockReturnValue([])
    backOrHome('student')
    expect(uni.reLaunch).toHaveBeenCalledWith(expect.objectContaining({ url: ROUTES.studentPbl }))
  })

  it('falls back to the page-specific entry when history is missing or navigateBack fails', () => {
    backOrRoute(ROUTES.studentCases)
    expect(uni.reLaunch).toHaveBeenCalledWith(expect.objectContaining({ url: ROUTES.studentCases }))

    vi.clearAllMocks()
    vi.mocked(getCurrentPages).mockReturnValue([{}, {}] as never)
    vi.mocked(uni.navigateBack).mockImplementation((options) => {
      options?.fail?.({ errMsg: 'navigateBack:fail' })
    })
    backOrRoute(ROUTES.teacherWorkspace, { tab: 'problems' })
    expect(uni.reLaunch).toHaveBeenCalledWith(
      expect.objectContaining({ url: `${ROUTES.teacherWorkspace}?tab=problems` }),
    )
  })

  it('intercepts native back only at the user-initiated boundary', () => {
    expect(handleBackPress('navigateBack', ROUTES.studentCases)).toBe(false)
    expect(uni.navigateBack).not.toHaveBeenCalled()
    expect(uni.reLaunch).not.toHaveBeenCalled()

    vi.mocked(getCurrentPages).mockReturnValue([])
    expect(handleBackPress('backbutton', ROUTES.studentCases)).toBe(true)
    expect(uni.reLaunch).toHaveBeenCalledWith(expect.objectContaining({ url: ROUTES.studentCases }))
  })

  it('normalizes an invalid back delta instead of creating an unreachable jump', () => {
    vi.mocked(getCurrentPages).mockReturnValue([{}, {}] as never)
    backOrRoute(ROUTES.studentLearning, {}, 0)
    expect(uni.navigateBack).toHaveBeenCalledWith(expect.objectContaining({ delta: 1 }))
  })
})
