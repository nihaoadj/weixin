import { vi } from 'vitest'

export function respond(
  options: UniApp.RequestOptions,
  data: UniApp.RequestSuccessCallbackResult['data'],
  statusCode = 200,
): void {
  options.success?.({ statusCode, data, header: {}, cookies: [], errMsg: 'request:ok' })
}
export function mockHttp(
  handler: (path: string, options: UniApp.RequestOptions) => UniApp.RequestSuccessCallbackResult['data'],
): void {
  vi.mocked(uni.request).mockImplementation((options) => {
    respond(options, handler(new URL(String(options.url)).pathname, options))
    return undefined as never
  })
}
export const now = '2026-08-30T00:00:00Z'
