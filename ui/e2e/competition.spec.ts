import { test, expect } from '@playwright/test';

test.describe('Competition Page', () => {
  test('shows leaderboard and FAQ interactions', async ({ page }) => {
    await page.goto('/competition');

    await expect(page.locator('text=Rodeo Rankings')).toBeVisible();
    await expect(page.getByRole('table').getByText('baseline-v1')).toBeVisible();

    const faqButton = page.locator('button:has-text("How do I stream intermediate steps?")');
    await expect(faqButton).toBeVisible();
    await faqButton.click();

    await expect(
      page.locator('text=Stream reasoning_content in your SSE chunks')
    ).toBeVisible();
  });
});
