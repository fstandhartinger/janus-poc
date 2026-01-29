import { test, expect } from '@playwright/test';
import {
  mockChatStream,
  mockServiceHealth,
  onlyForProjects,
  stabilizeChatPage,
  stabilizeLandingHero,
  waitForChatReady,
} from './utils';

test.beforeEach(async ({ page }) => {
  await mockServiceHealth(page);
});

test.describe('UI State Screenshots', () => {
  test.describe('Loading States', () => {
    test('chat loading indicator', async ({ page }, testInfo) => {
      onlyForProjects(testInfo, ['Desktop']);

      await mockChatStream(page, { content: 'Loading response', delayMs: 2500 });
      await page.goto('/chat');
      await page.waitForLoadState('networkidle');

      // Send message to trigger loading
      const input = page.locator('textarea').first();
      await input.fill('Hello');
      await page.keyboard.press('Enter');

      // Capture loading state quickly
      await page.waitForTimeout(500);

      const loadingIndicator = page
        .locator('[data-loading="true"], .loading, .spinner, .chat-streaming')
        .first();
      if (await loadingIndicator.isVisible()) {
        await expect(loadingIndicator).toHaveScreenshot('state-loading.png');
      }

      await page.waitForTimeout(2500);
    });
  });

  test.describe('Error States', () => {
    test('error message styling', async ({ page }, testInfo) => {
      onlyForProjects(testInfo, ['Desktop']);

      await page.goto('/chat');
      await page.waitForLoadState('networkidle');

      // Inject error message for screenshot
      await page.evaluate(() => {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message bg-red-500/20 border border-red-500 p-4 rounded';
        errorDiv.textContent = 'An error occurred. Please try again.';
        document.body.appendChild(errorDiv);
      });

      const errorMessage = page.locator('.error-message').first();
      await expect(errorMessage).toHaveScreenshot('state-error.png');
    });
  });

  test.describe('Empty States', () => {
    test('no conversations empty state', async ({ page }, testInfo) => {
      onlyForProjects(testInfo, ['Desktop']);

      await page.goto('/chat');
      await page.waitForLoadState('networkidle');

      // Clear chat storage to show empty state while preserving pre-release access.
      await page.evaluate(() => {
        const preRelease = localStorage.getItem('janusPreReleasePassword');
        localStorage.setItem(
          'janus-chat-storage',
          JSON.stringify({ state: { sessions: [], currentSessionId: null }, version: 0 })
        );
        if (preRelease) {
          localStorage.setItem('janusPreReleasePassword', preRelease);
        }
      });
      await page.reload();
      await page.waitForLoadState('networkidle');
      await waitForChatReady(page);
      await stabilizeChatPage(page);

      await expect(page).toHaveScreenshot('state-empty-chat.png', {
        animations: 'disabled',
        maxDiffPixels: 6000,
      });
    });
  });

  test.describe('Hover States', () => {
    test('button hover', async ({ page }, testInfo) => {
      onlyForProjects(testInfo, ['Desktop']);

      await page.goto('/');
      await page.waitForLoadState('networkidle');
      await stabilizeLandingHero(page);

      const button = page.locator('a.bg-moss, button.bg-moss, .btn-primary').first();
      if (await button.isVisible()) {
        await button.hover();
        await page.waitForTimeout(300);
        await expect(button).toHaveScreenshot('state-button-hover.png');
      }
    });

    test('link hover', async ({ page }, testInfo) => {
      onlyForProjects(testInfo, ['Desktop']);

      await page.goto('/');
      await page.waitForLoadState('networkidle');
      await stabilizeLandingHero(page);

      const link = page.locator('a').first();
      if (await link.isVisible()) {
        await link.hover();
        await page.waitForTimeout(300);
        await expect(link).toHaveScreenshot('state-link-hover.png');
      }
    });
  });

  test.describe('Focus States', () => {
    test('input focus', async ({ page }, testInfo) => {
      onlyForProjects(testInfo, ['Desktop']);

      await page.goto('/chat');
      await page.waitForLoadState('networkidle');

      const input = page.locator('textarea').first();
      await input.focus();
      await page.waitForTimeout(300);

      await expect(input).toHaveScreenshot('state-input-focus.png');
    });
  });
});
