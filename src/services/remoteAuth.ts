import { apiRequest, clearApiToken, isRemoteApiEnabled, saveApiToken } from '@/services/apiClient'
import { apiLoginResponseSchema, type ValidatedLoginResponse } from '@/data/contracts/auth'
import type { SessionUser, UserRole } from '@/types/domain'

type LoginUser = NonNullable<ValidatedLoginResponse['user']>

export function isWechatMiniProgram(): boolean {
  // #ifdef MP-WEIXIN
  return true
  // #endif
  return false
}

function toSessionUser(user: LoginUser): SessionUser {
  return {
    openid: `api-user-${user.id}`,
    role: user.role,
    nickName: user.nickname,
    avatarUrl: user.avatar_url || '',
    classIds: user.class_ids,
    permissions: user.permissions,
    createdAt: user.created_at,
  }
}

export async function syncDemoLoginWithBackend(params: {
  role: UserRole
  openid: string
  nickName: string
  avatarUrl: string
}): Promise<string[]> {
  if (!isRemoteApiEnabled()) return []
  clearApiToken()
  const response = await apiRequest({
    path: '/auth/demo-login',
    method: 'POST',
    auth: false,
    schema: apiLoginResponseSchema,
    body: {
      role: params.role,
      external_id: params.openid,
      nickname: params.nickName,
      avatar_url: params.avatarUrl,
      class_ids: params.role === 'student' ? ['demo_class_1'] : [],
    },
  })
  saveApiToken(response.access_token)
  return response.user?.permissions || []
}

export async function syncWechatLoginWithBackend(params: {
  requestedRole: UserRole
  nickName: string
  avatarUrl: string
}): Promise<SessionUser> {
  if (!isRemoteApiEnabled()) throw new Error('微信登录仅适用于 API 模式')
  const loginResult = await uni.login({ provider: 'weixin' })
  if (!loginResult.code) throw new Error('未获取到微信登录凭证')
  clearApiToken()
  const response = await apiRequest({
    path: '/auth/wechat-login',
    method: 'POST',
    auth: false,
    schema: apiLoginResponseSchema,
    body: {
      code: loginResult.code,
      nickname: params.nickName,
      avatar_url: params.avatarUrl,
      requested_role: params.requestedRole,
    },
  })
  saveApiToken(response.access_token)
  if (!response.user) throw new Error('微信登录未返回用户信息')
  return toSessionUser(response.user)
}
