import { defineConfig, devices } from '@playwright/test'

const demoH5Port = Number(process.env.E2E_DEMO_H5_PORT ?? 41734)

export default defineConfig({
  testDir: './e2e',
  testMatch: /(demo-flow|design-visual)\.spec\.ts/,
  workers: 1,
  timeout: 90_000,
  expect: { timeout: 10_000 },
  reporter: 'list',
  use: {
    browserName: 'chromium',
    baseURL: `http://127.0.0.1:${demoH5Port}`,
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure',
  },
  projects: [
    {
      name: 'mobile-demo',
      use: { ...devices['Pixel 5'], browserName: 'chromium' },
    },
    {
      name: 'desktop-demo',
      testMatch: /design-visual\.spec\.ts/,
      use: { ...devices['Desktop Chrome'], browserName: 'chromium', viewport: { width: 1440, height: 900 } },
    },
  ],
  webServer: {
    command: `npm run dev:h5 -- --host 127.0.0.1 --port ${demoH5Port}`,
    url: `http://127.0.0.1:${demoH5Port}`,
    timeout: 60_000,
    reuseExistingServer: false,
    env: { ...process.env, VITE_APP_MODE: 'demo', VITE_API_BASE_URL: '' },
  },
})
