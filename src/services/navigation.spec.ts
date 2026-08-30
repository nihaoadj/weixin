import { beforeEach, describe, expect, it, vi } from 'vitest'
import { backOrHome, goDetail, goPrimary, roleHome, ROUTES, withQuery } from './navigation'

describe('navigation semantics', () => {
  beforeEach(() => {
    vi.mocked(getCurrentPages).mockReturnValue([])
  })

  it('maps each session role to one canonical home', () => {
    expect(roleHome('student')).toBe(ROUTES.studentChat)
    expect(roleHome('teacher')).toBe(ROUTES.teacherWorkspace)
    expect(roleHome(null)).toBe(ROUTES.login)
  })

  it('encodes detail parameters and omits empty values', () => {
    expect(withQuery('/detail', { id: '病例 1/2', empty: '', page: 2 })).toBe(
      '/detail?id=%E7%97%85%E4%BE%8B%201%2F2&page=2',
    )
    goDetail('/detail', { id: 'a&b' })
    expect(uni.navigateTo).toHaveBeenCalledWith({ url: '/detail?id=a%26b' })
  })

  it('does not redirect when the selected primary page is already active', () => {
    vi.mocked(getCurrentPages).mockReturnValue([{ route: 'pages/student/chat/chat' }] as never)
    goPrimary(ROUTES.studentChat)
    expect(uni.redirectTo).not.toHaveBeenCalled()
  })

  it('returns through the stack and falls back to the role home', () => {
    vi.mocked(getCurrentPages).mockReturnValue([{}, {}] as never)
    backOrHome('teacher')
    expect(uni.navigateBack).toHaveBeenCalledWith(expect.objectContaining({ delta: 1 }))

    vi.mocked(getCurrentPages).mockReturnValue([])
    backOrHome('student')
    expect(uni.reLaunch).toHaveBeenCalledWith({ url: ROUTES.studentChat })
  })
})
