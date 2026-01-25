# Spec 87: API Documentation Page

## Status: NOT STARTED

## Context / Why

Developers want to integrate with the Janus API to build applications, chatbots, and automated systems. The API is OpenAI-compatible but has Janus-specific extensions for artifacts, generative UI, memory, and more. A dedicated documentation page in the UI provides:

1. Quick-start examples in multiple languages
2. Complete parameter reference
3. Documentation of Janus-specific extensions
4. Interactive Swagger/OpenAPI explorer
5. Copy-paste ready code snippets

## Goals

- Create an API documentation section in the UI
- Provide code examples in Python, JavaScript/TypeScript, cURL, and Go
- Document all request/response parameters including Janus extensions
- Link to interactive Swagger documentation
- Explain special response formats (generative UI, artifacts)

## Non-Goals

- SDK library development (future consideration)
- API key management UI (covered elsewhere)
- Rate limiting documentation (infrastructure concern)

## Functional Requirements

### FR-1: API Documentation Page

Create a new page at `/api-docs` with comprehensive documentation.

```typescript
// ui/src/app/api-docs/page.tsx

import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { CodeBlock } from '@/components/CodeBlock';

export default function ApiDocsPage() {
  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-5xl mx-auto px-4 py-12">
        <h1 className="text-4xl font-bold mb-4">Janus API Documentation</h1>
        <p className="text-muted-foreground text-lg mb-8">
          OpenAI-compatible chat completions API with Janus extensions for
          artifacts, generative UI, and intelligent agent capabilities.
        </p>

        {/* Quick Links */}
        <div className="flex gap-4 mb-12">
          <a
            href="/api/docs"
            target="_blank"
            className="px-4 py-2 bg-moss/20 text-moss rounded-lg hover:bg-moss/30"
          >
            Swagger UI
          </a>
          <a
            href="/api/openapi.json"
            target="_blank"
            className="px-4 py-2 bg-white/10 rounded-lg hover:bg-white/20"
          >
            OpenAPI Spec
          </a>
        </div>

        {/* Sections */}
        <TableOfContents />
        <QuickStart />
        <Authentication />
        <ChatCompletionsEndpoint />
        <RequestParameters />
        <ResponseFormat />
        <JanusExtensions />
        <CodeExamples />
        <ErrorHandling />
      </div>
    </div>
  );
}
```

### FR-2: Quick Start Section

```markdown
## Quick Start

The Janus API is compatible with OpenAI's chat completions API.
If you're already using OpenAI, just change the base URL:

**Base URL:** `https://janus-gateway-bqou.onrender.com/v1`

**Endpoint:** `POST /v1/chat/completions`
```

### FR-3: Code Examples Component

```typescript
// ui/src/components/docs/CodeExamples.tsx

