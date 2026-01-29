import { test, expect } from '@playwright/test';
import { signInWithChutes, stubChatDependencies, waitForChatReady } from './utils/helpers';

const CHUTES_FINGERPRINT = process.env.CHUTES_FINGERPRINT || '';

test.describe('Memory Feature', () => {
  test.skip(!CHUTES_FINGERPRINT, 'Requires CHUTES_FINGERPRINT env var');

  test.beforeEach(async ({ page }) => {
    await stubChatDependencies(page, { id: 'test-user', username: 'tester' });
    await page.route('**/api/memories**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ memories: [] }),
      });
    });

    await page.goto('/chat');
    await waitForChatReady(page);
    await signInWithChutes(page, CHUTES_FINGERPRINT);
  });

  test('memory toggle is visible', async ({ page }) => {
    const memoryToggle = page.locator('button[aria-label*="Memory"], button[aria-label*="memory"]');
    await expect(memoryToggle.first()).toBeVisible();
  });

  test('can open memory sheet', async ({ page }) => {
    const memoryToggle = page.locator('button[aria-label*="Memory"], button[aria-label*="memory"]');
    await memoryToggle.first().click();

    const dialog = page.getByRole('dialog', { name: /Memory management/i });
    await expect(dialog).toBeVisible();
  });

  test('can toggle memory on and off', async ({ page }) => {
    const memoryToggle = page.locator('button[aria-label*="Memory"], button[aria-label*="memory"]');
    await memoryToggle.first().click();

    const dialog = page.getByRole('dialog', { name: /Memory management/i });
    const switchButton = dialog.locator('button[role="switch"]');
    await expect(switchButton).toBeVisible();

    const initialState = await switchButton.getAttribute('aria-checked');
    await switchButton.click();
    await page.waitForTimeout(300);

    const nextState = await switchButton.getAttribute('aria-checked');
    expect(nextState).not.toBe(initialState);
  });
});
