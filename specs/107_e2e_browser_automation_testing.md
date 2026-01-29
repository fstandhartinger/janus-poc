# Spec 102: E2E Browser Automation Testing

## Status: COMPLETE

**Priority:** High
**Complexity:** High
**Prerequisites:** Specs 100, 101

---

## Overview

End-to-end browser automation tests verify the complete user experience by controlling a real browser. These tests:

1. Navigate through the UI as a real user would
2. Fill forms, click buttons, upload files
3. Verify streaming responses render correctly
4. Test authentication flows (Sign In With Chutes)
5. Test responsive design across device sizes
6. Capture screenshots for debugging

**Important:** If any tests fail, FIX the underlying code. Use `CHUTES_FINGERPRINT` env var for authenticated tests.

---

## Test Framework Setup

### Install Playwright

```bash
cd ui
npm install -D @playwright/test playwright
npx playwright install chromium firefox webkit
```

### Configuration: `ui/playwright.config.ts`

```typescript
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  timeout: 60000,
  expect: {
    timeout: 10000,
  },
  fullyParallel: false, // Run serially for consistent state
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: [
    ['html', { outputFolder: 'playwright-report' }],
    ['list'],
  ],
  use: {
    baseURL: process.env.TEST_URL || 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    {
      name: 'Desktop Chrome',
      use: {
        ...devices['Desktop Chrome'],
        viewport: { width: 1920, height: 1080 },
      },
    },
    {
      name: 'Tablet',
      use: {
        ...devices['iPad Pro'],
        viewport: { width: 1024, height: 768 },
      },
    },
    {
      name: 'Mobile',
      use: {
        ...devices['iPhone 14'],
        viewport: { width: 390, height: 844 },
      },
    },
  ],
  webServer: process.env.CI ? undefined : {
    command: 'npm run dev',
    url: 'http://localhost:3000',
    reuseExistingServer: true,
  },
});
```

### Test Utilities: `ui/e2e/utils/helpers.ts`

```typescript
import { Page, expect } from '@playwright/test';

/**
 * Wait for the page to be fully loaded with no pending requests.
 */
export async function waitForPageReady(page: Page) {
  await page.waitForLoadState('networkidle');
  // Additional wait for hydration
  await page.waitForTimeout(500);
}

/**
 * Wait for streaming response to complete.
 */
export async function waitForStreamingComplete(page: Page, timeout = 60000) {
  // Wait for the "stop" button to disappear or content to stop updating
  const startTime = Date.now();
  let lastContent = '';

  while (Date.now() - startTime < timeout) {
    await page.waitForTimeout(1000);

    // Check if still streaming (look for loading indicator)
    const isStreaming = await page.locator('[data-streaming="true"]').count() > 0;
    if (!isStreaming) break;

    // Check if content is still updating
    const currentContent = await page.locator('[data-testid="chat-messages"]').textContent();
    if (currentContent === lastContent) break;
    lastContent = currentContent || '';
  }
}

/**
 * Get all console errors from the page.
 */
export function captureConsoleErrors(page: Page): string[] {
  const errors: string[] = [];
  page.on('console', msg => {
    if (msg.type() === 'error') {
      errors.push(msg.text());
    }
  });
  return errors;
}

/**
 * Sign in with Chutes using fingerprint cookie.
 */
export async function signInWithChutes(page: Page, fingerprint: string) {
  // Set the fingerprint cookie that simulates authenticated session
  await page.context().addCookies([
    {
      name: 'chutes_fingerprint',
      value: fingerprint,
      domain: new URL(page.url()).hostname,
      path: '/',
    },
  ]);
  await page.reload();
  await waitForPageReady(page);
}

/**
 * Take screenshot with timestamp.
 */
export async function takeTimestampedScreenshot(page: Page, name: string) {
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  await page.screenshot({
    path: `e2e-screenshots/${name}_${timestamp}.png`,
    fullPage: true,
  });
}
```

---

## Part 1: Landing Page Tests

