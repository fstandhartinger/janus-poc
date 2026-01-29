import { test, expect } from '@playwright/test';
import { mockChatStream, mockServiceHealth, onlyForProjects, stabilizeLandingHero } from './utils';

test.beforeEach(async ({ page }) => {
  await mockServiceHealth(page);
});

test.describe('Component Screenshots', () => {
  test.describe('Navigation', () => {
    test('header desktop', async ({ page }, testInfo) => {
      onlyForProjects(testInfo, ['Desktop']);

      await page.goto('/');
      await page.waitForLoadState('networkidle');
      await stabilizeLandingHero(page);

      const header = page.locator('header, nav').first();
      await expect(header).toHaveScreenshot('header-desktop.png');
    });

    test('header mobile with menu closed', async ({ page }, testInfo) => {
      onlyForProjects(testInfo, ['Mobile']);

      await page.setViewportSize({ width: 390, height: 844 });
      await page.goto('/');
      await page.waitForLoadState('networkidle');
      await stabilizeLandingHero(page);

      const header = page.locator('header, nav').first();
      await expect(header).toHaveScreenshot('header-mobile-closed.png');
    });

    test('header mobile with menu open', async ({ page }, testInfo) => {
      onlyForProjects(testInfo, ['Mobile']);

      await page.setViewportSize({ width: 390, height: 844 });
      await page.goto('/');
      await page.waitForLoadState('networkidle');
      await stabilizeLandingHero(page);

      // Open mobile menu
      const menuButton = page
        .locator('button[aria-label*="menu"], button[aria-label*="Menu"], .mobile-menu-button')
        .first();
      if (await menuButton.isVisible()) {
        await menuButton.click();
        await page.waitForTimeout(500);
      }

      await expect(page).toHaveScreenshot('header-mobile-open.png');
    });
  });

  test.describe('Chat Components', () => {
    test('chat input component', async ({ page }, testInfo) => {
      onlyForProjects(testInfo, ['Desktop']);

      await page.goto('/chat');
      await page.waitForLoadState('networkidle');

      const inputContainer = page.locator('.chat-input-container, form').last();
      await expect(inputContainer).toHaveScreenshot('chat-input.png');
    });

    test('chat message bubble - user', async ({ page }, testInfo) => {
      onlyForProjects(testInfo, ['Desktop']);

      await mockChatStream(page, { content: 'Hello from Janus' });
      await page.goto('/chat');
      await page.waitForLoadState('networkidle');

      // Send a message to create user bubble
      const input = page.locator('textarea').first();
      await input.fill('Hello');
      await page.keyboard.press('Enter');
      await page.waitForTimeout(1000);

      const userMessage = page
        .locator('[data-testid="user-message"], [data-role="user"], .user-message')
        .first();
      if (await userMessage.isVisible()) {
        await expect(userMessage).toHaveScreenshot('message-user.png');
      }
    });

    test('chat message bubble - assistant', async ({ page }, testInfo) => {
      onlyForProjects(testInfo, ['Desktop']);

      await mockChatStream(page, { content: 'Hi there!' });
      await page.goto('/chat');
      await page.waitForLoadState('networkidle');

      // Send a message and wait for response
      const input = page.locator('textarea').first();
      await input.fill('Say hi');
      await page.keyboard.press('Enter');

      // Wait for assistant response
      const assistantMessage = page
        .locator('[data-testid="assistant-message"], [data-role="assistant"], .assistant-message')
        .first();
      await assistantMessage.waitFor({ timeout: 30000 });

      await expect(assistantMessage).toHaveScreenshot('message-assistant.png', {
        mask: [page.locator('.timestamp, time')], // Mask dynamic timestamps
      });
    });

    test('chat sidebar', async ({ page }, testInfo) => {
      onlyForProjects(testInfo, ['Desktop']);

      await page.goto('/chat');
      await page.waitForLoadState('networkidle');

      const sidebar = page.locator('[data-testid="chat-sidebar"], .sidebar, aside').first();
      if (await sidebar.isVisible()) {
        await expect(sidebar).toHaveScreenshot('chat-sidebar.png');
      }
    });
  });

  test.describe('Buttons and Controls', () => {
    test('primary button', async ({ page }, testInfo) => {
      onlyForProjects(testInfo, ['Desktop']);

      await page.goto('/');
      await page.waitForLoadState('networkidle');
      await stabilizeLandingHero(page);

      const primaryButton = page.locator('a.bg-moss, button.bg-moss, .btn-primary').first();
      if (await primaryButton.isVisible()) {
        await expect(primaryButton).toHaveScreenshot('button-primary.png');
      }
    });

    test('send button', async ({ page }, testInfo) => {
      onlyForProjects(testInfo, ['Desktop']);

      await page.goto('/chat');
      await page.waitForLoadState('networkidle');

      const sendButton = page.locator('button[type="submit"]').first();
      await expect(sendButton).toHaveScreenshot('button-send.png');
    });
  });
});
