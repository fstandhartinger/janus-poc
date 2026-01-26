import Link from 'next/link';

import { CodeBlock } from '@/components/CodeBlock';
import { CodeExamples } from '@/components/docs/CodeExamples';
import { JanusExtensions } from '@/components/docs/JanusExtensions';
import { ParameterTable, type ParameterEntry } from '@/components/docs/ParameterTable';
import { ResponseFormat } from '@/components/docs/ResponseFormat';
import { Footer, Header } from '@/components/landing';

const gatewayOrigin = 'https://janus-gateway-bqou.onrender.com';
const baseUrl = `${gatewayOrigin}/v1`;
const swaggerUrl = `${gatewayOrigin}/api/docs`;
const openApiUrl = `${gatewayOrigin}/api/openapi.json`;

const tocSections = [
  { id: 'quick-start', label: 'Quick start' },
  { id: 'authentication', label: 'Authentication' },
  { id: 'endpoints', label: 'Endpoints' },
  { id: 'request-parameters', label: 'Request parameters' },
  { id: 'response-format', label: 'Response format' },
  { id: 'janus-extensions', label: 'Janus extensions' },
  { id: 'code-examples', label: 'Code examples' },
  { id: 'multimodal-input', label: 'Multimodal input' },
  { id: 'memory-features', label: 'Memory features' },
  { id: 'error-handling', label: 'Error handling' },
];

const quickStart = `curl -X POST "${baseUrl}/chat/completions" \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "baseline-cli-agent",
    "messages": [
      {"role": "user", "content": "Hello Janus"}
    ],
    "stream": true
  }'`;

const errorExample = `{
  "error": {
    "message": "The model \"baseline-cli-agent\" does not exist.",
    "type": "invalid_request_error",
    "param": "model",
    "code": "model_not_found"
  }
}`;

const multimodalPython = `# Image analysis with URL
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
)`;

const multimodalTypeScript = `// Image analysis with TypeScript
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
`;

const memoryExample = `# Enable memory for personalized responses
response = client.chat.completions.create(
    model="baseline-cli-agent",
    messages=[
        {"role": "user", "content": "Remember that my favorite color is blue"}
    ],
    user="user_abc123",  # Required for memory features
    extra_body={
        "enable_memory": True
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
`;

const standardParameters: ParameterEntry[] = [
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
      {
        name: 'role',
        type: '"user" | "assistant" | "system"',
        required: true,
        description: 'Message author role',
      },
      {
        name: 'content',
        type: 'string | ContentPart[]',
        required: true,
        description: 'Text or multimodal content',
      },
    ],
  },
  {
    name: 'stream',
    type: 'boolean',
    defaultValue: 'false',
    description: 'Enable Server-Sent Events streaming for real-time responses.',
  },
  {
    name: 'temperature',
    type: 'number',
    defaultValue: '0.7',
    description: 'Sampling temperature (0-2). Lower = more focused, higher = more creative.',
  },
  {
    name: 'max_tokens',
    type: 'integer',
    defaultValue: '4096',
    description: 'Maximum tokens to generate in the response.',
  },
  {
    name: 'user',
    type: 'string',
    description: 'Unique user identifier for memory features and usage tracking.',
  },
  {
    name: 'tools',
    type: 'array',
    description: 'Function definitions the model can call.',
  },
  {
    name: 'tool_choice',
    type: 'string | object',
    description: 'Control tool usage: "auto", "none", or specific tool.',
  },
  {
    name: 'metadata',
    type: 'object',
    description: 'Custom metadata passed through to the response.',
  },
];

const janusExtensions: ParameterEntry[] = [
  {
    name: 'competitor_id',
    type: 'string',
    description: 'Explicitly route to a specific competitor implementation.',
  },
  {
    name: 'enable_memory',
    type: 'boolean',
    defaultValue: 'false',
    description: 'Enable memory extraction and retrieval for personalized responses.',
  },
  {
    name: 'generation_flags',
    type: 'object',
    description: 'Request specific generation types.',
    children: [
      { name: 'generate_image', type: 'boolean', description: 'Request image generation' },
      { name: 'generate_video', type: 'boolean', description: 'Request video generation' },
      { name: 'generate_audio', type: 'boolean', description: 'Request audio generation' },
      { name: 'deep_research', type: 'boolean', description: 'Enable deep web research' },
      { name: 'web_search', type: 'boolean', description: 'Enable web search' },
    ],
  },
];