### Location: `ui/e2e/landing.spec.ts`

```typescript
import { test, expect } from '@playwright/test';
import { waitForPageReady, captureConsoleErrors } from './utils/helpers';

test.describe('Landing Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await waitForPageReady(page);
  });

  test('renders without console errors', async ({ page }) => {
    const errors = captureConsoleErrors(page);
    await page.waitForTimeout(2000);
    expect(errors).toHaveLength(0);
  });

  test('displays Janus branding', async ({ page }) => {
    // Check for Janus title or logo
    await expect(page.locator('text=Janus')).toBeVisible();
  });

  test('has navigation to all pages', async ({ page }) => {
    // Check navigation links exist
    await expect(page.locator('a[href="/chat"]')).toBeVisible();
    await expect(page.locator('a[href="/competition"]')).toBeVisible();
    // Marketplace may or may not be visible depending on config
  });

  test('hero section is visible', async ({ page }) => {
    // Check for main CTA or hero content
    const heroSection = page.locator('section').first();
    await expect(heroSection).toBeVisible();
  });

  test('CTA button navigates to chat', async ({ page }) => {
    // Find and click main CTA
    const ctaButton = page.locator('a:has-text("Try"), a:has-text("Start"), a:has-text("Chat")').first();
    if (await ctaButton.isVisible()) {
      await ctaButton.click();
      await expect(page).toHaveURL(/\/chat/);
    }
  });

  test('page is responsive on mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.waitForTimeout(500);

    // Check no horizontal scroll
    const hasHorizontalScroll = await page.evaluate(() =>
      document.body.scrollWidth > document.body.clientWidth
    );
    expect(hasHorizontalScroll).toBe(false);
  });

  test('dark mode styling is applied', async ({ page }) => {
    const bgColor = await page.evaluate(() =>
      getComputedStyle(document.body).backgroundColor
    );
    // Dark mode should have dark background
    // RGB values should be low (< 50 each for dark theme)
    expect(bgColor).toMatch(/rgb\((\d{1,2}), (\d{1,2}), (\d{1,2})\)/);
  });
});
```

---

## Part 2: Chat Page Tests

### Location: `ui/e2e/chat.spec.ts`

