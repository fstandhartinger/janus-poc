import { test, expect } from '@playwright/test';
import {
  mockServiceHealth,
  onlyForProjects,
  stabilizeLandingHero,
  stabilizeChatPage,
  waitForChatReady,
} from './utils';

test.beforeEach(async ({ page }) => {
  await mockServiceHealth(page);
});

test.describe('Theme & Dark Mode', () => {
  test('landing page dark mode styling', async ({ page }, testInfo) => {
    onlyForProjects(testInfo, ['Desktop']);

    await page.goto('/');
    await page.waitForLoadState('networkidle');
    await stabilizeLandingHero(page);

    // Verify dark background
    const bgColor = await page.evaluate(() =>
      getComputedStyle(document.body).backgroundColor
    );

    // Should be dark (low RGB values)
    const rgb = bgColor.match(/\d+/g)?.map(Number) || [];
    const avgBrightness = rgb.reduce((a, b) => a + b, 0) / 3;
    expect(avgBrightness).toBeLessThan(50); // Dark mode check

    await expect(page).toHaveScreenshot('theme-dark-landing.png', {
      fullPage: true,
      animations: 'disabled',
    });
  });

  test('chat page dark mode styling', async ({ page }, testInfo) => {
    onlyForProjects(testInfo, ['Desktop']);

    await page.goto('/chat');
    await page.waitForLoadState('networkidle');
    await waitForChatReady(page);
    await stabilizeChatPage(page);

    await expect(page).toHaveScreenshot('theme-dark-chat.png', {
      animations: 'disabled',
      maxDiffPixels: 6000,
    });
  });

  test('aurora gradient is visible', async ({ page }, testInfo) => {
    onlyForProjects(testInfo, ['Desktop']);

    await page.goto('/');
    await page.waitForLoadState('networkidle');
    await stabilizeLandingHero(page);

    // Check for aurora gradient elements
    const hasGradient = await page.evaluate(() => {
      const elements = document.querySelectorAll('*');
      for (const el of elements) {
        const style = getComputedStyle(el);
        if (style.backgroundImage.includes('gradient')) {
          return true;
        }
      }
      return false;
    });

    expect(hasGradient).toBe(true);
  });

  test('moss green accent color is used', async ({ page }, testInfo) => {
    onlyForProjects(testInfo, ['Desktop']);

    await page.goto('/chat');
    await page.waitForLoadState('networkidle');

    // Check for moss green (#63D297) usage
    const hasMossGreen = await page.evaluate(() => {
      const elements = document.querySelectorAll('*');
      for (const el of elements) {
        const style = getComputedStyle(el);
        if (
          style.color.includes('99') ||
          style.backgroundColor.includes('99') ||
          style.borderColor.includes('99')
        ) {
          return true;
        }
      }
      // Also check for class names
      return document.querySelector('.text-moss, .bg-moss, .border-moss') !== null;
    });

    expect(hasMossGreen).toBe(true);
  });
});