export default function ApiDocsPage() {
  return (
    <div className="min-h-screen aurora-bg flex flex-col">
      <Header />
      <main className="flex-1 py-16 lg:py-24">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="space-y-12">
            <header className="space-y-4">
              <p className="text-xs uppercase tracking-[0.35em] text-[#9CA3AF]">API Documentation</p>
              <h1 className="text-3xl sm:text-4xl font-semibold text-[#F3F4F6]">
                Janus API Reference
              </h1>
              <p className="text-lg text-[#9CA3AF]">
                OpenAI-compatible chat completions API with Janus extensions for artifacts,
                generative UI, memory, and intelligent agent workflows.
              </p>
              <div className="flex flex-wrap gap-3">
                <a
                  href={swaggerUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="px-4 py-2 bg-[#63D297] text-[#0B0F14] rounded-lg font-semibold text-sm"
                >
                  Swagger UI
                </a>
                <a
                  href={openApiUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="px-4 py-2 bg-white/10 rounded-lg text-sm text-[#F3F4F6] hover:bg-white/20"
                >
                  OpenAPI Spec
                </a>
              </div>
            </header>

            <div className="grid gap-10 lg:grid-cols-[220px,1fr]">
              <aside className="lg:sticky lg:top-24 h-fit bg-[#0B0F14]/95 backdrop-blur-sm lg:py-4 lg:-my-4 lg:pr-4 z-10">
                <TableOfContents />
              </aside>

              <div className="space-y-12">
                <section id="quick-start" className="space-y-4 scroll-mt-24">
                  <h2 className="text-2xl font-semibold text-[#F3F4F6]">Quick start</h2>
                  <p className="text-sm text-[#9CA3AF]">
                    The Janus API is compatible with OpenAI&apos;s chat completions API. If you&apos;re
                    already using OpenAI, change the base URL to Janus and reuse your client.
                  </p>
                  <div className="grid gap-4 sm:grid-cols-2">
                    <div className="glass-card p-4 space-y-2">
                      <p className="text-xs uppercase tracking-[0.2em] text-[#9CA3AF]">Base URL</p>
                      <p className="text-sm text-[#F3F4F6] font-mono break-all">{baseUrl}</p>
                    </div>
                    <div className="glass-card p-4 space-y-2">
                      <p className="text-xs uppercase tracking-[0.2em] text-[#9CA3AF]">Endpoint</p>
                      <p className="text-sm text-[#F3F4F6] font-mono">POST /v1/chat/completions</p>
                    </div>
                  </div>
                  <CodeBlock code={quickStart} language="bash" />
                </section>

                <section id="authentication" className="space-y-4 scroll-mt-24">
                  <h2 className="text-2xl font-semibold text-[#F3F4F6]">Authentication</h2>
                  <p className="text-sm text-[#D1D5DB]">
                    The Janus gateway is currently open access. API keys and quotas will be added
                    later; you can pass any placeholder string in the OpenAI client for now.
                  </p>
                  <div className="glass-card p-4 text-sm text-[#9CA3AF]">
                    <strong className="text-[#F3F4F6]">Tip:</strong> When API keys arrive, simply
                    swap in the key value without changing any payloads.
                  </div>
                </section>

                <section id="endpoints" className="space-y-4 scroll-mt-24">
                  <h2 className="text-2xl font-semibold text-[#F3F4F6]">Endpoints</h2>
                  <div className="grid gap-4 sm:grid-cols-3">
                    <EndpointCard
                      method="POST"
                      path="/v1/chat/completions"
                      description="Create chat completions with streaming, tools, and artifacts."
                    />
                    <EndpointCard
                      method="GET"
                      path="/v1/models"
                      description="List available models and competitor baselines."
                    />
                    <EndpointCard
                      method="GET"
                      path="/v1/artifacts/{id}"
                      description="Fetch generated artifacts by ID."
                    />
                  </div>
                </section>

                <section id="request-parameters" className="space-y-6 scroll-mt-24">
                  <h2 className="text-2xl font-semibold text-[#F3F4F6]">Request parameters</h2>
                  <ParameterTable
                    title="Standard OpenAI parameters"
                    description="All standard OpenAI chat completion fields are supported."
                    entries={standardParameters}
                  />
                  <ParameterTable
                    title="Janus extensions"
                    description="Janus-specific fields enable memory, routing, and generation controls."
                    entries={janusExtensions}
                  />
                </section>

                <section id="response-format" className="space-y-4 scroll-mt-24">
                  <h2 className="text-2xl font-semibold text-[#F3F4F6]">Response format</h2>
                  <p className="text-sm text-[#9CA3AF]">
                    Responses mirror OpenAI&apos;s schema with optional Janus fields for artifacts,
                    reasoning, and cost metadata.
                  </p>
                  <ResponseFormat />
                </section>

                <section id="janus-extensions" className="space-y-4 scroll-mt-24">
                  <h2 className="text-2xl font-semibold text-[#F3F4F6]">Janus extensions</h2>
                  <JanusExtensions />
                </section>

                <section id="code-examples" className="space-y-4 scroll-mt-24">
                  <h2 className="text-2xl font-semibold text-[#F3F4F6]">Code examples</h2>
                  <CodeExamples />
                </section>

                <section id="multimodal-input" className="space-y-4 scroll-mt-24">
                  <h2 className="text-2xl font-semibold text-[#F3F4F6]">Multimodal input</h2>
                  <p className="text-sm text-[#9CA3AF]">
                    Send image URLs or base64 data URLs inside the message content array.
                  </p>
                  <div className="grid gap-6 lg:grid-cols-2">
                    <div className="space-y-2">
                      <p className="text-xs uppercase tracking-[0.2em] text-[#9CA3AF]">Python</p>
                      <CodeBlock code={multimodalPython} language="python" />
                    </div>
                    <div className="space-y-2">
                      <p className="text-xs uppercase tracking-[0.2em] text-[#9CA3AF]">TypeScript</p>
                      <CodeBlock code={multimodalTypeScript} language="typescript" />
                    </div>
                  </div>
                </section>

                <section id="memory-features" className="space-y-4 scroll-mt-24">
                  <h2 className="text-2xl font-semibold text-[#F3F4F6]">Memory features</h2>
                  <p className="text-sm text-[#9CA3AF]">
                    Provide a stable user ID and set <span className="font-mono">enable_memory</span>
                    to persist and retrieve user memories.
                  </p>
                  <CodeBlock code={memoryExample} language="python" />
                </section>

                <section id="error-handling" className="space-y-4 scroll-mt-24">
                  <h2 className="text-2xl font-semibold text-[#F3F4F6]">Error handling</h2>
                  <p className="text-sm text-[#9CA3AF]">
                    Errors follow the OpenAI schema with an error object, code, and parameter hints.
                  </p>
                  <CodeBlock code={errorExample} language="json" />
                </section>

                <section className="space-y-4">
                  <div className="flex flex-wrap gap-3">
                    <Link href="/docs" className="btn-secondary">
                      View legacy docs
                    </Link>
                    <a
                      href={swaggerUrl}
                      target="_blank"
                      rel="noreferrer"
                      className="btn-primary"
                    >
                      Open Swagger Explorer
                    </a>
                  </div>
                </section>
              </div>
            </div>
          </div>
        </div>
      </main>
      <Footer />
    </div>
  );
}

function TableOfContents() {
  return (
    <div className="space-y-4">
      <p className="text-xs uppercase tracking-[0.35em] text-[#9CA3AF]">Contents</p>
      <div className="flex flex-wrap gap-2 lg:flex-col">
        {tocSections.map((section) => (
          <a
            key={section.id}
            href={`#${section.id}`}
            className="px-3 py-1.5 rounded-full border border-[#1F2937] text-xs uppercase tracking-[0.2em] text-[#9CA3AF] hover:text-[#F3F4F6]"
          >
            {section.label}
          </a>
        ))}
      </div>
    </div>
  );
}

function EndpointCard({
  method,
  path,
  description,
}: {
  method: string;
  path: string;
  description: string;
}) {
  return (
    <div className="glass-card p-4 space-y-3">
      <div className="flex items-center gap-2">
        <span className="px-2 py-1 text-xs font-semibold rounded bg-white/10 text-[#F3F4F6]">
          {method}
        </span>
        <span className="text-sm font-mono text-[#F3F4F6]">{path}</span>
      </div>
      <p className="text-sm text-[#9CA3AF]">{description}</p>
    </div>
  );
}
