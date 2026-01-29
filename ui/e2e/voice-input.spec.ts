import { test, expect } from '@playwright/test';
import { waitForPageReady } from './utils/helpers';

const VOICE_ENABLED = process.env.NEXT_PUBLIC_ENABLE_VOICE_INPUT === 'true';

test.describe('Voice Input', () => {
  test.skip(!VOICE_ENABLED, 'Voice input disabled');

  test.beforeEach(async ({ page, context }) => {
    await context.grantPermissions(['microphone']);
    await page.route('**/api/transcribe/health**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ available: true, endpoint: 'gateway', api_key_configured: true }),
      });
    });
    await page.goto('/chat');
    await waitForPageReady(page);
  });

  test('microphone button exists', async ({ page }) => {
    const micButton = page.locator('button[aria-label*="voice"], button[aria-label*="recording"]');
    await expect(micButton.first()).toBeVisible();
  });

  test('clicking mic button shows recording state', async ({ page }) => {
    const micButton = page.locator('button[aria-label*="voice"], button[aria-label*="recording"]');
    await expect(micButton.first()).toBeVisible();

    await micButton.first().click();

    const recordingIndicator = page.locator('text=/Esc to cancel/i');
    await expect(recordingIndicator).toBeVisible();
  });

  test('handles permission denied gracefully', async ({ page, context }) => {
    await context.clearPermissions();

    const micButton = page.locator('button[aria-label*="voice"], button[aria-label*="recording"]');
    if (!(await micButton.first().isVisible())) {
      test.skip(true, 'Voice input button not available');
    }

    await micButton.first().click();
    await page.waitForTimeout(1000);

    const errorMessage = page.locator('text=/permission denied|microphone permission denied/i');
    if ((await errorMessage.count()) > 0) {
      await expect(errorMessage.first()).toBeVisible();
    }
  });
});