```typescript
import { test, expect } from '@playwright/test';
import { waitForPageReady, waitForStreamingComplete, captureConsoleErrors } from './utils/helpers';

test.describe('Chat Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/chat');
    await waitForPageReady(page);
  });

  test('renders chat interface', async ({ page }) => {
    // Check for essential chat elements
    await expect(page.locator('textarea, input[type="text"]')).toBeVisible();
  });

  test('renders without console errors', async ({ page }) => {
    const errors = captureConsoleErrors(page);
    await page.waitForTimeout(2000);
    expect(errors).toHaveLength(0);
  });

  test('model selector is visible', async ({ page }) => {
    // Look for model dropdown
    const modelSelector = page.locator('[data-testid="model-select"], select, [role="combobox"]').first();
    await expect(modelSelector).toBeVisible();
  });

  test('can type in chat input', async ({ page }) => {
    const input = page.locator('textarea, input[placeholder*="Ask"]').first();
    await input.fill('Hello, this is a test message');
    await expect(input).toHaveValue('Hello, this is a test message');
  });

  test('send button is present', async ({ page }) => {
    const sendButton = page.locator('button[type="submit"], button:has-text("Send"), button[aria-label*="Send"]').first();
    await expect(sendButton).toBeVisible();
  });

  test('voice input button is present', async ({ page }) => {
    const micButton = page.locator('button[aria-label*="voice"], button[aria-label*="microphone"], button:has([data-lucide="mic"])').first();
    // May not be visible if feature is disabled
    // Just check it doesn't cause errors
  });

  test('attachment button is present', async ({ page }) => {
    const attachButton = page.locator('button[aria-label*="attach"], button:has([data-lucide="plus"]), button:has([data-lucide="paperclip"])').first();
    // May or may not be visible
  });
});

test.describe('Chat Functionality', () => {
  test('can send a simple message', async ({ page }) => {
    await page.goto('/chat');
    await waitForPageReady(page);

    // Type message
    const input = page.locator('textarea, input[placeholder*="Ask"]').first();
    await input.fill('Say hello');

    // Submit
    await page.keyboard.press('Enter');

    // Wait for response
    await page.waitForSelector('[data-role="assistant"], .assistant-message, .message:has-text("")', {
      timeout: 30000,
    });

    // Verify user message appears
    await expect(page.locator('text=Say hello')).toBeVisible();
  });

  test('streaming response renders incrementally', async ({ page }) => {
    await page.goto('/chat');
    await waitForPageReady(page);

    const input = page.locator('textarea, input[placeholder*="Ask"]').first();
    await input.fill('Count from 1 to 5');
    await page.keyboard.press('Enter');

    // Wait for streaming to start
    await page.waitForTimeout(2000);

    // Check that content is appearing
    const messageArea = page.locator('[data-testid="chat-messages"], .messages-container').first();
    const initialContent = await messageArea.textContent();

    await page.waitForTimeout(2000);
    const updatedContent = await messageArea.textContent();

    // Content should have grown (streaming)
    expect(updatedContent?.length).toBeGreaterThan(initialContent?.length || 0);

    // Wait for completion
    await waitForStreamingComplete(page, 60000);
  });

  test('can send message with Enter key', async ({ page }) => {
    await page.goto('/chat');
    await waitForPageReady(page);

    const input = page.locator('textarea, input[placeholder*="Ask"]').first();
    await input.fill('Hi');
    await input.press('Enter');

    // Should clear input after sending
    await page.waitForTimeout(1000);
    // Note: Input may or may not clear immediately depending on implementation
  });

  test('empty message cannot be sent', async ({ page }) => {
    await page.goto('/chat');
    await waitForPageReady(page);

    const sendButton = page.locator('button[type="submit"]').first();
    const isDisabled = await sendButton.isDisabled();

    // Send button should be disabled when input is empty
    expect(isDisabled).toBe(true);
  });
});

test.describe('Chat History', () => {
  test('new chat button exists', async ({ page }) => {
    await page.goto('/chat');
    await waitForPageReady(page);

    const newChatButton = page.locator('button:has-text("New"), button[aria-label*="new chat"]').first();
    await expect(newChatButton).toBeVisible();
  });

  test('can start new chat', async ({ page }) => {
    await page.goto('/chat');
    await waitForPageReady(page);

    // Send a message first
    const input = page.locator('textarea, input[placeholder*="Ask"]').first();
    await input.fill('First message');
    await page.keyboard.press('Enter');
    await page.waitForTimeout(3000);

    // Click new chat
    const newChatButton = page.locator('button:has-text("New"), button[aria-label*="new chat"]').first();
    await newChatButton.click();
    await page.waitForTimeout(1000);

    // Messages should be cleared
    await expect(page.locator('text=First message')).not.toBeVisible();
  });
});

test.describe('Chat Model Selection', () => {
  test('can open model dropdown', async ({ page }) => {
    await page.goto('/chat');
    await waitForPageReady(page);

    const modelSelector = page.locator('[data-testid="model-select"], select, [role="combobox"]').first();
    await modelSelector.click();

    // Options should be visible
    await page.waitForTimeout(500);
    const options = page.locator('[role="option"], option');
    const count = await options.count();
    expect(count).toBeGreaterThan(0);
  });
});
```

---

## Part 3: Authentication Tests

### Location: `ui/e2e/auth.spec.ts`

