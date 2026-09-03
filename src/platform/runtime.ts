export type RuntimeMode = 'demo' | 'api'

function readRuntimeMode(): RuntimeMode {
  const mode = import.meta.env.VITE_APP_MODE?.trim().toLowerCase()
  if (!mode || mode === 'demo') return 'demo'
  if (mode === 'api') return 'api'
  throw new Error(`不支持的 VITE_APP_MODE: ${mode}`)
}

let configuredMode: RuntimeMode | undefined
let configuredEnvValue: string | undefined

/** The bootstrap root resolves mode once; direct unit tests may use the env fallback. */
export function configureRuntimeMode(mode: RuntimeMode): RuntimeMode {
  configuredMode = mode
  configuredEnvValue = import.meta.env.VITE_APP_MODE?.trim().toLowerCase() || 'demo'
  return configuredMode
}

export function getRuntimeMode(): RuntimeMode {
  const currentEnvValue = import.meta.env.VITE_APP_MODE?.trim().toLowerCase() || 'demo'
  if (!configuredMode || configuredEnvValue !== currentEnvValue) {
    configuredMode = readRuntimeMode()
    configuredEnvValue = currentEnvValue
  }
  return configuredMode
}

export function getApiBaseUrl(): string {
  const value = import.meta.env.VITE_API_BASE_URL?.trim().replace(/\/$/, '') || ''
  if (getRuntimeMode() === 'api' && !value) {
    throw new Error('API 模式必须配置 VITE_API_BASE_URL')
  }
  return value
}

export function isDemoMode(): boolean {
  return getRuntimeMode() === 'demo'
}

export function isApiMode(): boolean {
  return getRuntimeMode() === 'api'
}
