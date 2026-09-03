import { describe, expect, it, vi } from 'vitest'
import { logout, requireRole, saveSession } from '@/features/identity/public'
import { saveApiToken } from '@/platform/http/apiClient'

describe('auth lifecycle', () => {
  it('guards role mismatches and accepts matching sessions', () => {
    expect(requireRole('teacher')).toBe(false)
    saveSession({
      openid: 'teacher',
      role: 'teacher',
      nickName: '教师',
      avatarUrl: '',
      createdAt: new Date(0).toISOString(),
    })
    expect(requireRole('teacher')).toBe(true)
  })

  it('clears local and remote credentials on logout', () => {
    saveSession({
      openid: 'student-1',
      role: 'student',
      nickName: '学生',
      avatarUrl: '',
      createdAt: new Date(0).toISOString(),
    })
    saveApiToken('token')

    logout()

    expect(uni.removeStorageSync).toHaveBeenCalledWith('userInfo')
    expect(uni.removeStorageSync).toHaveBeenCalledWith('apiAccessToken')
    expect(vi.mocked(uni.reLaunch)).toHaveBeenCalledWith({ url: '/pages/login/login' })
  })
})
