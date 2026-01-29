import { test, expect } from '@playwright/test';
import { waitForPageReady } from './utils/helpers';

test.describe('Marketplace Page', () => {
  test('filters components and opens detail view', async ({ page }) => {
    await page.goto('/marketplace');
    await waitForPageReady(page);

    await expect(
      page.getByRole('heading', { name: 'Discover the building blocks' })
    ).toBeVisible();

    await page.getByRole('button', { name: 'Research', exact: true }).click();
    await expect(page.getByRole('heading', { name: 'Web Search Agent' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Code Sandbox' })).toHaveCount(0);

    await page.getByRole('button', { name: /Web Search Agent/ }).click();
    await expect(page.getByRole('heading', { name: 'Integration Guide' })).toBeVisible();
  });

  test('page is responsive', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto('/marketplace');
    await waitForPageReady(page);

    const hasHorizontalScroll = await page.evaluate(
      () => document.body.scrollWidth > document.body.clientWidth
    );
    expect(hasHorizontalScroll).toBe(false);
  });
});
