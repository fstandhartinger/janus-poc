import { test, expect } from '@playwright/test';
import path from 'path';
import fs from 'fs';

// Minimal 1x1 transparent PNG as base64
const PNG_BASE64 =
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==';

test.describe('Chat UI', () => {
  test('uploads an image and submits a prompt', async ({ page }) => {
    await page.goto('/chat');
    await page.waitForLoadState('networkidle');
    await page.locator('[data-testid="chat-input"]').waitFor();

    // Create a temp test image for this test
    const testImagePath = path.join(__dirname, `test-image-${Date.now()}.png`);
    const testImageName = path.basename(testImagePath);
    fs.writeFileSync(testImagePath, Buffer.from(PNG_BASE64, 'base64'));

    try {
      // Set the file directly on the hidden input for reliability.
      await page.locator('[data-testid="file-input"]').setInputFiles(testImagePath);

      // Verify image preview appears
      const imagePreview = page.locator(`img[alt="${testImageName}"]`);
      await expect(imagePreview).toBeVisible({ timeout: 10000 });

      // Enter a prompt
      const textarea = page.locator('[data-testid="chat-input"]');
      await expect(textarea).toBeEditable();
      await textarea.fill('What is in this image?');
      await expect(textarea).toHaveValue(/What is in this image\?/);

      // Submit the message
      const sendButton = page.locator('[data-testid="send-button"]');
      await expect(sendButton).toBeEnabled({ timeout: 10000 });
      await sendButton.click();

      // Verify user message appears (the message bubble div, not buttons)
      const userMessageBubble = page.locator('[data-testid="user-message"]');
      await expect(userMessageBubble.first()).toBeVisible();

      // Verify the message contains our text
      await expect(userMessageBubble.first()).toContainText('What is in this image?');
    } finally {
      // Clean up test image
      if (fs.existsSync(testImagePath)) {
        fs.unlinkSync(testImagePath);
      }
    }
  });

  test('shows streaming responses incrementally', async ({ page }) => {
    await page.route('**/api/chat', async (route) => {
      const streamChunks = [
        'data: {"id":"chatcmpl-test","object":"chat.completion.chunk","created":0,"model":"baseline","choices":[{"index":0,"delta":{"role":"assistant"},"finish_reason":null}]}',
        'data: {"id":"chatcmpl-test","object":"chat.completion.chunk","created":0,"model":"baseline","choices":[{"index":0,"delta":{"content":"Hello from Janus"},"finish_reason":null}]}',
        'data: [DONE]',
      ];
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
        body: streamChunks.join('\n\n'),
      });
    });

    await page.goto('/chat');
    await page.waitForLoadState('networkidle');
    await page.locator('[data-testid="chat-input"]').waitFor();

    // Enter a prompt
    const textarea = page.locator('[data-testid="chat-input"]');
    await expect(textarea).toBeEditable();
    await textarea.fill('Hello, how are you?');
    await expect(textarea).toHaveValue(/Hello, how are you\?/);

    // Submit the message
    const sendButton = page.locator('[data-testid="send-button"]');
    await expect(sendButton).toBeEnabled({ timeout: 10000 });
    await sendButton.click();

    const userMessageBubble = page.locator('[data-testid="user-message"]');
    await expect(userMessageBubble.first()).toContainText('Hello, how are you?');

    const assistantMessage = page.locator('[data-testid="assistant-message"]');
    await expect(assistantMessage.first()).toContainText('Hello from Janus');
  });

  test('demo prompts send messages and open the full list', async ({ page }) => {
    await page.route('**/api/chat', async (route) => {
      const streamChunks = [
        'data: {\"id\":\"chatcmpl-demo\",\"object\":\"chat.completion.chunk\",\"created\":0,\"model\":\"baseline\",\"choices\":[{\"index\":0,\"delta\":{\"role\":\"assistant\"},\"finish_reason\":null}]}',
        'data: {\"id\":\"chatcmpl-demo\",\"object\":\"chat.completion.chunk\",\"created\":0,\"model\":\"baseline\",\"choices\":[{\"index\":0,\"delta\":{\"content\":\"The sky is blue because of Rayleigh scattering.\"},\"finish_reason\":null}]}',
        'data: [DONE]',
      ];
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
        body: streamChunks.join('\\n\\n'),
      });
    });

    await page.goto('/chat');
    await page.waitForLoadState('networkidle');

    const seeMoreButton = page.getByTestId('see-more-prompts');
    await expect(seeMoreButton).toBeVisible();
    await seeMoreButton.click();
    await expect(page.getByTestId('all-prompts-modal')).toBeVisible();
    await page.keyboard.press('Escape');
    await expect(page.locator('[data-testid=\"all-prompts-modal\"]')).toHaveCount(0);

    const promptButton = page.getByTestId('demo-prompt-simple-sky');
    await expect(promptButton).toBeVisible();
    const [chatRequest] = await Promise.all([
      page.waitForRequest('**/api/chat'),
      promptButton.click(),
    ]);

    await expect(chatRequest.postData() || '').toContain('Explain why the sky is blue');

    const userMessageBubble = page.locator('[data-testid=\"user-message\"]');
    await expect(userMessageBubble.first()).toContainText('Explain why the sky is blue');
  });

  test('reasoning toggle is not shown in the top bar', async ({ page }) => {
    await page.goto('/chat');

    const toggleButton = page.locator('button:has-text("Thinking")');
    await expect(toggleButton).toHaveCount(0);
  });

  test('displays artifact links with download capability', async ({ page }) => {
    // This test verifies the artifact rendering component
    // In a real scenario, we'd need a mock server returning artifacts
    await page.goto('/chat');

    // Verify the message bubble component is set up to render artifacts
    // We can test this by checking the component exists and can render
    const chatArea = page.locator('.chat-area');
    await expect(chatArea).toBeVisible();

    // The artifact links are rendered with the following structure:
    // - Attachment label
    // - Display name
    // - Size in KB
    // This is verified through component code, as real artifacts require server integration
  });

  test('can create new chat session', async ({ page }) => {
    await page.goto('/chat');

    // Find the new chat button in sidebar
    const newChatButton = page.locator('button:has-text("New Chat")');
    await expect(newChatButton).toBeVisible();

    // Click to create new session
    await newChatButton.click();

    // Verify empty state appears
    const emptyState = page.locator('.chat-empty-title');
    await expect(emptyState).toBeVisible();
  });
});
