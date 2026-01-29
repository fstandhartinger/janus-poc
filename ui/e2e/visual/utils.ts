import { Page, test, type TestInfo } from '@playwright/test';

type ChatStreamOptions = {
  content?: string;
  delayMs?: number;
};

export function onlyForProjects(testInfo: TestInfo, projectNames: string[]) {
  test.skip(!projectNames.includes(testInfo.project.name), `Runs on ${projectNames.join(', ')} only.`);
}

export async function mockServiceHealth(page: Page) {
  await page.route('**/api/transcribe/health', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        available: true,
        endpoint: 'http://localhost:8000/api/transcribe/health',
        api_key_configured: true,
      }),
    });
  });

  await page.route('**/health', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        status: 'ok',
        sandbox_available: true,
        features: { agent_sandbox: true },
      }),
    });
  });

  await page.route('**/api/arena/leaderboard', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        { model: 'baseline-cli-agent', elo: 1520, wins: 12, losses: 5, ties: 3, matches: 20 },
        { model: 'baseline-langchain', elo: 1480, wins: 9, losses: 7, ties: 4, matches: 20 },
      ]),
    });
  });
}

export async function mockChatStream(page: Page, options: ChatStreamOptions = {}) {
  const content = options.content ?? 'Hello from Janus';
  const delayMs = options.delayMs ?? 0;

  await page.route('**/api/chat', async (route) => {
    if (delayMs > 0) {
      await new Promise((resolve) => setTimeout(resolve, delayMs));
    }

    const chunks = [
      'data: {"id":"chatcmpl-test","object":"chat.completion.chunk","created":0,"model":"baseline","choices":[{"index":0,"delta":{"role":"assistant"},"finish_reason":null}]}',
      `data: {"id":"chatcmpl-test","object":"chat.completion.chunk","created":0,"model":"baseline","choices":[{"index":0,"delta":{"content":${JSON.stringify(content)}},"finish_reason":null}]}`,
      'data: [DONE]',
    ];

    await route.fulfill({
      status: 200,
      headers: { 'Content-Type': 'text/event-stream' },
      body: chunks.join('\n\n'),
    });
  });
}

export async function stabilizeLandingHero(page: Page) {
  await page.addStyleTag({
    content: `
      .hero-video-element,
      .hero-video-canvas {
        display: none !important;
      }
      .hero-video-poster {
        opacity: 1 !important;
      }
    `,
  });

  await page.evaluate(() => {
    const video = document.querySelector<HTMLVideoElement>('.hero-video-element');
    if (video) {
      video.pause();
      video.currentTime = 0;
    }
  });
}

export async function waitForChatReady(page: Page) {
  await page.waitForSelector('.agent-status-indicator', { timeout: 5000 }).catch(() => {});
  await page
    .waitForFunction(
      () => !document.querySelector('.agent-status-indicator.is-loading'),
      null,
      { timeout: 5000 }
    )
    .catch(() => {});
}

export async function stabilizeChatPage(page: Page) {
  await page.addStyleTag({
    content: `
      .agent-status-dot,
      .chat-streaming-dot {
        animation: none !important;
      }
      textarea,
      input {
        caret-color: transparent !important;
      }
    `,
  });
}
