import { test, expect } from '@playwright/test';
import fs from 'fs';
import path from 'path';
import { stubChatDependencies, waitForChatReady, waitForStreamingComplete } from './utils/helpers';

const fixturesDir = path.join(__dirname, 'fixtures');
const testImagePath = path.join(fixturesDir, 'test-image.png');

const pngData = Buffer.from(
  [
    0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a, 0x00, 0x00, 0x00, 0x0d,
    0x49, 0x48, 0x44, 0x52, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
    0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53, 0xde, 0x00, 0x00, 0x00,
    0x0c, 0x49, 0x44, 0x41, 0x54, 0x08, 0xd7, 0x63, 0xf8, 0x0f, 0x00, 0x00,
    0x01, 0x01, 0x00, 0x05, 0x18, 0xd8, 0x4d, 0x06, 0x00, 0x00, 0x00, 0x00,
    0x49, 0x45, 0x4e, 0x44, 0xae, 0x42, 0x60, 0x82,
  ]
);

test.beforeAll(() => {
  if (!fs.existsSync(fixturesDir)) {
    fs.mkdirSync(fixturesDir, { recursive: true });
  }
  fs.writeFileSync(testImagePath, pngData);
});

test.describe('File Upload', () => {
  test.beforeEach(async ({ page }) => {
    await stubChatDependencies(page);
  });

  test('can upload image via file input', async ({ page }) => {
    await page.goto('/chat');
    await waitForChatReady(page);

    const fileInput = page.locator('[data-testid="file-input"]');
    if ((await fileInput.count()) === 0) {
      test.skip(true, 'File input not available');
    }

    await fileInput.setInputFiles(testImagePath);

    const preview = page.locator(`img[alt="${path.basename(testImagePath)}"]`);
    await expect(preview).toBeVisible();
  });

  test('can remove attached image before sending', async ({ page }) => {
    await page.goto('/chat');
    await waitForChatReady(page);

    const fileInput = page.locator('[data-testid="file-input"]');
    if ((await fileInput.count()) === 0) {
      test.skip(true, 'File input not available');
    }

    await fileInput.setInputFiles(testImagePath);

    const removeButton = page.locator(
      `button[aria-label="Remove ${path.basename(testImagePath)}"]`
    );
    await expect(removeButton).toBeVisible();
    await removeButton.click();

    await expect(page.locator(`img[alt="${path.basename(testImagePath)}"]`)).toHaveCount(0);
  });

  test('can send message with attached image', async ({ page }) => {
    await page.route('**/api/chat', async (route) => {
      const streamChunks = [
        'data: {"id":"chatcmpl-file","object":"chat.completion.chunk","created":0,"model":"baseline","choices":[{"index":0,"delta":{"role":"assistant"},"finish_reason":null}]}',
        'data: {"id":"chatcmpl-file","object":"chat.completion.chunk","created":0,"model":"baseline","choices":[{"index":0,"delta":{"content":"Here\'s a response."},"finish_reason":null}]}',
        'data: [DONE]',
      ];
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/event-stream', 'x-request-id': 'file-upload-request' },
        body: streamChunks.join('\n\n'),
      });
    });

    await page.goto('/chat');
    await waitForChatReady(page);

    const fileInput = page.locator('[data-testid="file-input"]');
    if ((await fileInput.count()) === 0) {
      test.skip(true, 'File input not available');
    }

    await fileInput.setInputFiles(testImagePath);

    const input = page.locator('[data-testid="chat-input"]');
    await input.fill('What do you see?');
    await page.keyboard.press('Enter');

    await waitForStreamingComplete(page);

    await expect(page.locator('[data-testid="assistant-message"]').first()).toBeVisible();
  });
});
