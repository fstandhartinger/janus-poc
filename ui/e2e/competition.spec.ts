import { test, expect } from '@playwright/test';

test.describe('Competition Page', () => {
  test('shows leaderboard and FAQ content', async ({ page }) => {
    await page.goto('/competition');

    await expect(page.locator('text=Rodeo Rankings')).toBeVisible();
    await expect(page.getByRole('table').getByText('baseline-cli-agent')).toBeVisible();
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
});