const examples = {
  python: `import openai

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

  typescript: `import OpenAI from 'openai';

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

  curl: `curl -X POST "https://janus-gateway-bqou.onrender.com/v1/chat/completions" \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "baseline-cli-agent",
    "messages": [
      {"role": "user", "content": "Explain quantum computing in simple terms"}
    ],
    "stream": false
  }'
`,

  go: `package main

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

  httpie: `http POST https://janus-gateway-bqou.onrender.com/v1/chat/completions \\
  model=baseline-cli-agent \\
  messages:='[{"role": "user", "content": "Hello!"}]' \\
  stream:=false
`
};
```

### FR-4: Request Parameters Documentation

```typescript
// ui/src/components/docs/RequestParameters.tsx

const parameters = [
  {
    name: 'model',
    type: 'string',
    required: true,
    description: 'Model/competitor to use. Currently: "baseline-cli-agent", "baseline-langchain", or "baseline".',
  },
  {
    name: 'messages',
    type: 'array',
    required: true,
    description: 'Array of message objects with role and content.',
    children: [
      { name: 'role', type: '"user" | "assistant" | "system"', description: 'Message author role' },
      { name: 'content', type: 'string | ContentPart[]', description: 'Text or multimodal content' },
    ]
  },
  {
    name: 'stream',
    type: 'boolean',
    required: false,
    default: 'false',
    description: 'Enable Server-Sent Events streaming for real-time responses.',
  },
  {
    name: 'temperature',
    type: 'number',
    required: false,
    default: '0.7',
    description: 'Sampling temperature (0-2). Lower = more focused, higher = more creative.',
  },
  {
    name: 'max_tokens',
    type: 'integer',
    required: false,
    default: '4096',
    description: 'Maximum tokens to generate in the response.',
  },
  {
    name: 'user',
    type: 'string',
    required: false,
    description: 'Unique user identifier for memory features and usage tracking.',
  },
  {
    name: 'tools',
    type: 'array',
    required: false,
    description: 'Function definitions the model can call.',
  },
  {
    name: 'tool_choice',
    type: 'string | object',
    required: false,
    description: 'Control tool usage: "auto", "none", or specific tool.',
  },
  {
    name: 'metadata',
    type: 'object',
    required: false,
    description: 'Custom metadata passed through to the response.',
  },
];

// Janus-specific extensions
const janusExtensions = [
  {
    name: 'competitor_id',
    type: 'string',
    required: false,
    description: 'Explicitly route to a specific competitor implementation.',
  },
  {
    name: 'enable_memory',
    type: 'boolean',
    required: false,
    default: 'false',
    description: 'Enable memory extraction and retrieval for personalized responses.',
  },
  {
    name: 'generation_flags',
    type: 'object',
    required: false,
    description: 'Request specific generation types.',
    children: [
      { name: 'generate_image', type: 'boolean', description: 'Request image generation' },
      { name: 'generate_video', type: 'boolean', description: 'Request video generation' },
      { name: 'generate_audio', type: 'boolean', description: 'Request audio generation' },
      { name: 'deep_research', type: 'boolean', description: 'Enable deep web research' },
      { name: 'web_search', type: 'boolean', description: 'Enable web search' },
    ]
  },
];
```

### FR-5: Response Format Documentation

```typescript
// Response structure documentation

const responseFormat = `
## Response Format

### Non-Streaming Response

\`\`\`json
{
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
}
\`\`\`

### Streaming Response (SSE)

\`\`\`
data: {"id":"chatcmpl-abc123","object":"chat.completion.chunk","choices":[{"delta":{"role":"assistant"},"index":0}]}

data: {"id":"chatcmpl-abc123","object":"chat.completion.chunk","choices":[{"delta":{"content":"Quantum"},"index":0}]}

data: {"id":"chatcmpl-abc123","object":"chat.completion.chunk","choices":[{"delta":{"content":" computing"},"index":0}]}

data: [DONE]
\`\`\`
`;
```

### FR-6: Janus Extensions Documentation

```markdown
## Janus Extensions

### Artifacts

When the model generates files, images, or other non-text outputs, they appear
in the `artifacts` array:

```json
{
  "message": {
    "content": "I've created the chart you requested.",
    "artifacts": [
      {
        "id": "artf_x7k9m2p4",
        "type": "image",
        "mime_type": "image/png",
        "display_name": "sales_chart.png",
        "size_bytes": 45678,
        "url": "https://janus-gateway.../v1/artifacts/artf_x7k9m2p4",
        "ttl_seconds": 3600
      }
    ]
  }
}
```

**Artifact Types:**
- `image` - Generated images (PNG, JPEG, WebP)
- `file` - Documents, code, data files
- `dataset` - Structured data collections
- `binary` - Raw binary outputs

**Note:** Artifacts under 1MB are returned as data: URLs. Larger files use HTTP URLs.

### Generative UI Blocks

Responses may contain interactive UI widgets using the `html-gen-ui` code fence:

```markdown
Here's an interactive calculator:

\`\`\`html-gen-ui
<!DOCTYPE html>
<html>
<head>
  <style>
    body { background: #1a1a2e; color: #e0e0e0; padding: 1rem; }
  </style>
</head>
<body>
  <input type="number" id="a"> + <input type="number" id="b">
  <button onclick="calculate()">Calculate</button>
  <p id="result"></p>
  <script>
    function calculate() {
      const a = parseFloat(document.getElementById('a').value) || 0;
      const b = parseFloat(document.getElementById('b').value) || 0;
      document.getElementById('result').textContent = 'Result: ' + (a + b);
    }
  </script>
</body>
</html>
\`\`\`
```

These blocks render as sandboxed iframes in the Janus chat UI.

### Reasoning Content

For complex tasks, the model may include intermediate reasoning steps:

```json
{
  "message": {
    "content": "The answer is 42.",
    "reasoning_content": "Let me break this down step by step..."
  }
}
```

### Janus Stream Events

During streaming, special events may appear in the `janus` field:

```json
{
  "delta": {
    "content": null,
    "janus": {
      "event": "tool_start",
      "tool_name": "web_search",
      "metadata": {"query": "latest AI news"}
    }
  }
}
```

**Event Types:**
- `tool_start` / `tool_end` - Tool execution lifecycle
- `sandbox_start` / `sandbox_end` - Agent sandbox execution
- `artifact_generated` - New artifact created
```

### FR-7: Multimodal Input Examples

```typescript
// Examples for vision/multimodal input

const multimodalExamples = {
  python: `# Image analysis with URL
response = client.chat.completions.create(
    model="baseline-cli-agent",
    messages=[
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "What's in this image?"},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": "https://example.com/image.jpg",
                        "detail": "high"  # "auto", "low", or "high"
                    }
                }
            ]
        }
    ]
)

# Image analysis with base64
import base64

with open("image.png", "rb") as f:
    image_data = base64.b64encode(f.read()).decode()

response = client.chat.completions.create(
    model="baseline-cli-agent",
    messages=[
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Describe this image"},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{image_data}"
                    }
                }
            ]
        }
    ]
)
`,

  typescript: `// Image analysis with TypeScript
const response = await client.chat.completions.create({
  model: 'baseline-cli-agent',
  messages: [
    {
      role: 'user',
      content: [
        { type: 'text', text: "What's in this image?" },
        {
          type: 'image_url',
          image_url: {
            url: 'https://example.com/image.jpg',
            detail: 'high',
          },
        },
      ],
    },
  ],
});
`,
};
```

### FR-8: Memory Feature Examples

```typescript
const memoryExamples = {
  python: `# Enable memory for personalized responses
response = client.chat.completions.create(
    model="baseline-cli-agent",
    messages=[
        {"role": "user", "content": "Remember that my favorite color is blue"}
    ],
    user="user_abc123",  # Required for memory features
    extra_body={
        "enable_memory": True  # Janus extension
    }
)

# Later conversation - memories are automatically retrieved
response = client.chat.completions.create(
    model="baseline-cli-agent",
    messages=[
        {"role": "user", "content": "What's my favorite color?"}
    ],
    user="user_abc123",
    extra_body={
        "enable_memory": True
    }
)
# Response: "Your favorite color is blue!"
`,
};
```

### FR-9: Swagger/OpenAPI Integration

Enable Swagger UI in the gateway and link from the docs page.

```python
# gateway/janus_gateway/main.py - ensure docs are enabled

app = FastAPI(
    title="Janus Gateway API",
    description="""
OpenAI-compatible AI agent gateway for the Janus competitive network.

## Features
- Chat completions with streaming support
- Multimodal inputs (text, images)
- Artifact generation (images, files, data)
- Generative UI responses
- Memory and personalization
- Intelligent agent routing

## Authentication
Currently open access. API keys coming soon.
    """,
    version=__version__,
    docs_url="/api/docs",       # Swagger UI
    redoc_url="/api/redoc",     # ReDoc
    openapi_url="/api/openapi.json",
)
```

### FR-10: Navigation Integration

Add API Docs link to the site navigation.

```typescript
// ui/src/components/Navigation.tsx (update)

const navItems = [
  { href: '/', label: 'Home' },
  { href: '/chat', label: 'Chat' },
  { href: '/competition', label: 'Competition' },
  { href: '/api-docs', label: 'API' },  // NEW
];
```

### FR-11: CodeBlock Component

Create a reusable code block with copy functionality.

```typescript
// ui/src/components/CodeBlock.tsx

'use client';

import { useState } from 'react';
import { Check, Copy } from 'lucide-react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';

interface CodeBlockProps {
  code: string;
  language: string;
  showLineNumbers?: boolean;
}

export function CodeBlock({ code, language, showLineNumbers = true }: CodeBlockProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="relative group rounded-lg overflow-hidden">
      <button
        onClick={handleCopy}
        className="absolute right-2 top-2 p-2 rounded bg-white/10 opacity-0 group-hover:opacity-100 transition-opacity"
        aria-label="Copy code"
      >
        {copied ? (
          <Check size={16} className="text-moss" />
        ) : (
          <Copy size={16} className="text-white/60" />
        )}
      </button>
      <SyntaxHighlighter
        language={language}
        style={vscDarkPlus}
        showLineNumbers={showLineNumbers}
        customStyle={{
          margin: 0,
          borderRadius: '0.5rem',
          fontSize: '0.875rem',
        }}
      >
        {code}
      </SyntaxHighlighter>
    </div>
  );
}
```

## Technical Design

### Page Structure

```
/api-docs
├── Quick Start (base URL, simple example)
├── Authentication (current: open, future: API keys)
├── Endpoints
│   ├── POST /v1/chat/completions
│   ├── GET /v1/models
│   └── GET /v1/artifacts/{id}
├── Request Parameters
│   ├── Standard OpenAI parameters
│   └── Janus extensions
├── Response Format
│   ├── Non-streaming
│   ├── Streaming (SSE)
│   └── Artifacts
├── Janus Extensions
│   ├── Generative UI
│   ├── Memory
│   ├── Generation flags
│   └── Stream events
├── Code Examples (tabbed)
│   ├── Python
│   ├── TypeScript/JavaScript
│   ├── cURL
│   ├── Go
│   └── HTTPie
├── Multimodal Input
├── Error Handling
└── Links
    ├── Swagger UI (/api/docs)
    └── OpenAPI JSON (/api/openapi.json)
