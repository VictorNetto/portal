import { defineConfig } from '@playwright/test'

// Browser tests against the running stack. They are meant to run inside the official
// Playwright container on the compose network (see README.md in this folder).
export default defineConfig({
  testDir: './tests',
  timeout: 90_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  workers: 1,            // tests share the dev database and a handful of seeded accounts
  retries: 0,
  reporter: 'list',
  use: {
    baseURL: process.env.E2E_BASE_URL || 'http://nginx:80',
    viewport: { width: 1440, height: 1000 },
    acceptDownloads: true,
    ignoreHTTPSErrors: true,
    locale: 'pt-BR',
    timezoneId: 'America/Sao_Paulo',
  },
})
