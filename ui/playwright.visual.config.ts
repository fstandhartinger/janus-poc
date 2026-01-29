import { defineConfig, devices } from '@playwright/test';

const testUrl = process.env.TEST_URL || process.env.TEST_BASE_URL;
const testPort = process.env.TEST_PORT || '4721';
const baseURL = testUrl || `http://127.0.0.1:${testPort}`;

export default defineConfig({
  testDir: './e2e/visual',
  snapshotDir: './e2e/visual/snapshots',
  timeout: 30000,
  expect: {
    toHaveScreenshot: {
      maxDiffPixels: 100,
      threshold: 0.2,
    },
  },
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: [
    ['html', { outputFolder: 'playwright-report' }],
    ['list'],
  ],
  use: {
    baseURL,
    storageState: {
      cookies: [],
      origins: [
        {
          origin: baseURL,
          localStorage: [
            {
              name: 'janusPreReleasePassword',
              value: process.env.CHUTES_JANUS_PRE_RELEASE_PWD || 'chutesSquad987!!!',
            },
            {
              name: 'janus-chat-storage',
              value: JSON.stringify({ state: { sessions: [], currentSessionId: null }, version: 0 }),
            },
            {
              name: 'janus_free_chats_v1',
              value: JSON.stringify({ date: '1970-01-01', count: 0 }),
            },
          ],
        },
      ],
    },
  },
  projects: [
    {
      name: 'Desktop',
      use: {
        browserName: 'chromium',
        ...devices['Desktop Chrome'],
        viewport: { width: 1920, height: 1080 },
      },
    },
    {
      name: 'Tablet',
      use: {
        browserName: 'chromium',
        ...devices['iPad Pro'],
        viewport: { width: 1024, height: 768 },
      },
    },
    {
      name: 'Mobile',
      use: {
        browserName: 'chromium',
        ...devices['iPhone 14'],
        viewport: { width: 390, height: 844 },
      },
    },
  ],
  webServer: testUrl
    ? undefined
    : {
        command: `PORT=${testPort} npm run dev`,
        url: baseURL,
        reuseExistingServer: true,
        timeout: 60000,
      },
});
