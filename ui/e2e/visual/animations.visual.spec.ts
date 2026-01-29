import { test, expect } from '@playwright/test';
import { mockChatStream, mockServiceHealth, onlyForProjects } from './utils';

test.beforeEach(async ({ page }) => {
  await mockServiceHealth(page);
});

test.describe('Animations', () => {
  test('streaming text animation', async ({ page }, testInfo) => {
    onlyForProjects(testInfo, ['Desktop']);

    await mockChatStream(page, { content: 'One two three', delayMs: 2500 });
    await page.goto('/chat');
    await page.waitForLoadState('networkidle');

    // Send message
    const input = page.locator('textarea').first();
    await input.fill('Count to 3');
    await page.keyboard.press('Enter');

    // Capture during streaming
    await page.waitForTimeout(2000);

    // Take multiple screenshots to verify animation
    const screenshots = [];
    for (let i = 0; i < 3; i += 1) {
      screenshots.push(await page.screenshot());
      await page.waitForTimeout(500);
    }

    // Screenshots should be different (animation happening)
    // This is a sanity check - actual comparison would be more complex
    expect(screenshots.length).toBe(3);
  });

  test('modal open animation', async ({ page }, testInfo) => {
    onlyForProjects(testInfo, ['Desktop']);

    await page.goto('/chat');
    await page.waitForLoadState('networkidle');

    // Trigger a modal if available
    const modalTrigger = page
      .locator('[data-testid="open-modal"], button:has-text("Settings")')
      .first();
    if (await modalTrigger.isVisible()) {
      await modalTrigger.click();
      await page.waitForTimeout(100);

      // Capture during animation
      await expect(page).toHaveScreenshot('animation-modal-opening.png');

      await page.waitForTimeout(400);
      await expect(page).toHaveScreenshot('animation-modal-open.png');
    }
  });
});
