import { test, expect } from '@playwright/test';
import { mockServiceHealth, onlyForProjects, stabilizeLandingHero } from './utils';

test.beforeEach(async ({ page }) => {
  await mockServiceHealth(page);
});

test.describe('Accessibility Visual Checks', () => {
  test('focus visible outlines', async ({ page }, testInfo) => {
    onlyForProjects(testInfo, ['Desktop']);

    await page.goto('/chat');
    await page.waitForLoadState('networkidle');

    // Tab through focusable elements
    const focusTarget = page.locator('[data-testid="chat-input"], textarea').first();
    await focusTarget.focus();
    await page.waitForTimeout(300);

    // Capture focus ring
    await expect(focusTarget).toHaveScreenshot('a11y-focus-outline.png');
  });

  test('sufficient color contrast', async ({ page }, testInfo) => {
    onlyForProjects(testInfo, ['Desktop']);

    await page.goto('/');
    await page.waitForLoadState('networkidle');
    await stabilizeLandingHero(page);

    // Visual check - actual contrast testing would need axe-core
    await expect(page).toHaveScreenshot('a11y-contrast-landing.png', {
      animations: 'disabled',
    });
  });

  test('text is readable at default zoom', async ({ page }, testInfo) => {
    onlyForProjects(testInfo, ['Desktop']);

    await page.goto('/');
    await page.waitForLoadState('networkidle');
    await stabilizeLandingHero(page);

    // Screenshot at 100% zoom
    await expect(page).toHaveScreenshot('a11y-zoom-100.png', {
      animations: 'disabled',
    });
  });

  test('text is readable at 200% zoom', async ({ page }, testInfo) => {
    onlyForProjects(testInfo, ['Desktop']);

    await page.goto('/');

    // Set 200% zoom
    await page.evaluate(() => {
      document.body.style.zoom = '200%';
    });
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(500);
    await stabilizeLandingHero(page);

    await expect(page).toHaveScreenshot('a11y-zoom-200.png', {
      animations: 'disabled',
    });
  });
});
