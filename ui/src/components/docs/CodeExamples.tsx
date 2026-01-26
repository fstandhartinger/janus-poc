'use client';

import { useState } from 'react';

import { CodeBlock } from '@/components/CodeBlock';

const codeExamples = [
  {
    id: 'python',
    label: 'Python',
    language: 'python',
    code: `import openai

client = openai.OpenAI(
    base_url="https://janus-gateway-bqou.onrender.com/v1",
    api_key="not-required"  # Currently open access
)

response = client.chat.completions.create(
    model="baseline-cli-agent",
    messages=[
        {"role": "user", "content": "Explain quantum computing in simple terms"}
    ],
    stream=True
)

for chunk in response:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="")
`,
  },
  {
    id: 'typescript',
    label: 'TypeScript',
    language: 'typescript',
    code: `import OpenAI from 'openai';

const client = new OpenAI({
  baseURL: 'https://janus-gateway-bqou.onrender.com/v1',
  apiKey: 'not-required',  // Currently open access
});

async function chat() {
  const stream = await client.chat.completions.create({
    model: 'baseline-cli-agent',
    messages: [
      { role: 'user', content: 'Explain quantum computing in simple terms' }
    ],
    stream: true,
  });

  for await (const chunk of stream) {
    const content = chunk.choices[0]?.delta?.content || '';
    process.stdout.write(content);
  }
}

chat();
`,
  },
  {
    id: 'curl',
    label: 'cURL',
    language: 'bash',
    code: `curl -X POST "https://janus-gateway-bqou.onrender.com/v1/chat/completions" \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "baseline-cli-agent",
    "messages": [
      {"role": "user", "content": "Explain quantum computing in simple terms"}
    ],
    "stream": false
  }'
`,
  },
  {
    id: 'go',
    label: 'Go',
    language: 'go',
    code: `package main

import (
    "context"
    "fmt"
    "github.com/sashabaranov/go-openai"
)

func main() {
    config := openai.DefaultConfig("not-required")
    config.BaseURL = "https://janus-gateway-bqou.onrender.com/v1"
    client := openai.NewClientWithConfig(config)

    resp, err := client.CreateChatCompletion(
        context.Background(),
        openai.ChatCompletionRequest{
            Model: "baseline-cli-agent",
            Messages: []openai.ChatCompletionMessage{
                {
                    Role:    openai.ChatMessageRoleUser,
                    Content: "Explain quantum computing in simple terms",
                },
            },
        },
    )
    if err != nil {
        panic(err)
    }

    fmt.Println(resp.Choices[0].Message.Content)
}
`,
  },
  {
    id: 'httpie',
    label: 'HTTPie',
    language: 'bash',
    code: `http POST https://janus-gateway-bqou.onrender.com/v1/chat/completions \\
  model=baseline-cli-agent \\
  messages:='[{"role": "user", "content": "Hello!"}]' \\
  stream:=false
`,
  },
];

export function CodeExamples() {
  const [activeId, setActiveId] = useState(codeExamples[0].id);
  const activeExample = codeExamples.find((example) => example.id === activeId) ?? codeExamples[0];

  return (
    <div className="glass-card p-6 space-y-4">
      <div className="flex flex-wrap gap-2" role="tablist" aria-label="API code examples">
        {codeExamples.map((example) => {
          const isActive = example.id === activeId;

          return (
            <button
              key={example.id}
              type="button"
              role="tab"
              aria-selected={isActive}
              onClick={() => setActiveId(example.id)}
              className={`px-3 py-1.5 rounded-full text-xs uppercase tracking-[0.2em] transition ${
                isActive
                  ? 'bg-[#63D297] text-[#0B0F14]'
                  : 'border border-[#1F2937] text-[#9CA3AF] hover:text-[#F3F4F6]'
              }`}
            >
              {example.label}
            </button>
          );
        })}
      </div>
      <CodeBlock code={activeExample.code} language={activeExample.language} />
    </div>
  );
}
