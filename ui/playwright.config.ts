import { defineConfig, devices } from '@playwright/test';

const testUrl = process.env.TEST_URL || process.env.TEST_BASE_URL;
const testPort = process.env.TEST_PORT || '4721';
const baseURL = testUrl || `http://127.0.0.1:${testPort}`;

export default defineConfig({
  testDir: './e2e',
  testIgnore: ['e2e/visual/**'],
  timeout: 60000,
  expect: {
    timeout: 10000,
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
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
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
      name: 'Desktop Chrome',
      use: { ...devices['Desktop Chrome'] },
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
