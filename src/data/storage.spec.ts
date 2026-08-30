import { describe, expect, it, vi } from 'vitest'
import { getConversations, getSession, saveSession } from '@/services/repository'
import { z } from 'zod'
import { sessionSchema, storage, storageKeys } from './storage'

describe('storage gateway', () => {
  it('does not expose corrupted persisted values to the domain layer', () => {
    vi.mocked(uni.setStorageSync)(storageKeys.user, { role: 'student', openid: 42 })
    const warning = vi.spyOn(console, 'warn').mockImplementation(() => undefined)

    expect(getSession()).toBeNull()
    expect(warning).toHaveBeenCalledWith(`忽略不符合本地数据契约的存储项: ${storageKeys.user}`)
  })

  it('validates data before writing', () => {
    expect(() => storage.write(storageKeys.user, null, sessionSchema.nullable())).not.toThrow()
    expect(uni.setStorageSync).toHaveBeenCalledWith(storageKeys.user, null)
  })

  it('migrates v2 private data once without losing already scoped data', () => {
    const user = {
      openid: 'legacy/user',
      role: 'student' as const,
      nickName: '学生',
      avatarUrl: '',
      createdAt: '2026-08-30',
    }
    const conversation = { conversationId: 'legacy', messages: [], createdAt: '2026-08-30', updatedAt: '2026-08-30' }
    uni.setStorageSync(storageKeys.schemaVersion, 2)
    uni.setStorageSync(storageKeys.conversations, [conversation])
    saveSession(user)
    expect(getConversations()).toEqual([conversation])
    expect(uni.getStorageSync(`${storageKeys.conversations}:legacy%2Fuser`)).toEqual([conversation])
    expect(uni.getStorageSync(storageKeys.conversations)).toBeUndefined()
    expect(uni.getStorageSync(storageKeys.schemaVersion)).toBe(3)
    saveSession({ ...user, openid: 'other' })
    expect(getConversations()).toEqual([])
    saveSession(user)
    expect(getConversations()).toEqual([conversation])
  })

  it('preserves corrupt legacy data and reports storage failures without content logs', () => {
    const warning = vi.spyOn(console, 'warn').mockImplementation(() => undefined)
    const error = vi.spyOn(console, 'error').mockImplementation(() => undefined)
    uni.setStorageSync(storageKeys.conversations, [{ private: 'synthetic medical note' }])
    saveSession({ openid: 'student', role: 'student', nickName: '学生', avatarUrl: '', createdAt: '2026-08-30' })
    expect(uni.getStorageSync(storageKeys.conversations)).toEqual([{ private: 'synthetic medical note' }])
    expect(() => storage.write('test', 'invalid', z.number() as never)).toThrow('拒绝写入')
    vi.mocked(uni.setStorageSync).mockImplementation(() => {
      throw new Error('synthetic medical note')
    })
    expect(() => storage.write('test', 'value', z.string())).toThrow('本地存储空间不足')
    expect(error).toHaveBeenCalledWith('写入本地存储失败: test')
    expect(JSON.stringify(error.mock.calls)).not.toContain('synthetic medical note')
    warning.mockRestore()
    error.mockRestore()
  })

  it('does not migrate business data in API mode', () => {
    vi.stubEnv('VITE_APP_MODE', 'api')
    uni.setStorageSync(storageKeys.schemaVersion, 2)
    uni.setStorageSync(storageKeys.conversations, [])
    saveSession({ openid: 'api-user', role: 'student', nickName: '学生', avatarUrl: '', createdAt: '2026-08-30' })
    expect(uni.getStorageSync(storageKeys.schemaVersion)).toBe(2)
    expect(uni.getStorageSync(`${storageKeys.conversations}:api-user`)).toBeUndefined()
    vi.unstubAllEnvs()
  })
})