```

### Styling

- Dark theme matching Janus UI
- Syntax-highlighted code blocks with copy buttons
- Collapsible sections for detailed content
- Responsive tables for parameters
- Tab groups for language selection
- Anchor links for deep linking

## Acceptance Criteria

- [ ] API documentation page accessible at `/api-docs`
- [ ] Code examples in Python, TypeScript, cURL, Go, HTTPie
- [ ] All request parameters documented with types and defaults
- [ ] Response format documented including Janus extensions
- [ ] Generative UI code fence format explained
- [ ] Memory feature flags documented
- [ ] Artifacts and multimodal input documented
- [ ] Copy-to-clipboard on all code blocks
- [ ] Swagger UI link works (`/api/docs`)
- [ ] OpenAPI JSON link works (`/api/openapi.json`)
- [ ] Navigation includes API link
- [ ] Mobile-responsive layout

## Files to Create/Modify

```
ui/src/
├── app/
│   └── api-docs/
│       └── page.tsx              # NEW: Main docs page
├── components/
│   ├── CodeBlock.tsx             # NEW: Syntax-highlighted code
│   ├── docs/
│   │   ├── CodeExamples.tsx      # NEW: Multi-language examples
│   │   ├── ParameterTable.tsx    # NEW: Parameter documentation
│   │   ├── ResponseFormat.tsx    # NEW: Response docs
│   │   └── JanusExtensions.tsx   # NEW: Janus-specific features
│   └── Navigation.tsx            # UPDATE: Add API link