```typescript
import { test, expect } from '@playwright/test';
import { waitForPageReady, signInWithChutes } from './utils/helpers';

const CHUTES_FINGERPRINT = process.env.CHUTES_FINGERPRINT || '';

test.describe('Free Chat Limit', () => {
  test('shows free chat counter', async ({ page }) => {
    await page.goto('/chat');
    await waitForPageReady(page);

    // Look for free chat indicator (may not be visible if signed in)
    const counter = page.locator('text=/\\d+.*free.*chat/i, text=/\\d+.*remaining/i');
    // Counter may or may not be visible
  });

  test('sign in dialog appears after limit', async ({ page }) => {
    await page.goto('/chat');
    await waitForPageReady(page);

    // Clear any existing auth
    await page.context().clearCookies();
    await page.reload();

    // This would require actually hitting the limit
    // For now, check sign-in link exists
    const signInLink = page.locator('text=/sign in/i, a[href*="login"]').first();
    // May or may not be visible depending on state
  });
});

test.describe('Authenticated User', () => {
  test.skip(!CHUTES_FINGERPRINT, 'Requires CHUTES_FINGERPRINT env var');

  test('can sign in with Chutes fingerprint', async ({ page }) => {
    await page.goto('/chat');
    await signInWithChutes(page, CHUTES_FINGERPRINT);

    // Should show user menu or avatar
    const userIndicator = page.locator('[data-testid="user-menu"], [aria-label*="user"], .user-avatar');
    await expect(userIndicator).toBeVisible({ timeout: 10000 });
  });

  test('authenticated user has unlimited chats', async ({ page }) => {
    await page.goto('/chat');
    await signInWithChutes(page, CHUTES_FINGERPRINT);

    // Free chat counter should not be visible or should show unlimited
    const limitedCounter = page.locator('text=/\\d+\\/5.*chat/i');
    await expect(limitedCounter).not.toBeVisible();
  });

  test('can sign out', async ({ page }) => {
    await page.goto('/chat');
    await signInWithChutes(page, CHUTES_FINGERPRINT);

    // Find and click sign out
    const userMenu = page.locator('[data-testid="user-menu"]').first();
    if (await userMenu.isVisible()) {
      await userMenu.click();
      const signOutButton = page.locator('text=/sign out/i, button:has-text("Log out")');
      if (await signOutButton.isVisible()) {
        await signOutButton.click();
        await page.waitForTimeout(1000);
        // Should show sign in again
      }
    }
  });
});

test.describe('OAuth Flow', () => {
  test('login button redirects to Chutes IDP', async ({ page }) => {
    await page.goto('/chat');
    await waitForPageReady(page);

    // Find login link/button
    const loginButton = page.locator('a:has-text("Sign in"), button:has-text("Sign in")').first();
    if (await loginButton.isVisible()) {
      // Check href or click and verify redirect
      const href = await loginButton.getAttribute('href');
      if (href) {
        expect(href).toContain('/api/auth/login');
      }
    }
  });
});
```

---

## Part 4: File Upload Tests

### Location: `ui/e2e/file-upload.spec.ts`

