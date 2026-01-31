import { test, expect, Page } from '@playwright/test';
import {
  setChatInputValue,
  stubChatDependencies,
  waitForChatReady,
  waitForStreamingComplete,
} from './utils/helpers';

async function enableDebugMode(page: Page) {
  const debugToggle = page.locator('button[aria-label*="Debug mode"]');
  if (await debugToggle.isVisible()) {
    await debugToggle.scrollIntoViewIfNeeded();
    await debugToggle.click();
  } else {
    const overflowToggle = page.locator('button[aria-label="More options"]');
    await overflowToggle.click();
    const debugMenuItem = page.getByRole('menuitem', { name: /debug mode/i });
    await debugMenuItem.click();
  }
  await expect(debugToggle).toHaveAttribute('aria-pressed', 'true');
}

test.describe('Debug Mode', () => {
  test.beforeEach(async ({ page }) => {
    await stubChatDependencies(page);
  });

  test('debug panel opens and closes', async ({ page }) => {
    await page.goto('/chat');
    await waitForChatReady(page);

    await enableDebugMode(page);

    const debugPanel = page.locator('[data-testid="debug-panel"]');
    await expect(debugPanel).toBeVisible();
    await expect(debugPanel.locator('.mermaid-container')).toBeVisible({ timeout: 10000 });

    await debugPanel.locator('button[aria-label="Close debug panel"]').click();
    await expect(debugPanel).toHaveCount(0);
  });

  test('debug panel shows event log during fast path request', async ({ page }) => {
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

    await enableDebugMode(page);

    const input = page.locator('[data-testid="chat-input"]');
    await setChatInputValue(page, 'Show debug data');
    await page.keyboard.press('Enter');

    await waitForStreamingComplete(page);

    const debugPanel = page.locator('[data-testid="debug-panel"]');
    await expect(debugPanel).toBeVisible();
    await expect(debugPanel.locator('.debug-log-row')).toHaveCount(1);
  });

  test('debug panel shows agent path events with tools', async ({ page }) => {
    await page.route('**/api/chat', async (route) => {
      const streamChunks = [
        'data: {"id":"chatcmpl-agent","object":"chat.completion.chunk","created":0,"model":"baseline","choices":[{"index":0,"delta":{"role":"assistant"},"finish_reason":null}]}',
        'data: {"id":"chatcmpl-agent","object":"chat.completion.chunk","created":0,"model":"baseline","choices":[{"index":0,"delta":{"content":"Agent response"},"finish_reason":null}]}',
        'data: [DONE]',
      ];
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/event-stream', 'x-request-id': 'agent-request' },
        body: streamChunks.join('\n\n'),
      });
    });

    await page.route('**/api/debug/stream/**', async (route) => {
      const debugEvents = [
        {
          request_id: 'agent-request',
          timestamp: new Date().toISOString(),
          type: 'complexity_check_complete',
          step: 'ROUTING',
          message: 'Complex task detected',
        },
        {
          request_id: 'agent-request',
          timestamp: new Date(Date.now() + 100).toISOString(),
          type: 'agent_path_start',
          step: 'SANDY',
          message: 'Starting agent path',
        },
        {
          request_id: 'agent-request',
          timestamp: new Date(Date.now() + 200).toISOString(),
          type: 'tool_call_start',
          step: 'TOOLS',
          message: 'Calling web search tool',
        },
      ];
      const body = debugEvents.map(e => `data: ${JSON.stringify(e)}`).join('\n\n');
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
        body: body + '\n\n',
      });
    });

    await page.goto('/chat');
    await waitForChatReady(page);

    await enableDebugMode(page);

    await setChatInputValue(page, 'Search the web for latest news');
    await page.keyboard.press('Enter');

    await waitForStreamingComplete(page);

    const debugPanel = page.locator('[data-testid="debug-panel"]');
    await expect(debugPanel).toBeVisible();
    // Should have multiple debug events logged
    await expect(debugPanel.locator('.debug-log-row')).toHaveCount(3);
  });
});
