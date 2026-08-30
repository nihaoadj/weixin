export class AppError extends Error {
  readonly statusCode?: number
  readonly code: string

  constructor(message: string, options: { code?: string; statusCode?: number; cause?: unknown } = {}) {
    super(message, { cause: options.cause })
    this.name = 'AppError'
    this.code = options.code || 'APP_ERROR'
    this.statusCode = options.statusCode
  }
}