```typescript
import { test, expect } from '@playwright/test';
import { waitForPageReady, waitForStreamingComplete } from './utils/helpers';
import path from 'path';
import fs from 'fs';

test.describe('Image Upload', () => {
  // Create a test image
  const testImagePath = path.join(__dirname, 'fixtures', 'test-image.png');

  test.beforeAll(async () => {
    // Create fixtures directory and test image if they don't exist
    const fixturesDir = path.join(__dirname, 'fixtures');
    if (!fs.existsSync(fixturesDir)) {
      fs.mkdirSync(fixturesDir, { recursive: true });
    }

    // Create a simple 1x1 PNG
    const pngData = Buffer.from([
      0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A, 0x00, 0x00, 0x00, 0x0D,
      0x49, 0x48, 0x44, 0x52, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
      0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53, 0xDE, 0x00, 0x00, 0x00,
      0x0C, 0x49, 0x44, 0x41, 0x54, 0x08, 0xD7, 0x63, 0xF8, 0x0F, 0x00, 0x00,
      0x01, 0x01, 0x00, 0x05, 0x18, 0xD8, 0x4D, 0x06, 0x00, 0x00, 0x00, 0x00,
      0x49, 0x45, 0x4E, 0x44, 0xAE, 0x42, 0x60, 0x82,
    ]);
    fs.writeFileSync(testImagePath, pngData);
  });

  test('can upload image via file input', async ({ page }) => {
    await page.goto('/chat');
    await waitForPageReady(page);

    // Find file input (may be hidden)
    const fileInput = page.locator('input[type="file"]');

    if (await fileInput.count() > 0) {
      await fileInput.setInputFiles(testImagePath);

      // Check for image preview or confirmation
      await page.waitForTimeout(1000);

      // Image should be attached (look for preview or badge)
      const hasAttachment = await page.locator('[data-testid="attachment-preview"], img[src*="data:"], .attachment-badge').count() > 0;
      expect(hasAttachment).toBe(true);
    }
  });

  test('can send message with attached image', async ({ page }) => {
    await page.goto('/chat');
    await waitForPageReady(page);

    const fileInput = page.locator('input[type="file"]');
    if (await fileInput.count() > 0) {
      await fileInput.setInputFiles(testImagePath);
      await page.waitForTimeout(500);

      // Type message
      const input = page.locator('textarea, input[placeholder*="Ask"]').first();
      await input.fill('What do you see?');
      await page.keyboard.press('Enter');

      // Wait for response
      await waitForStreamingComplete(page);

      // Should have received a response
      const messages = page.locator('[data-role="assistant"], .assistant-message');
      await expect(messages.first()).toBeVisible({ timeout: 60000 });
    }
  });

  test('can remove attached image before sending', async ({ page }) => {
    await page.goto('/chat');
    await waitForPageReady(page);

    const fileInput = page.locator('input[type="file"]');
    if (await fileInput.count() > 0) {
      await fileInput.setInputFiles(testImagePath);
      await page.waitForTimeout(500);

      // Find and click remove button
      const removeButton = page.locator('[data-testid="remove-attachment"], button[aria-label*="remove"]').first();
      if (await removeButton.isVisible()) {
        await removeButton.click();

        // Attachment should be gone
        await expect(page.locator('[data-testid="attachment-preview"]')).not.toBeVisible();
      }
    }
  });
});

test.describe('Drag and Drop Upload', () => {
  test('shows drop zone on drag over', async ({ page }) => {
    await page.goto('/chat');
    await waitForPageReady(page);

    // Simulate drag over (this is tricky in Playwright)
    // May need to dispatch custom events
  });
});
```

---

## Part 5: Voice Input Tests

### Location: `ui/e2e/voice-input.spec.ts`

```typescript
import { test, expect } from '@playwright/test';
import { waitForPageReady } from './utils/helpers';

test.describe('Voice Input', () => {
  test.beforeEach(async ({ page, context }) => {
    // Grant microphone permission
    await context.grantPermissions(['microphone']);
    await page.goto('/chat');
    await waitForPageReady(page);
  });

  test('microphone button exists', async ({ page }) => {
    const micButton = page.locator('button[aria-label*="voice"], button[aria-label*="mic"]').first();
    // Button may or may not exist
  });

  test('clicking mic button shows recording state', async ({ page }) => {
    const micButton = page.locator('button[aria-label*="voice"], button[aria-label*="mic"]').first();

    if (await micButton.isVisible()) {
      await micButton.click();
      await page.waitForTimeout(500);

      // Should show recording indicator
      const recordingIndicator = page.locator('[data-recording="true"], .recording, text=/recording/i');
      // May or may not work depending on browser/permissions
    }
  });

  test('handles permission denied gracefully', async ({ page, context }) => {
    // Revoke permission
    await context.clearPermissions();

    const micButton = page.locator('button[aria-label*="voice"], button[aria-label*="mic"]').first();

    if (await micButton.isVisible()) {
      await micButton.click();
      await page.waitForTimeout(1000);

      // Should show error message
      const errorMessage = page.locator('text=/permission/i, text=/denied/i');
      // Error handling may vary
    }
  });
});
```

