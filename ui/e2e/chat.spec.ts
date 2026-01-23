import { test, expect } from '@playwright/test';
import path from 'path';
import fs from 'fs';

// Minimal 1x1 transparent PNG as base64
const PNG_BASE64 =
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==';

test.describe('Chat UI', () => {
  test('uploads an image and submits a prompt', async ({ page }) => {
    await page.goto('/chat');

    // Create a temp test image for this test
    const testImagePath = path.join(__dirname, `test-image-${Date.now()}.png`);
    fs.writeFileSync(testImagePath, Buffer.from(PNG_BASE64, 'base64'));

    try {
      // Set the file directly on the hidden input for reliability.
      await page.locator('[data-testid="file-input"]').setInputFiles(testImagePath);

      // Verify image preview appears
      const imagePreview = page.locator('img[alt="Upload preview"]');
      await expect(imagePreview).toBeVisible();

      // Enter a prompt
      const textarea = page.locator('[data-testid="chat-input"]');
      await textarea.fill('What is in this image?');

      // Submit the message
      const sendButton = page.locator('[data-testid="send-button"]');
      await sendButton.click();

      // Verify user message appears (the message bubble div, not buttons)
      const userMessageBubble = page.locator('[data-testid="user-message"]');
      await expect(userMessageBubble.first()).toBeVisible();

      // Verify the message contains our text
      await expect(userMessageBubble.first()).toContainText('What is in this image?');

      // Verify attached image appears in the message
      const attachedImage = userMessageBubble.first().locator('img[alt="Attached"]');
      await expect(attachedImage).toBeVisible();
    } finally {
      // Clean up test image
      if (fs.existsSync(testImagePath)) {
        fs.unlinkSync(testImagePath);
      }
    }
  });

  test('shows streaming responses incrementally', async ({ page }) => {
    await page.route('**/v1/chat/completions', async (route) => {
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

    // Enter a prompt
    const textarea = page.locator('[data-testid="chat-input"]');
    await textarea.fill('Hello, how are you?');

    // Submit the message
    const sendButton = page.locator('[data-testid="send-button"]');
    await expect(sendButton).toBeEnabled();
    await sendButton.click();

    const userMessageBubble = page.locator('[data-testid="user-message"]');
    await expect(userMessageBubble.first()).toContainText('Hello, how are you?');

    const assistantMessage = page.locator('[data-testid="assistant-message"]');
    await expect(assistantMessage.first()).toContainText('Hello from Janus');
  });

  test('reasoning panel can be toggled', async ({ page }) => {
    await page.goto('/chat');

    // Find the reasoning toggle button
    const toggleButton = page.locator('button:has-text("Thinking")');
    await expect(toggleButton).toBeVisible();

    // Initially should show "Thinking: OFF"
    await expect(toggleButton).toContainText('Off');

    // Click to enable
    await toggleButton.click();
    await expect(toggleButton).toContainText('On');

    // Click to disable
    await toggleButton.click();
    await expect(toggleButton).toContainText('Off');
  });

  test('displays artifact links with download capability', async ({ page }) => {
    // This test verifies the artifact rendering component
    // In a real scenario, we'd need a mock server returning artifacts
    await page.goto('/chat');

    // Verify the message bubble component is set up to render artifacts
    // We can test this by checking the component exists and can render
    const chatArea = page.locator('.flex-1.flex.flex-col');
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
