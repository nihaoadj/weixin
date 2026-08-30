import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  testMatch: /demo-flow\.spec\.ts/,
  workers: 1,
  timeout: 90_000,
  expect: { timeout: 10_000 },
  reporter: 'list',
  use: {
    ...devices['Pixel 5'],
    browserName: 'chromium',
    baseURL: 'http://127.0.0.1:41734',
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure',
  },
  webServer: {
    command: 'npm run dev:h5 -- --host 127.0.0.1 --port 41734',
    url: 'http://127.0.0.1:41734',
    timeout: 60_000,
    reuseExistingServer: false,
    env: { ...process.env, VITE_APP_MODE: 'demo', VITE_API_BASE_URL: '' },
  },
})