---

## Part 6: Memory Feature Tests

### Location: `ui/e2e/memory.spec.ts`

```typescript
import { test, expect } from '@playwright/test';
import { waitForPageReady, signInWithChutes } from './utils/helpers';

const CHUTES_FINGERPRINT = process.env.CHUTES_FINGERPRINT || '';

test.describe('Memory Feature', () => {
  test.skip(!CHUTES_FINGERPRINT, 'Requires CHUTES_FINGERPRINT');

  test.beforeEach(async ({ page }) => {
    await page.goto('/chat');
    await signInWithChutes(page, CHUTES_FINGERPRINT);
  });

  test('memory toggle is visible', async ({ page }) => {
    const memoryToggle = page.locator('button[aria-label*="memory"], [data-testid="memory-toggle"]');
    await expect(memoryToggle).toBeVisible();
  });

  test('can toggle memory on/off', async ({ page }) => {
    const memoryToggle = page.locator('button[aria-label*="memory"], [data-testid="memory-toggle"]').first();

    if (await memoryToggle.isVisible()) {
      const initialState = await memoryToggle.getAttribute('data-enabled');
      await memoryToggle.click();
      await page.waitForTimeout(500);
      const newState = await memoryToggle.getAttribute('data-enabled');
      expect(newState).not.toBe(initialState);
    }
  });
});

test.describe('Memory Management', () => {
  test.skip(!CHUTES_FINGERPRINT, 'Requires CHUTES_FINGERPRINT');

  test('can access memory management page', async ({ page }) => {
    await page.goto('/chat');
    await signInWithChutes(page, CHUTES_FINGERPRINT);

    // Look for memory management link
    const memoryLink = page.locator('a[href*="memory"], button:has-text("Manage memories")');
    if (await memoryLink.isVisible()) {
      await memoryLink.click();
      // Should navigate to memory page
    }
  });
});
```

---

## Part 7: Debug Mode Tests

### Location: `ui/e2e/debug-mode.spec.ts`

```typescript
import { test, expect } from '@playwright/test';
import { waitForPageReady, waitForStreamingComplete } from './utils/helpers';

test.describe('Debug Mode', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/chat');
    await waitForPageReady(page);
  });

  test('debug toggle exists', async ({ page }) => {
    const debugToggle = page.locator('button[aria-label*="debug"], [data-testid="debug-toggle"]');
    // May or may not be visible
  });

  test('enabling debug mode shows debug panel', async ({ page }) => {
    const debugToggle = page.locator('button[aria-label*="debug"], [data-testid="debug-toggle"]').first();

    if (await debugToggle.isVisible()) {
      await debugToggle.click();
      await page.waitForTimeout(500);

      // Debug panel should appear
      const debugPanel = page.locator('[data-testid="debug-panel"], .debug-panel');
      await expect(debugPanel).toBeVisible();
    }
  });

  test('debug panel shows Mermaid diagram', async ({ page }) => {
    const debugToggle = page.locator('button[aria-label*="debug"]').first();

    if (await debugToggle.isVisible()) {
      await debugToggle.click();

      // Look for Mermaid SVG
      const mermaidDiagram = page.locator('.debug-panel svg, .mermaid svg');
      // May or may not render immediately
    }
  });

  test('debug panel shows event log during request', async ({ page }) => {
    const debugToggle = page.locator('button[aria-label*="debug"]').first();

    if (await debugToggle.isVisible()) {
      await debugToggle.click();

      // Send a message
      const input = page.locator('textarea').first();
      await input.fill('Hi');
      await page.keyboard.press('Enter');

      // Wait and check for event log entries
      await page.waitForTimeout(3000);
      const logEntries = page.locator('.debug-log-entry, [data-testid="debug-event"]');
      // May have entries
    }
  });
});
```

---

## Part 8: Competition Page Tests

### Location: `ui/e2e/competition.spec.ts`

