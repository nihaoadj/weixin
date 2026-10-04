export type StableErrorCode =
  | 'AUTH_REQUIRED'
  | 'FORBIDDEN'
  | 'RESOURCE_NOT_FOUND'
  | 'STATE_CONFLICT'
  | 'VALIDATION_ERROR'
  | 'SERVICE_ERROR'
  | 'ROLE_REQUIRED'
  | 'INVALID_DATE_RANGE'
  | 'CONTRACT_ERROR'
  | 'NETWORK_ERROR'
  | 'API_CONFIG_ERROR'
  | 'STALE_SESSION'
  | 'UNSUPPORTED_OPERATION'
  | 'RETIRED_FLOW'

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
