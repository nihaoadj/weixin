import { defineConfig } from 'vitest/config'
import { fileURLToPath } from 'node:url'

export default defineConfig({
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  test: {
    environment: 'happy-dom',
    include: ['src/**/*.{spec,test}.ts'],
    setupFiles: ['src/test/setup.ts'],
    clearMocks: true,
    coverage: {
      provider: 'v8',
      reporter: ['text', 'lcov'],
      include: [
        'src/config/runtime.ts',
        'src/services/ai.ts',
        'src/services/apiClient.ts',
        'src/services/auth.ts',
        'src/services/remoteAuth.ts',
        'src/services/caseRepository.ts',
        'src/services/caseRepositoryAsync.ts',
        'src/utils/**/*.ts',
      ],
      thresholds: {
        branches: 80,
        functions: 85,
        lines: 85,
        statements: 85,
      },
    },
  },
})
