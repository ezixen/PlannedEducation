import { defineConfig, devices } from '@playwright/test';

const PORTAL_URL = process.env.PORTAL_URL || 'http://127.0.0.1:5175';
const CI = process.env.CI === 'true';

export default defineConfig({
  testDir: './tests/visual',
  snapshotDir: './tests/visual/snapshots',
  fullyParallel: false,
  forbidOnly: CI,
  retries: 0,
  workers: 1,
  reporter: 'list',
  globalTeardown: './tests/visual/global-teardown.ts',
  use: {
    baseURL: PORTAL_URL,
    trace: 'off',
    screenshot: 'off',
  },
  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        channel: 'chrome',
      },
    },
    {
      name: 'mobile-chrome',
      use: {
        ...devices['Pixel 5'],
        channel: 'chrome',
      },
    },
    {
      name: 'tablet',
      use: {
        viewport: { width: 768, height: 1024 },
        channel: 'chrome',
      },
    },
  ],
  expect: {
    toHaveScreenshot: {
      maxDiffPixels: 150,
      threshold: 0.2,
      animations: 'disabled',
    },
  },
});