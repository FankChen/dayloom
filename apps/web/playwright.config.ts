import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './tests',
  fullyParallel: false,
  workers: 1,
  timeout: 30000,
  expect: { timeout: 10000 },
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: 'http://127.0.0.1:18878',
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
    url: 'http://127.0.0.1:18878/api/health',
    reuseExistingServer: false,
    timeout: 60000,
    env: {
      DAYLOOM_DEV_API_PORT: '18078',
      DAYLOOM_DEV_WEB_PORT: '18878',
      DAYLOOM_DATABASE_URL: 'sqlite:///data/e2e.db',
      DAYLOOM_MODEL_PROVIDER: 'DemoProvider',
      DAYLOOM_ACCESS_TOKEN: '',
      DAYLOOM_WORKER_POLL_SECONDS: '0.1',
    },
  },
})
