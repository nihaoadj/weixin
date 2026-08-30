import { afterEach, describe, expect, it, vi } from 'vitest'
import { detectEmergency, requestMedicalAssistant } from './ai'

describe('ai service safety', () => {
  afterEach(() => {
    vi.unstubAllEnvs()
    vi.unstubAllGlobals()
  })

  it('detects emergency descriptions', () => {
    expect(detectEmergency('胸口持续压榨样疼痛，呼吸困难')).toBe(true)
  })

  it('returns emergency guidance before demo answer', async () => {
    const response = await requestMedicalAssistant({
      prompt: '我胸口持续压榨样疼痛，已经两小时了',
      history: [],
    })

    expect(response).toContain('120')
  })

  it('returns demo guidance when no API base URL is configured', async () => {
    const response = await requestMedicalAssistant({
      prompt: '请说明高血压诊断标准',
      history: [],
    })

    expect(response).toContain('演示反馈')
  })

  it('returns mode-specific demo guidance', async () => {
    const simulation = await requestMedicalAssistant({
      prompt: '请进行模拟问诊',
      history: [],
      mode: '模拟诊疗',
    })
    const caseAnalysis = await requestMedicalAssistant({
      prompt: '请分析病例',
      history: [],
      mode: '病例分析',
    })

    expect(simulation).toContain('继续询问')
    expect(caseAnalysis).toContain('鉴别诊断')
  })

  it('uses the remote API and omits duplicated current prompt from history', async () => {
    vi.stubEnv('VITE_APP_MODE', 'api')
    vi.stubEnv('VITE_API_BASE_URL', 'https://api.example.com/')
    const request = vi.fn((options: UniApp.RequestOptions) => {
      expect(options.url).toBe('https://api.example.com/v1/medical-chat')
      expect(options.header).toMatchObject({ Authorization: 'Bearer test-token' })
      expect(options.data).toMatchObject({
        prompt: '肺炎如何鉴别诊断',
        messages: [{ role: 'assistant', content: '先看病史' }],
      })
      options.success?.({
        statusCode: 200,
        data: { data: { content: '远程回答' } },
        header: {},
        cookies: [],
        errMsg: 'request:ok',
      })
    })
    vi.stubGlobal('uni', { request, getStorageSync: () => 'test-token' })

    await expect(
      requestMedicalAssistant({
        prompt: '肺炎如何鉴别诊断',
        history: [
          { id: '1', role: 'assistant', content: '先看病史', timestamp: '10:00' },
          { id: '2', role: 'user', content: '肺炎如何鉴别诊断', timestamp: '10:01' },
        ],
      }),
    ).resolves.toBe('远程回答')
  })

  it('rejects invalid remote API responses', async () => {
    vi.stubEnv('VITE_APP_MODE', 'api')
    vi.stubEnv('VITE_API_BASE_URL', 'https://api.example.com')
    vi.stubGlobal('uni', {
      getStorageSync: () => 'test-token',
      request: (options: UniApp.RequestOptions) => {
        options.success?.({
          statusCode: 502,
          data: { message: 'gateway failed' },
          header: {},
          cookies: [],
          errMsg: 'request:ok',
        })
      },
    })

    await expect(requestMedicalAssistant({ prompt: '普通医学问题', history: [] })).rejects.toThrow('gateway failed')
  })
})
