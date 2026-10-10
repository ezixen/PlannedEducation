import { defineConfig, devices } from '@playwright/test';

const PORTAL_URL = process.env.PORTAL_URL || 'http://127.0.0.1:5175';
const CI = process.env.CI === 'true';

export default defineConfig({
  testDir: './tests',
  snapshotDir: './snapshots',
  fullyParallel: false,
  forbidOnly: CI,
  retries: CI ? 2 : 0,
  workers: CI ? 2 : 1,
  reporter: [
    ['list'],
    ['html', { outputFolder: '../playwright-report', open: 'never' }],
    ['json', { outputFile: '../test-results/results.json' }],
  ],
  globalTeardown: './tests/global-teardown.ts',
  use: {
    baseURL: PORTAL_URL,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    actionTimeout: 30000,
    navigationTimeout: 30000,
  },
  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
      },
    },
    {
      name: 'chromium-canary',
      use: {
        ...devices['Desktop Chrome'],
        channel: 'chrome-canary',
      },
    },
    {
      name: 'chromium-debug',
      use: {
        ...devices['Desktop Chrome'],
        channel: 'chrome',
        launchOptions: {
          args: [
            '--auto-open-devtools-for-tabs',
            '--disable-extensions',
            '--disable-background-networking',
            '--disable-background-timer-throttling',
            '--disable-backgrounding-occluded-windows',
            '--disable-breakpad',
            '--disable-client-side-phishing-detection',
            '--disable-component-extensions-with-background-pages',
            '--disable-default-apps',
            '--disable-dev-shm-usage',
            '--disable-extensions',
            '--disable-features=TranslateUI',
            '--disable-hang-monitor',
            '--disable-ipc-flooding-protection',
            '--disable-popup-blocking',
            '--disable-prompt-on-repost',
            '--disable-renderer-backgrounding',
            '--disable-sync',
            '--disable-translate',
            '--metrics-recording-only',
            '--no-first-run',
            '--no-default-browser-check',
            '--disable-background-mode',
            '--enable-automation',
            '--password-store=basic',
            '--use-mock-keychain',
          ],
        },
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
  timeout: 60000,
});