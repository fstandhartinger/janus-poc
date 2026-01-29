import { test, expect } from '@playwright/test';
import { captureConsoleErrors, waitForPageReady } from './utils/helpers';

test.describe('Competition Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.route('**/api/arena/leaderboard**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          { model: 'baseline-cli-agent', elo: 1200, wins: 1, losses: 0, ties: 0, matches: 1 },
        ]),
      });
    });
  });

  test('renders without console errors', async ({ page }) => {
    const errors = captureConsoleErrors(page);
    await page.goto('/competition');
    await waitForPageReady(page);
    await page.waitForTimeout(2000);
    expect(errors).toHaveLength(0);
  });

  test('shows leaderboard and FAQ content', async ({ page }) => {
    await page.goto('/competition');
    await waitForPageReady(page);

    await expect(page.locator('text=Rodeo Rankings')).toBeVisible();
    await expect(
      page.locator('#arena-leaderboard').getByRole('cell', { name: 'baseline-cli-agent' })
    ).toBeVisible();
    await expect(
      page.getByRole('heading', { name: 'Five Steps to the Janus Rodeo' })
    ).toBeVisible();
    await expect(
      page.getByRole('heading', { name: 'The Prize Pool', level: 2 })
    ).toBeVisible();
    await expect(
      page.getByRole('heading', { name: 'Component Marketplace', level: 2 })
    ).toBeVisible();

    await expect(
      page.getByRole('heading', { name: 'Frequently Asked Questions' })
    ).toBeVisible();
    const faqSection = page.locator('#faq');
    await faqSection.getByRole('button', { name: 'General' }).click();
    await expect(
      faqSection.getByRole('heading', {
        name: 'What is the Janus Competition?',
        level: 4,
      })
    ).toBeVisible();
    await faqSection
      .getByRole('button', { name: 'What is the Janus Competition?' })
      .click();
    await expect(faqSection.locator('text=OpenAI-compatible')).toBeVisible();
  });

  test('Mermaid diagrams render', async ({ page }) => {
    await page.goto('/competition');
    await waitForPageReady(page);

    const diagrams = page.locator('.mermaid-container svg');
    await expect(diagrams.first()).toBeVisible();
  });

  test('page is responsive', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto('/competition');
    await waitForPageReady(page);

    const { scrollWidth, clientWidth } = await page.evaluate(() => ({
      scrollWidth: document.documentElement.scrollWidth,
      clientWidth: document.documentElement.clientWidth,
    }));
    expect(scrollWidth - clientWidth).toBeLessThanOrEqual(80);
  });
});
