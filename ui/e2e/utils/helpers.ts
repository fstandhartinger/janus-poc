import { Page, expect } from '@playwright/test';
import fs from 'fs';
import path from 'path';

export async function waitForPageReady(page: Page) {
  await page.waitForLoadState('domcontentloaded');
  await page.waitForTimeout(500);
}

type StubAuthUser = { id: string; username?: string | null };

export async function stubChatDependencies(page: Page, user: StubAuthUser | null = null) {
  const corsHeaders = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
    'Access-Control-Allow-Headers': '*',
  };

  const handleGatewayRoute: Parameters<Page['route']>[1] = async (route) => {
    const request = route.request();
    if (request.method() === 'OPTIONS') {
      await route.fulfill({ status: 204, headers: corsHeaders });
      return;
    }

    const url = new URL(request.url());
    if (url.pathname === '/health') {
      await route.fulfill({
        status: 200,
        headers: corsHeaders,
        contentType: 'application/json',
        body: JSON.stringify({ sandbox_available: true }),
      });
      return;
    }

    if (url.pathname === '/v1/models') {
      await route.fulfill({
        status: 200,
        headers: corsHeaders,
        contentType: 'application/json',
        body: JSON.stringify({
          data: [
            { id: 'baseline-cli-agent', object: 'model', created: 0, owned_by: 'janus' },
            { id: 'baseline-langchain', object: 'model', created: 0, owned_by: 'janus' },
          ],
        }),
      });
      return;
    }

    await route.fulfill({
      status: 200,
      headers: corsHeaders,
      contentType: 'application/json',
      body: JSON.stringify({ ok: true }),
    });
  };

  await page.route('**://localhost:8000/**', handleGatewayRoute);
  await page.route('**://127.0.0.1:8000/**', handleGatewayRoute);

  await page.route('**/api/auth/me', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ user }),
    });
  });

  await page.route('**/api/auth/logout', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: '{}' });
  });
}

export async function waitForChatReady(page: Page) {
  await waitForPageReady(page);
  const statusIndicator = page.locator('.agent-status-indicator');
  await statusIndicator.waitFor({ state: 'attached' });
  await expect(statusIndicator).not.toHaveClass(/is-loading/);
}

export async function waitForStreamingComplete(page: Page, timeout = 60000) {
  const startTime = Date.now();
  let lastContent = '';

  while (Date.now() - startTime < timeout) {
    await page.waitForTimeout(1000);

    const isStreaming = (await page.locator('[aria-busy="true"]').count()) > 0;
    const messageArea = page.locator('[data-testid="chat-messages"], .chat-messages-container').first();
    const currentContent = (await messageArea.textContent()) || '';

    if (!isStreaming && currentContent === lastContent) {
      break;
    }

    if (currentContent !== lastContent) {
      lastContent = currentContent;
    }
  }

  await expect(page.locator('[aria-busy="true"]')).toHaveCount(0);
}

export function captureConsoleErrors(page: Page): string[] {
  const errors: string[] = [];
  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      errors.push(msg.text());
    }
  });
  return errors;
}

export async function signInWithChutes(page: Page, fingerprint: string) {
  const url = new URL(page.url());
  await page.context().addCookies([
    {
      name: 'chutes_fingerprint',
      value: fingerprint,
      domain: url.hostname,
      path: '/',
      sameSite: 'Lax',
    },
  ]);
  try {
    await page.reload({ waitUntil: 'domcontentloaded' });
  } catch {
    await page.goto(url.toString(), { waitUntil: 'domcontentloaded' });
  }
  await waitForPageReady(page);
}

export async function setChatInputValue(page: Page, value: string) {
  const textarea = page.locator('[data-testid="chat-input"]');
  await textarea.waitFor({ state: 'visible' });
  await textarea.click();
  await textarea.fill(value);
  let current = await textarea.inputValue();
  if (current !== value) {
    await page.evaluate((text) => {
      const input = document.querySelector('[data-testid="chat-input"]') as HTMLTextAreaElement | null;
      if (!input) return;
      input.value = text;
      input.dispatchEvent(new Event('input', { bubbles: true }));
      input.dispatchEvent(new Event('change', { bubbles: true }));
    }, value);
    current = await textarea.inputValue();
  }
  await expect(textarea).toHaveValue(value);
}

export async function takeTimestampedScreenshot(page: Page, name: string) {
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const screenshotDir = path.join(process.cwd(), 'e2e-screenshots');
  await fs.promises.mkdir(screenshotDir, { recursive: true });
  await page.screenshot({
    path: path.join(screenshotDir, `${name}_${timestamp}.png`),
    fullPage: true,
  });
}
