import { test, expect } from '@playwright/test';
import { signInWithChutes, waitForPageReady } from './utils/helpers';

const CHUTES_FINGERPRINT = process.env.CHUTES_FINGERPRINT || '';

test.describe('Authentication', () => {
  test('shows free chat counter when signed out', async ({ page }) => {
    await page.goto('/chat');
    await waitForPageReady(page);

    await expect(page.locator('button:has-text("Sign in")')).toBeVisible();
    await expect(page.locator('.chat-free-count')).toBeVisible();
  });

  test('can sign in with Chutes fingerprint', async ({ page }) => {
    test.skip(!CHUTES_FINGERPRINT, 'Requires CHUTES_FINGERPRINT env var');

    await page.goto('/chat');
    await waitForPageReady(page);
    await signInWithChutes(page, CHUTES_FINGERPRINT);

    await expect(page.locator('.auth-user-button')).toBeVisible();
    await expect(page.locator('.chat-free-count')).toHaveCount(0);
  });

  test('can sign out', async ({ page }) => {
    test.skip(!CHUTES_FINGERPRINT, 'Requires CHUTES_FINGERPRINT env var');

    await page.goto('/chat');
    await waitForPageReady(page);
    await signInWithChutes(page, CHUTES_FINGERPRINT);

    const userMenuButton = page.locator('.auth-user-button');
    await expect(userMenuButton).toBeVisible();
    await userMenuButton.click();

    const signOutButton = page.locator('.auth-user-signout');
    await expect(signOutButton).toBeVisible();
    await signOutButton.click();

    await expect(page.locator('button:has-text("Sign in")')).toBeVisible();
  });
});
