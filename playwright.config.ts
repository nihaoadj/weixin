import { defineConfig, devices } from '@playwright/test'

const apiPort = Number(process.env.E2E_API_PORT ?? 8001)
const h5Port = Number(process.env.E2E_H5_PORT ?? 41733)

export default defineConfig({
  testDir: './e2e',
  testIgnore: /(demo-flow|design-visual)\.spec\.ts/,
  timeout: 90_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [['html', { open: 'never' }], ['github']] : 'list',
  use: {
    baseURL: `http://127.0.0.1:${h5Port}`,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  webServer: [
    {
      command: 'python scripts/run_e2e_server.py',
      cwd: './backend',
      url: `http://127.0.0.1:${apiPort}/health`,
      timeout: 30_000,
      reuseExistingServer: false,
      env: {
        ...process.env,
        E2E_PORT: String(apiPort),
        E2E_CORS_ORIGIN: `http://127.0.0.1:${h5Port}`,
      },
    },
    {
      command: `npm run dev:h5 -- --host 127.0.0.1 --port ${h5Port}`,
      cwd: '.',
      url: `http://127.0.0.1:${h5Port}`,
      timeout: 60_000,
      reuseExistingServer: false,
      env: {
        ...process.env,
        VITE_APP_MODE: 'api',
        VITE_API_BASE_URL: `http://127.0.0.1:${apiPort}`,
      },
    },
  ],
  projects: [
    {
      name: 'mobile-chromium',
      use: { ...devices['Pixel 5'], browserName: 'chromium', viewport: { width: 390, height: 844 } },
    },
    {
      name: 'desktop-chromium',
      testMatch: /visual\.spec\.ts/,
      use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 900 } },
    },
  ],
})