gateway/janus_gateway/
└── main.py                       # UPDATE: Enable Swagger UI paths
```

## Example Full Page Content

### Python Example (Complete)

```python
"""
Janus API - Python Example

Install: pip install openai
"""

import openai
from typing import Generator

# Initialize client
client = openai.OpenAI(
    base_url="https://janus-gateway-bqou.onrender.com/v1",
    api_key="not-required"
)

# Simple completion
def simple_chat(message: str) -> str:
    response = client.chat.completions.create(
        model="baseline-cli-agent",
        messages=[{"role": "user", "content": message}],
    )
    return response.choices[0].message.content

# Streaming completion
def stream_chat(message: str) -> Generator[str, None, None]:
    stream = client.chat.completions.create(
        model="baseline-cli-agent",
        messages=[{"role": "user", "content": message}],
        stream=True,
    )
    for chunk in stream:
        if chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content

# With memory enabled
def chat_with_memory(message: str, user_id: str) -> str:
    response = client.chat.completions.create(
        model="baseline-cli-agent",
        messages=[{"role": "user", "content": message}],
        user=user_id,
        extra_body={"enable_memory": True},
    )
    return response.choices[0].message.content

# With generation flags
def generate_image(prompt: str) -> dict:
    response = client.chat.completions.create(
        model="baseline-cli-agent",
        messages=[{"role": "user", "content": prompt}],
        extra_body={
            "generation_flags": {
                "generate_image": True
            }
        },
    )
    message = response.choices[0].message
    return {
        "content": message.content,
        "artifacts": message.artifacts or []
    }

