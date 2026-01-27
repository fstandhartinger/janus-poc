import { test, expect } from '@playwright/test';
import fs from 'fs';
import path from 'path';

const viewports = [
  { name: 'desktop', width: 1920, height: 1080 },
  { name: 'tablet', width: 768, height: 1024 },
  { name: 'mobile', width: 375, height: 812 },
];

const screenshotDir = path.join('playwright-report', 'hero-video');

test.beforeAll(() => {
  fs.mkdirSync(screenshotDir, { recursive: true });
});

test.describe('Hero Video', () => {
  test.setTimeout(60000);
  for (const viewport of viewports) {
    test(`renders hero video sequence on ${viewport.name}`, async ({ page }) => {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      await page.goto('/');

      await expect(page.locator('.hero-video-container')).toBeVisible();
      await expect(page.locator('.hero-video-poster')).toBeVisible();

      await page.screenshot({
        path: path.join(screenshotDir, `hero-initial-${viewport.name}.png`),
        fullPage: false,
      });

      await page.waitForTimeout(2000);
      await page.screenshot({
        path: path.join(screenshotDir, `hero-playing-${viewport.name}.png`),
        fullPage: false,
      });

      await expect(page.locator('.hero-video-canvas')).toBeVisible({ timeout: 20000 });
      await page.screenshot({
        path: path.join(screenshotDir, `hero-canvas-${viewport.name}.png`),
        fullPage: false,
      });

      await page.evaluate(() => window.scrollTo(0, 500));
      await page.waitForTimeout(500);
      await page.screenshot({
        path: path.join(screenshotDir, `hero-scroll-500-${viewport.name}.png`),
        fullPage: false,
      });

      await page.evaluate(() => window.scrollTo(0, 1000));
      await page.waitForTimeout(500);
      await page.screenshot({
        path: path.join(screenshotDir, `hero-scroll-1000-${viewport.name}.png`),
        fullPage: false,
      });

      await page.evaluate(() => window.scrollTo(0, 1500));
      await page.waitForTimeout(500);
      await page.screenshot({
        path: path.join(screenshotDir, `hero-scroll-1500-${viewport.name}.png`),
        fullPage: false,
      });

      const posterBox = await page.locator('.hero-video-poster').boundingBox();
      const videoBox = await page.locator('.hero-video-element').boundingBox();

      if (posterBox && videoBox) {
        expect(Math.abs(posterBox.x - videoBox.x)).toBeLessThan(5);
        expect(Math.abs(posterBox.y - videoBox.y)).toBeLessThan(5);
        expect(Math.abs(posterBox.width - videoBox.width)).toBeLessThan(10);
        expect(Math.abs(posterBox.height - videoBox.height)).toBeLessThan(10);
      }
    });
  }

  test('video plays without audio', async ({ page }) => {
    await page.goto('/');

    const video = page.locator('.hero-video-element');
    await expect(video).toHaveAttribute('muted', '');

    const isMuted = await video.evaluate((el) => (el as HTMLVideoElement).muted);
    expect(isMuted).toBe(true);
  });

  test('no console errors during playback', async ({ page }) => {
    const errors: string[] = [];

    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });

    await page.goto('/');
    await page.waitForTimeout(12000);

    const significantErrors = errors.filter(
      (error) => !error.includes('favicon') && !error.includes('autoplay')
    );

    expect(significantErrors).toHaveLength(0);
  });
});
