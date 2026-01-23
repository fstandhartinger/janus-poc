import { test, expect } from '@playwright/test';
import { fetchModels, streamChatCompletion } from '@/lib/api';

test.describe('API client', () => {
  test('fetchModels returns model list', async () => {
    const originalFetch = globalThis.fetch;
    globalThis.fetch = (async () =>
      new Response(
        JSON.stringify({
          data: [
            { id: 'baseline', object: 'model', created: 0, owned_by: 'janus' },
          ],
        }),
        { status: 200 }
      )) as typeof fetch;

    try {
      const models = await fetchModels();
      expect(models).toHaveLength(1);
      expect(models[0].id).toBe('baseline');
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  test('streamChatCompletion yields chunks', async () => {
    const originalFetch = globalThis.fetch;
    const encoder = new TextEncoder();
    const stream = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(
          encoder.encode(
            'data: {"id":"chatcmpl-test","object":"chat.completion.chunk","created":0,"model":"baseline","choices":[{"index":0,"delta":{"content":"Hello"},"finish_reason":null}]}\n\n'
          )
        );
        controller.enqueue(encoder.encode('data: [DONE]\n\n'));
        controller.close();
      },
    });

    globalThis.fetch = (async () => new Response(stream, { status: 200 })) as typeof fetch;

    const chunks = [];
    try {
      for await (const chunk of streamChatCompletion({
        model: 'baseline',
        messages: [{ role: 'user', content: 'Hi' }],
        stream: true,
      })) {
        chunks.push(chunk);
      }
      expect(chunks).toHaveLength(1);
      expect(chunks[0].choices[0].delta.content).toBe('Hello');
    } finally {
      globalThis.fetch = originalFetch;
    }
  });
});