# Usage
if __name__ == "__main__":
    # Simple
    print(simple_chat("What is 2+2?"))

    # Streaming
    for text in stream_chat("Tell me a joke"):
        print(text, end="", flush=True)
    print()

    # With memory
    print(chat_with_memory("My name is Alice", "user_123"))
    print(chat_with_memory("What's my name?", "user_123"))
```

### TypeScript Example (Complete)

```typescript
/**
 * Janus API - TypeScript Example
 *
 * Install: npm install openai
 */

import OpenAI from 'openai';

const client = new OpenAI({
  baseURL: 'https://janus-gateway-bqou.onrender.com/v1',
  apiKey: 'not-required',
});

// Simple completion
async function simpleChat(message: string): Promise<string> {
  const response = await client.chat.completions.create({
    model: 'baseline-cli-agent',
    messages: [{ role: 'user', content: message }],
  });
  return response.choices[0].message.content ?? '';
}

// Streaming completion
async function* streamChat(message: string): AsyncGenerator<string> {
  const stream = await client.chat.completions.create({
    model: 'baseline-cli-agent',
    messages: [{ role: 'user', content: message }],
    stream: true,
  });

  for await (const chunk of stream) {
    const content = chunk.choices[0]?.delta?.content;
    if (content) yield content;
  }
}

// With memory enabled
async function chatWithMemory(message: string, userId: string): Promise<string> {
  const response = await client.chat.completions.create({
    model: 'baseline-cli-agent',
    messages: [{ role: 'user', content: message }],
    user: userId,
    // @ts-ignore - Janus extension
    enable_memory: true,
  });
  return response.choices[0].message.content ?? '';
}

// With multimodal input
async function analyzeImage(imageUrl: string, question: string): Promise<string> {
  const response = await client.chat.completions.create({
    model: 'baseline-cli-agent',
    messages: [
      {
        role: 'user',
        content: [
          { type: 'text', text: question },
          { type: 'image_url', image_url: { url: imageUrl, detail: 'high' } },
        ],
      },
    ],
  });
  return response.choices[0].message.content ?? '';
}

// Usage
async function main() {
  // Simple
  console.log(await simpleChat('What is 2+2?'));

  // Streaming
  for await (const text of streamChat('Tell me a joke')) {
    process.stdout.write(text);
  }
  console.log();

  // Image analysis
  console.log(await analyzeImage(
    'https://upload.wikimedia.org/wikipedia/commons/a/a7/Camponotus_flavomarginatus_ant.jpg',
    'What insect is this?'
  ));
}

main();
```

## Related Specs

- `specs/86_generative_ui_responses.md` - Generative UI format
- `specs/72_memory_service_backend.md` - Memory service (planned)
- `specs/78_generation_flags.md` - Generation flags (planned)
- `specs/80_debug_mode.md` - Debug streaming (planned)

NR_OF_TRIES: 0
