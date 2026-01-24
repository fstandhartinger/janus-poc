import { defineConfig, devices } from '@playwright/test';

const testPort = process.env.TEST_PORT || '3001';
const baseURL = process.env.TEST_BASE_URL || `http://127.0.0.1:${testPort}`;

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  use: {
    baseURL,
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: process.env.TEST_BASE_URL
    ? undefined
    : {
        command: `PORT=${testPort} npm run start`,
        url: baseURL,
        reuseExistingServer: true,
        timeout: 60000,
      },
});
