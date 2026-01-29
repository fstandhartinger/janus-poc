import { test, expect } from '@playwright/test';
import {
  setChatInputValue,
  stubChatDependencies,
  waitForChatReady,
  waitForStreamingComplete,
} from './utils/helpers';

test.describe('Debug Mode', () => {
  test.beforeEach(async ({ page }) => {
    await stubChatDependencies(page);
  });

  test('debug panel opens and closes', async ({ page }) => {
    await page.goto('/chat');
    await waitForChatReady(page);

    const debugToggle = page.locator('button[aria-label*="Debug mode"]');
    await expect(debugToggle).toBeVisible();
    await debugToggle.click();

    const debugPanel = page.locator('[data-testid="debug-panel"]');
    await expect(debugPanel).toBeVisible();
    await expect(debugPanel.locator('.mermaid-container')).toBeVisible({ timeout: 10000 });

    await debugPanel.locator('button[aria-label="Close debug panel"]').click();
    await expect(debugPanel).toHaveCount(0);
  });

  test('debug panel shows event log during request', async ({ page }) => {
    await page.route('**/api/chat', async (route) => {
      const streamChunks = [
        'data: {"id":"chatcmpl-debug","object":"chat.completion.chunk","created":0,"model":"baseline","choices":[{"index":0,"delta":{"role":"assistant"},"finish_reason":null}]}',
        'data: {"id":"chatcmpl-debug","object":"chat.completion.chunk","created":0,"model":"baseline","choices":[{"index":0,"delta":{"content":"Debug response"},"finish_reason":null}]}',
        'data: [DONE]',
      ];
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/event-stream', 'x-request-id': 'debug-request' },
        body: streamChunks.join('\n\n'),
      });
    });

    await page.route('**/api/debug/stream/**', async (route) => {
      const debugEvent = {
        request_id: 'debug-request',
        timestamp: new Date().toISOString(),
        type: 'fast_path_start',
        step: 'FAST_LLM',
        message: 'Routing to fast path',
      };
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
        body: `data: ${JSON.stringify(debugEvent)}\n\n`,
      });
    });

    await page.goto('/chat');
    await waitForChatReady(page);

    const debugToggle = page.locator('button[aria-label*="Debug mode"]');
    await debugToggle.click();

    const input = page.locator('[data-testid="chat-input"]');
    await setChatInputValue(page, 'Show debug data');
    await page.keyboard.press('Enter');

    await waitForStreamingComplete(page);

    const debugPanel = page.locator('[data-testid="debug-panel"]');
    await expect(debugPanel).toBeVisible();
    await expect(debugPanel.locator('.debug-log-row')).toHaveCount(1);
  });
});
