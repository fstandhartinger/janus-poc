import { test, expect } from '@playwright/test';
import {
  captureConsoleErrors,
  stubChatDependencies,
  waitForChatReady,
  waitForStreamingComplete,
} from './utils/helpers';

test.describe('Demo Prompts', () => {
  test.beforeEach(async ({ page }) => {
    await stubChatDependencies(page);
  });

  test.describe('Simple prompts - fast path routing', () => {
    test('simple-sky: explains why sky is blue', async ({ page }) => {
      await page.route('**/api/chat', async (route) => {
        const streamChunks = [
          'data: {"id":"chatcmpl-sky","object":"chat.completion.chunk","created":0,"model":"baseline","choices":[{"index":0,"delta":{"role":"assistant"},"finish_reason":null}]}',
          'data: {"id":"chatcmpl-sky","object":"chat.completion.chunk","created":0,"model":"baseline","choices":[{"index":0,"delta":{"content":"The sky appears blue due to Rayleigh scattering. Sunlight contains all colors, but blue wavelengths scatter more when hitting air molecules."},"finish_reason":null}]}',
          'data: [DONE]',
        ];
        await route.fulfill({
          status: 200,
          headers: { 'Content-Type': 'text/event-stream' },
          body: streamChunks.join('\n\n'),
        });
      });

      await page.goto('/chat');
      await waitForChatReady(page);

      const promptButton = page.getByTestId('demo-prompt-simple-sky');
      await expect(promptButton).toBeVisible();
      await promptButton.click();

      await waitForStreamingComplete(page);

      const assistantMessage = page.locator('[data-testid="assistant-message"]');
      await expect(assistantMessage.first()).toContainText(/blue|scattering/i);
    });

    test('simple-compare: compares Python and JavaScript', async ({ page }) => {
      await page.route('**/api/chat', async (route) => {
        const streamChunks = [
          'data: {"id":"chatcmpl-compare","object":"chat.completion.chunk","created":0,"model":"baseline","choices":[{"index":0,"delta":{"role":"assistant"},"finish_reason":null}]}',
          'data: {"id":"chatcmpl-compare","object":"chat.completion.chunk","created":0,"model":"baseline","choices":[{"index":0,"delta":{"content":"Python is known for readability and data science. JavaScript dominates web development with browser-native support."},"finish_reason":null}]}',
          'data: [DONE]',
        ];
        await route.fulfill({
          status: 200,
          headers: { 'Content-Type': 'text/event-stream' },
          body: streamChunks.join('\n\n'),
        });
      });

      await page.goto('/chat');
      await waitForChatReady(page);

      const promptButton = page.getByTestId('demo-prompt-simple-compare');
      await expect(promptButton).toBeVisible();
      await promptButton.click();

      await waitForStreamingComplete(page);

      const assistantMessage = page.locator('[data-testid="assistant-message"]');
      await expect(assistantMessage.first()).toContainText(/Python|JavaScript/i);
    });

    test('simple-translate: translates greeting', async ({ page }) => {
      await page.route('**/api/chat', async (route) => {
        const streamChunks = [
          'data: {"id":"chatcmpl-translate","object":"chat.completion.chunk","created":0,"model":"baseline","choices":[{"index":0,"delta":{"role":"assistant"},"finish_reason":null}]}',
          'data: {"id":"chatcmpl-translate","object":"chat.completion.chunk","created":0,"model":"baseline","choices":[{"index":0,"delta":{"content":"German: Hallo, wie geht es dir?\\nFrench: Bonjour, comment allez-vous?\\nJapanese: こんにちは、お元気ですか？"},"finish_reason":null}]}',
          'data: [DONE]',
        ];
        await route.fulfill({
          status: 200,
          headers: { 'Content-Type': 'text/event-stream' },
          body: streamChunks.join('\n\n'),
        });
      });

      await page.goto('/chat');
      await waitForChatReady(page);

      // simple-translate is in the "All Prompts" modal, not on the main page
      const seeMoreButton = page.getByTestId('see-more-prompts');
      await expect(seeMoreButton).toBeVisible();
      await seeMoreButton.click();
      await expect(page.getByTestId('all-prompts-modal')).toBeVisible();

      // Use the all-prompts-* test ID for items inside the modal
      const promptButton = page.getByTestId('all-prompts-simple-translate');
      await expect(promptButton).toBeVisible();
      await promptButton.click();

      await waitForStreamingComplete(page);

      const assistantMessage = page.locator('[data-testid="assistant-message"]');
      await expect(assistantMessage.first()).toContainText(/Hallo|Bonjour|こんにちは/i);
    });
  });

  test.describe('Multimodal prompts - image and audio generation', () => {
    test('multimodal-image-city: generates futuristic city image', async ({ page }) => {
      await page.route('**/api/chat', async (route) => {
        const streamChunks = [
          'data: {"id":"chatcmpl-image","object":"chat.completion.chunk","created":0,"model":"baseline","choices":[{"index":0,"delta":{"role":"assistant"},"finish_reason":null}]}',
          `data: {"id":"chatcmpl-image","object":"chat.completion.chunk","created":0,"model":"baseline","choices":[{"index":0,"delta":{"content":"I've generated a stunning image of a futuristic city.\\n\\n![Futuristic City](https://example.com/image.png)"},"finish_reason":null}]}`,
          'data: [DONE]',
        ];
        await route.fulfill({
          status: 200,
          headers: { 'Content-Type': 'text/event-stream' },
          body: streamChunks.join('\n\n'),
        });
      });

      await page.goto('/chat');
      await waitForChatReady(page);

      // Open the all prompts modal to find multimodal prompts
      const seeMoreButton = page.getByTestId('see-more-prompts');
      await expect(seeMoreButton).toBeVisible();
      await seeMoreButton.click();
      await expect(page.getByTestId('all-prompts-modal')).toBeVisible();

      // Use the all-prompts-* test ID for items inside the modal
      // Multimodal section is at the bottom of the modal, need to scroll to it
      const promptButton = page.getByTestId('all-prompts-multimodal-image-city');
      await promptButton.scrollIntoViewIfNeeded();
      await expect(promptButton).toBeVisible();
      await promptButton.click();

      await waitForStreamingComplete(page);

      const assistantMessage = page.locator('[data-testid="assistant-message"]');
      await expect(assistantMessage.first()).toContainText(/futuristic|city|image/i);
    });

    test('multimodal-poem-tts: writes and reads poem', async ({ page }) => {
      await page.route('**/api/chat', async (route) => {
        const streamChunks = [
          'data: {"id":"chatcmpl-poem","object":"chat.completion.chunk","created":0,"model":"baseline","choices":[{"index":0,"delta":{"role":"assistant"},"finish_reason":null}]}',
          `data: {"id":"chatcmpl-poem","object":"chat.completion.chunk","created":0,"model":"baseline","choices":[{"index":0,"delta":{"content":"Here's a poem about the ocean:\\n\\nWaves crash upon the shore,\\nWhispering secrets of the deep,\\nEternal tides forevermore."},"finish_reason":null}]}`,
          'data: [DONE]',
        ];
        await route.fulfill({
          status: 200,
          headers: { 'Content-Type': 'text/event-stream' },
          body: streamChunks.join('\n\n'),
        });
      });

      await page.goto('/chat');
      await waitForChatReady(page);

      const seeMoreButton = page.getByTestId('see-more-prompts');
      await seeMoreButton.click();
      await expect(page.getByTestId('all-prompts-modal')).toBeVisible();

      // Use the all-prompts-* test ID for items inside the modal
      // Multimodal section is at the bottom of the modal, need to scroll to it
      const promptButton = page.getByTestId('all-prompts-multimodal-poem-tts');
      await promptButton.scrollIntoViewIfNeeded();
      await expect(promptButton).toBeVisible();
      await promptButton.click();

      await waitForStreamingComplete(page);

      const assistantMessage = page.locator('[data-testid="assistant-message"]');
      await expect(assistantMessage.first()).toContainText(/ocean|waves|poem/i);
    });
  });

  test.describe('Research prompts - web search integration', () => {
    test('research-web-2026: searches for AI developments', async ({ page }) => {
      await page.route('**/api/chat', async (route) => {
        const streamChunks = [
          'data: {"id":"chatcmpl-research","object":"chat.completion.chunk","created":0,"model":"baseline","choices":[{"index":0,"delta":{"role":"assistant"},"finish_reason":null}]}',
          'data: {"id":"chatcmpl-research","object":"chat.completion.chunk","created":0,"model":"baseline","choices":[{"index":0,"delta":{"content":"# AI Developments in 2026\\n\\n## Key Trends\\n- Advanced reasoning models\\n- Improved code generation\\n- Multimodal capabilities\\n\\n**Sources:**\\n1. example.com/ai-news"},"finish_reason":null}]}',
          'data: [DONE]',
        ];
        await route.fulfill({
          status: 200,
          headers: { 'Content-Type': 'text/event-stream' },
          body: streamChunks.join('\n\n'),
        });
      });

      await page.goto('/chat');
      await waitForChatReady(page);

      const seeMoreButton = page.getByTestId('see-more-prompts');
      await seeMoreButton.click();
      await expect(page.getByTestId('all-prompts-modal')).toBeVisible();

      // Use the all-prompts-* test ID for items inside the modal
      const promptButton = page.getByTestId('all-prompts-research-web-2026');
      await expect(promptButton).toBeVisible();
      await promptButton.click();

      await waitForStreamingComplete(page);

      const assistantMessage = page.locator('[data-testid="assistant-message"]');
      await expect(assistantMessage.first()).toContainText(/AI|developments|2026/i);
    });
  });

  test.describe('Agentic prompts - complex task routing', () => {
    test('agentic-clone-summarize: clones and summarizes repo', async ({ page }) => {
      await page.route('**/api/chat', async (route) => {
        const streamChunks = [
          'data: {"id":"chatcmpl-agentic","object":"chat.completion.chunk","created":0,"model":"baseline","choices":[{"index":0,"delta":{"role":"assistant"},"finish_reason":null}]}',
          `data: {"id":"chatcmpl-agentic","object":"chat.completion.chunk","created":0,"model":"baseline","choices":[{"index":0,"delta":{"content":"I've cloned and analyzed the repository.\\n\\n## Summary\\nThe anthropic-cookbook contains examples and recipes for using Claude API."},"finish_reason":null}]}`,
          'data: [DONE]',
        ];
        await route.fulfill({
          status: 200,
          headers: { 'Content-Type': 'text/event-stream' },
          body: streamChunks.join('\n\n'),
        });
      });

      await page.goto('/chat');
      await waitForChatReady(page);

      const seeMoreButton = page.getByTestId('see-more-prompts');
      await seeMoreButton.click();
      await expect(page.getByTestId('all-prompts-modal')).toBeVisible();

      // Use the all-prompts-* test ID for items inside the modal
      const promptButton = page.getByTestId('all-prompts-agentic-clone-summarize');
      await expect(promptButton).toBeVisible();
      await promptButton.click();

      await waitForStreamingComplete(page);

      const assistantMessage = page.locator('[data-testid="assistant-message"]');
      await expect(assistantMessage.first()).toContainText(/clone|repository|summary/i);
    });
  });

  test.describe('All prompts modal', () => {
    test('opens and displays all 12 prompts', async ({ page }) => {
      await page.goto('/chat');
      await waitForChatReady(page);

      const seeMoreButton = page.getByTestId('see-more-prompts');
      await expect(seeMoreButton).toBeVisible();
      await seeMoreButton.click();

      const modal = page.getByTestId('all-prompts-modal');
      await expect(modal).toBeVisible();

      // Should have all 12 demo prompts (all-prompts-* prefix in the modal)
      const promptButtons = modal.locator('[data-testid^="all-prompts-"]');
      await expect(promptButtons).toHaveCount(12);
    });

    test('closes modal when Escape is pressed', async ({ page }) => {
      await page.goto('/chat');
      await waitForChatReady(page);

      const seeMoreButton = page.getByTestId('see-more-prompts');
      await seeMoreButton.click();

      const modal = page.getByTestId('all-prompts-modal');
      await expect(modal).toBeVisible();

      await page.keyboard.press('Escape');
      await expect(modal).toHaveCount(0);
    });

    test('closes modal when backdrop is clicked', async ({ page }) => {
      await page.goto('/chat');
      await waitForChatReady(page);

      const seeMoreButton = page.getByTestId('see-more-prompts');
      await seeMoreButton.click();

      const modal = page.getByTestId('all-prompts-modal');
      await expect(modal).toBeVisible();

      // Click backdrop (area outside modal content)
      await page.mouse.click(10, 10);
      await expect(modal).toHaveCount(0);
    });
  });

  test.describe('No console errors', () => {
    test('demo prompts render without errors', async ({ page }) => {
      const errors = captureConsoleErrors(page);
      await page.goto('/chat');
      await waitForChatReady(page);

      // Wait for prompts to render
      await page.waitForTimeout(1000);

      const filtered = errors.filter(
        (error) =>
          !error.includes('Failed to fetch service health') &&
          !error.includes('net::ERR_FAILED')
      );
      expect(filtered).toHaveLength(0);
    });
  });
});
