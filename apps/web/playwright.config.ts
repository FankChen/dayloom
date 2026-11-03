import { defineConfig, devices } from '@playwright/test'

const webPort = process.env.DAYLOOM_E2E_WEB_PORT ?? '18878'
const apiPort = process.env.DAYLOOM_E2E_API_PORT ?? '18078'
const baseURL = `http://127.0.0.1:${webPort}`

export default defineConfig({
  testDir: './tests',
  fullyParallel: false,
  workers: 1,
  timeout: 30000,
  expect: { timeout: 10000 },
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'desktop',
      use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 1000 } },
    },
    { name: 'mobile', use: { ...devices['Pixel 7'] } },
  ],
  webServer: {
    command: 'node ../../scripts/dev.mjs',
    url: `${baseURL}/api/health`,
    reuseExistingServer: false,
    timeout: 60000,
    env: {
      VITE_API_BASE_URL: '',
      DAYLOOM_AUTH_BACKEND: 'LocalAccess',
      DAYLOOM_PRODUCTION: 'false',
      DAYLOOM_DEV_API_PORT: apiPort,
      DAYLOOM_DEV_WEB_PORT: webPort,
      DAYLOOM_DATABASE_URL: process.env.DAYLOOM_E2E_DATABASE_URL ?? 'sqlite:///data/e2e.db',
      DAYLOOM_MODEL_PROVIDER: 'DemoProvider',
      DAYLOOM_ACCESS_TOKEN: '',
      DAYLOOM_WORKER_POLL_SECONDS: '0.1',
    },
  },
})