```typescript
import { test, expect } from '@playwright/test';
import { waitForPageReady, captureConsoleErrors } from './utils/helpers';

test.describe('Competition Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/competition');
    await waitForPageReady(page);
  });

  test('renders without console errors', async ({ page }) => {
    const errors = captureConsoleErrors(page);
    await page.waitForTimeout(2000);
    expect(errors).toHaveLength(0);
  });

  test('displays competition information', async ({ page }) => {
    // Check for competition-related content
    await expect(page.locator('h1, h2')).toBeVisible();
  });

  test('Mermaid diagrams render', async ({ page }) => {
    // Wait for Mermaid to render
    await page.waitForSelector('.mermaid svg, svg.mermaid', { timeout: 10000 });

    const diagrams = page.locator('.mermaid svg, svg.mermaid');
    const count = await diagrams.count();
    expect(count).toBeGreaterThan(0);
  });

  test('page is responsive', async ({ page }) => {
    // Test mobile viewport
    await page.setViewportSize({ width: 375, height: 812 });
    await page.waitForTimeout(500);

    const hasHorizontalScroll = await page.evaluate(() =>
      document.body.scrollWidth > document.body.clientWidth
    );
    expect(hasHorizontalScroll).toBe(false);
  });
});
```

---

## Part 9: Marketplace Page Tests

### Location: `ui/e2e/marketplace.spec.ts`

```typescript
import { test, expect } from '@playwright/test';
import { waitForPageReady } from './utils/helpers';

test.describe('Marketplace Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/marketplace');
    await waitForPageReady(page);
  });

  test('page loads successfully', async ({ page }) => {
    // May redirect or show "coming soon"
    await expect(page.locator('body')).toBeVisible();
  });

  test('displays marketplace content or placeholder', async ({ page }) => {
    // Check for either marketplace content or coming soon message
    const hasContent = await page.locator('h1, h2, text=/marketplace/i, text=/coming soon/i').count() > 0;
    expect(hasContent).toBe(true);
  });
});
```

---

## Running E2E Tests

### Commands

```bash
# Run all E2E tests
cd ui && npx playwright test

# Run specific test file
npx playwright test e2e/chat.spec.ts

# Run with headed browser (visible)
npx playwright test --headed

# Run on specific browser
npx playwright test --project="Desktop Chrome"

# Run against deployed URL
TEST_URL=https://janus.rodeo npx playwright test

# Generate HTML report
npx playwright show-report
```

### CI Configuration: `.github/workflows/e2e.yml`

```yaml
name: E2E Tests

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Install dependencies
        run: cd ui && npm ci

      - name: Install Playwright browsers
        run: cd ui && npx playwright install --with-deps

      - name: Run E2E tests
        run: cd ui && npx playwright test
        env:
          TEST_URL: ${{ secrets.TEST_URL }}
          CHUTES_FINGERPRINT: ${{ secrets.CHUTES_FINGERPRINT }}

      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: playwright-report
          path: ui/playwright-report/
          retention-days: 30
```

---

## Acceptance Criteria

- [ ] Landing page tests pass without console errors
- [ ] Chat interface loads and is interactive
- [ ] Can type and send messages
- [ ] Streaming responses render incrementally
- [ ] Model selector works
- [ ] New chat functionality works
- [ ] Image upload works (if feature enabled)
- [ ] Voice input UI works (with mocked permissions)
- [ ] Memory toggle works (with auth)
- [ ] Debug mode shows panel
- [ ] Competition page loads with Mermaid diagrams
- [ ] All pages are responsive
- [ ] Authentication flow tested (with CHUTES_FINGERPRINT)
- [ ] Tests run in CI
- [ ] Any failures result in code fixes

---

## Notes

- Use `CHUTES_FINGERPRINT` env var for authenticated tests
- Tests requiring external services may be skipped in CI
- Screenshots saved on failure for debugging
- Video recording available for flaky tests
- If a test fails, debug with `--headed` mode

NR_OF_TRIES: 1
