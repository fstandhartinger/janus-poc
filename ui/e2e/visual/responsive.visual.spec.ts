import { test, expect } from '@playwright/test';
import {
  mockServiceHealth,
  onlyForProjects,
  stabilizeLandingHero,
  stabilizeChatPage,
  waitForChatReady,
} from './utils';

const viewports = [
  { name: 'desktop-4k', width: 3840, height: 2160 },
  { name: 'desktop-1080p', width: 1920, height: 1080 },
  { name: 'laptop', width: 1440, height: 900 },
  { name: 'tablet-landscape', width: 1024, height: 768 },
  { name: 'tablet-portrait', width: 768, height: 1024 },
  { name: 'mobile-large', width: 428, height: 926 },
  { name: 'mobile-medium', width: 390, height: 844 },
  { name: 'mobile-small', width: 375, height: 667 },
];

test.beforeEach(async ({ page }) => {
  await mockServiceHealth(page);
});

test.describe('Responsive Layouts', () => {
  for (const viewport of viewports) {
    test.describe(`${viewport.name} (${viewport.width}x${viewport.height})`, () => {
      test.beforeEach(async ({ page }, testInfo) => {
        onlyForProjects(testInfo, ['Desktop']);
        await page.setViewportSize({ width: viewport.width, height: viewport.height });
      });

      test('landing page layout', async ({ page }) => {
        await page.goto('/');
        await page.waitForLoadState('networkidle');
        await page.waitForTimeout(500);
        await stabilizeLandingHero(page);

        await expect(page).toHaveScreenshot(`responsive-landing-${viewport.name}.png`, {
          fullPage: true,
          animations: 'disabled',
        });
      });

      test('chat page layout', async ({ page }) => {
        await page.goto('/chat');
        await page.waitForLoadState('networkidle');
        await page.waitForTimeout(500);
        await waitForChatReady(page);
        await stabilizeChatPage(page);

        await expect(page).toHaveScreenshot(`responsive-chat-${viewport.name}.png`, {
          animations: 'disabled',
          maxDiffPixels: 6000,
        });
      });

      test('no horizontal scroll', async ({ page }) => {
        await page.goto('/chat');
        await page.waitForLoadState('networkidle');

        const hasHorizontalScroll = await page.evaluate(() =>
          document.body.scrollWidth > document.body.clientWidth
        );

        expect(hasHorizontalScroll).toBe(false);
      });
    });
  }
});
