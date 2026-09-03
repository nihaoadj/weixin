import { defineConfig } from 'vitest/config'
import { fileURLToPath } from 'node:url'
import vue from '@dcloudio/vite-plugin-uni/node_modules/@vitejs/plugin-vue'

export default defineConfig({
  // Use the locked transitive Vue compiler for Vitest only. The uni plugin is
  // build-owned and currently cannot resolve its compiler in this worktree.
  plugins: [vue()],
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
      all: true,
      include: [
        'src/App.vue',
        'src/bootstrap/**/*.ts',
        'src/components/**/*.vue',
        'src/features/**/*.ts',
        'src/pages/**/*.vue',
        'src/platform/**/*.ts',
        'src/shared/**/*.ts',
        'src/utils/**/*.ts',
      ],
      exclude: [
        'src/**/*.spec.ts',
        'src/**/*.test.ts',
        'src/data/contracts/openapi.generated.ts',
        'src/config/**/*.ts',
        'src/types/**/*.ts',
        'src/features/**/demoSeeds.ts',
        'src/features/**/demoProblemSeeds.ts',
        'src/data/demo.ts',
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
