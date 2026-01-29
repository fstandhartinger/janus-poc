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

test.describe('Page Screenshots', () => {
  test.describe('Landing Page', () => {
    test('matches desktop baseline', async ({ page }, testInfo) => {
      onlyForProjects(testInfo, ['Desktop']);

      await page.goto('/');
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(1000); // Wait for animations
      await stabilizeLandingHero(page);

      await expect(page).toHaveScreenshot('landing-desktop.png', {
        fullPage: true,
        animations: 'disabled',
      });
    });

    test('matches tablet baseline', async ({ page }, testInfo) => {
      onlyForProjects(testInfo, ['Tablet']);

      await page.setViewportSize({ width: 1024, height: 768 });
      await page.goto('/');
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(1000);
      await stabilizeLandingHero(page);

      await expect(page).toHaveScreenshot('landing-tablet.png', {
        fullPage: true,
        animations: 'disabled',
      });
    });

    test('matches mobile baseline', async ({ page }, testInfo) => {
      onlyForProjects(testInfo, ['Mobile']);

      await page.setViewportSize({ width: 390, height: 844 });
      await page.goto('/');
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(1000);
      await stabilizeLandingHero(page);

      await expect(page).toHaveScreenshot('landing-mobile.png', {
        fullPage: true,
        animations: 'disabled',
      });
    });
  });

  test.describe('Chat Page', () => {
    test('empty state matches baseline', async ({ page }, testInfo) => {
      onlyForProjects(testInfo, ['Desktop']);

      await page.goto('/chat');
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(1000);
      await waitForChatReady(page);
      await stabilizeChatPage(page);

      await expect(page).toHaveScreenshot('chat-empty-desktop.png', {
        animations: 'disabled',
        maxDiffPixels: 6000,
      });
    });

    test('chat with model dropdown open', async ({ page }, testInfo) => {
      onlyForProjects(testInfo, ['Desktop']);

      await page.goto('/chat');
      await page.waitForLoadState('networkidle');
      await waitForChatReady(page);
      await stabilizeChatPage(page);

      // Open model selector
      const modelSelector = page.locator('[data-testid="model-select"], select').first();
      if (await modelSelector.isVisible()) {
        await modelSelector.click();
        await page.waitForTimeout(500);
      }

      await expect(page).toHaveScreenshot('chat-model-dropdown.png', {
        animations: 'disabled',
        maxDiffPixels: 6000,
      });
    });

    test('chat input focused state', async ({ page }, testInfo) => {
      onlyForProjects(testInfo, ['Desktop']);

      await page.goto('/chat');
      await page.waitForLoadState('networkidle');
      await waitForChatReady(page);
      await stabilizeChatPage(page);

      // Focus input
      const input = page.locator('textarea, input[type="text"]').first();
      await input.focus();
      await input.fill('Sample message text');

      await expect(page).toHaveScreenshot('chat-input-focused.png', {
        animations: 'disabled',
        maxDiffPixels: 6000,
      });
    });

    test('mobile chat layout', async ({ page }, testInfo) => {
      onlyForProjects(testInfo, ['Mobile']);

      await page.setViewportSize({ width: 390, height: 844 });
      await page.goto('/chat');
      await page.waitForLoadState('networkidle');
      await waitForChatReady(page);
      await stabilizeChatPage(page);

      await expect(page).toHaveScreenshot('chat-mobile.png', {
        animations: 'disabled',
        maxDiffPixels: 6000,
      });
    });
  });

  test.describe('Competition Page', () => {
    test('matches desktop baseline', async ({ page }, testInfo) => {
      onlyForProjects(testInfo, ['Desktop']);
      test.setTimeout(60000);

      await page.goto('/competition');
      await page.waitForLoadState('networkidle');
      // Wait for Mermaid diagrams to render
      await page.waitForSelector('.mermaid svg, svg.mermaid', { timeout: 10000 }).catch(() => {});
      await page.waitForTimeout(2000);

      await expect(page).toHaveScreenshot('competition-desktop.png', {
        fullPage: true,
        animations: 'disabled',
      });
    });

    test('matches mobile baseline', async ({ page }, testInfo) => {
      onlyForProjects(testInfo, ['Mobile']);
      test.setTimeout(60000);

      await page.setViewportSize({ width: 390, height: 844 });
      await page.goto('/competition');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForSelector('.mermaid svg', { timeout: 5000 }).catch(() => {});
      await page.waitForTimeout(1000);

      await expect(page).toHaveScreenshot('competition-mobile.png', {
        fullPage: true,
        animations: 'disabled',
      });
    });
  });

  test.describe('Marketplace Page', () => {
    test('matches desktop baseline', async ({ page }, testInfo) => {
      onlyForProjects(testInfo, ['Desktop']);

      await page.goto('/marketplace');
      await page.waitForLoadState('networkidle');

      await expect(page).toHaveScreenshot('marketplace-desktop.png', {
        fullPage: true,
        animations: 'disabled',
      });
    });
  });
});
