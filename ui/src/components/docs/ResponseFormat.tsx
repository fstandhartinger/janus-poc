import { CodeBlock } from '@/components/CodeBlock';

const nonStreamingResponse = `{
  "id": "chatcmpl-abc123def456",
  "object": "chat.completion",
  "created": 1706123456,
  "model": "baseline-cli-agent",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Quantum computing uses quantum mechanics...",
        "reasoning_content": null,
        "artifacts": [],
        "tool_calls": null
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 15,
    "completion_tokens": 142,
    "total_tokens": 157,
    "cost_usd": 0.00023,
    "sandbox_seconds": 45.2
  }
}`;

const streamingResponse = `data: {"id":"chatcmpl-abc123","object":"chat.completion.chunk","choices":[{"delta":{"role":"assistant"},"index":0}]}

data: {"id":"chatcmpl-abc123","object":"chat.completion.chunk","choices":[{"delta":{"content":"Quantum"},"index":0}]}

data: {"id":"chatcmpl-abc123","object":"chat.completion.chunk","choices":[{"delta":{"content":" computing"},"index":0}]}

data: [DONE]
`;

export function ResponseFormat() {
  return (
    <div className="space-y-4">
      <details open className="glass-card p-6">
        <summary className="cursor-pointer text-lg font-semibold text-[#F3F4F6]">
          Non-streaming response
        </summary>
        <div className="mt-4">
          <CodeBlock code={nonStreamingResponse} language="json" />
        </div>
      </details>
      <details className="glass-card p-6">
        <summary className="cursor-pointer text-lg font-semibold text-[#F3F4F6]">
          Streaming response (SSE)
        </summary>
        <div className="mt-4">
          <CodeBlock code={streamingResponse} language="text" />
        </div>
      </details>
    </div>
  );
}
