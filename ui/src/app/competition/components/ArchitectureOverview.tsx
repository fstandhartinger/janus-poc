import { MermaidDiagram } from '@/components/MermaidDiagram';

const architectureDiagram = `flowchart TB
    subgraph Users ["Users & Products"]
        U1[Janus Chat]
        U2[API Clients]
        U3[Third-party Apps]
    end

    subgraph Gateway ["Janus Gateway"]
        GW[API Gateway]
        LB[Load Balancer]
        RT[Router]
    end

    subgraph Execution ["Chutes TEE Nodes"]
        subgraph Container ["Your Implementation"]
            API["/v1/chat/completions"]
            IMPL[Your Code]
        end
    end

    subgraph Services ["Platform Services"]
        PROXY[Web Proxy]
        SEARCH[Search API]
        VECTOR[Vector Index]
        SANDBOX[Code Sandbox]
        INFERENCE[Chutes Inference]
    end

    subgraph Eval ["Evaluation"]
        BENCH[Bench Runner]
        SCORE[Scoring Engine]
        LDB[Leaderboard]
    end

    U1 --> GW
    U2 --> GW
    U3 --> GW
    GW --> LB
    LB --> RT
    RT --> API
    API --> IMPL
    IMPL --> PROXY
    IMPL --> SEARCH
    IMPL --> VECTOR
    IMPL --> SANDBOX
    IMPL --> INFERENCE

    BENCH --> API
    BENCH --> SCORE
    SCORE --> LDB`;

const serviceSequenceDiagram = `sequenceDiagram
    participant Impl as Your Implementation
    participant Proxy as Web Proxy
    participant Search as Search API
    participant Sandbox as Code Sandbox
    participant Inference as Chutes Inference

    Impl->>Search: Search for "quantum entanglement"
    Search-->>Impl: Top 10 results
    Impl->>Proxy: Fetch https://physics.org/quantum
    Proxy-->>Impl: Page content
    Impl->>Inference: Call DeepSeek-V3.2 for synthesis
    Inference-->>Impl: Synthesized explanation
    Impl->>Sandbox: Execute Python visualization
    Sandbox-->>Impl: Generated image`;

const egressDiagram = `flowchart LR
    subgraph TEE ["Your Container"]
        IMPL[Implementation]
    end

    subgraph Allowed ["Allowed"]
        S1[proxy.janus.rodeo]
        S2[search.janus.rodeo]
        S3[vector.janus.rodeo]
        S4[sandbox.janus.rodeo]
        S5[api.chutes.ai]
    end

    subgraph Blocked ["Blocked"]
        B1[Other APIs]
        B2[Arbitrary URLs]
        B3[Internal services]
    end

    IMPL --> S1
    IMPL --> S2
    IMPL --> S3
    IMPL --> S4
    IMPL --> S5
    IMPL -.->|Blocked| B1
    IMPL -.->|Blocked| B2
    IMPL -.->|Blocked| B3`;

const requestExample = `POST /v1/chat/completions
{
  "model": "janus",
  "messages": [{"role": "user", "content": "Explain quantum entanglement"}],
  "stream": true
}`;

const gatewayRouting = [
  'Validates the request format.',
  'Selects the target implementation (current #1 or specified).',
  'Routes to the appropriate TEE node.',
];

const teeExecution = [
  'Runs inside a Chutes CPU TEE node (isolated, attested).',
  'Has access to platform services via whitelisted endpoints.',
  'Generates a response using whatever logic you build.',
];

const streamingNotes = [
  'Reasoning tokens via reasoning_content field.',
  'Content tokens via content field.',
  'Continuous streaming, not batched.',
];

const teeIsolation = [
  'Memory encryption: RAM is encrypted; host cannot read your data.',
  'Attestation: proof that your code runs unmodified.',
  'Isolation: no access to host filesystem or other containers.',
];

const whitelistEnforcement = [
  'All outbound connections are routed through a proxy.',
  'Only whitelisted domains are allowed.',
  'Connection attempts to other hosts are logged and blocked.',
];

const secretsManagement = [
  'CHUTES_API_KEY injected as an environment variable.',
  'No hardcoded secrets; use env vars in your code.',
  'Platform keys rotate regularly.',
];

const monitoring = [
  'Request/response logging (content redacted).',
  'Resource usage tracking.',
  'Anomaly detection for unusual patterns.',
];

const platformServices = [
  {
    name: 'Web Proxy',
    endpoint: 'https://proxy.janus.rodeo',
    description: 'Fetch web pages for research and information gathering.',
    code: `import httpx

response = httpx.get(
    "https://proxy.janus.rodeo/fetch",
    params={"url": "https://example.com/article"}
)
content = response.json()["content"]  # Markdown-formatted`,
    features: [
      'Converts HTML to clean markdown.',
      'Respects robots.txt.',
      'Rate limited: 10 requests/minute.',
      'Max page size: 1MB.',
    ],
  },
  {
    name: 'Search API',
    endpoint: 'https://search.janus.rodeo',
    description: 'Web search for finding relevant information.',
    code: `import httpx

response = httpx.post(
    "https://search.janus.rodeo/search",
    json={"query": "quantum entanglement explained", "num_results": 10}
)
results = response.json()["results"]
# [{"title": "...", "url": "...", "snippet": "..."}, ...]`,
    features: [
      'Powered by Brave Search API.',
      'Returns title, URL, snippet.',
      'Rate limited: 20 searches/minute.',
    ],
  },
  {
    name: 'Vector Index',
    endpoint: 'https://vector.janus.rodeo',
    description: 'Semantic search over indexed knowledge bases.',
    code: `import httpx

response = httpx.post(
    "https://vector.janus.rodeo/query",
    json={"query": "How does TCP handshake work?", "top_k": 5}
)
chunks = response.json()["chunks"]
# [{"content": "...", "source": "...", "score": 0.92}, ...]`,
    features: [
      'Pre-indexed documentation (Chutes, Bittensor, common frameworks).',
      'Custom index upload (future feature).',
      'Rate limited: 50 queries/minute.',
    ],
  },
  {
    name: 'Code Sandbox',
    endpoint: 'https://sandbox.janus.rodeo',
    description: 'Execute code safely in an isolated environment.',
    code: `import httpx

response = httpx.post(
    "https://sandbox.janus.rodeo/execute",
    json={
        "language": "python",
        "code": "print(2 + 2)",
        "timeout": 30
    }
)
result = response.json()
# {"stdout": "4\\n", "stderr": "", "exit_code": 0}`,
    features: [
      'Supported languages: Python, JavaScript, Bash, Go, Rust.',
      'Timeout: max 60 seconds.',
      'Memory: max 512MB.',
      'File I/O available within sandbox.',
      'Network access: none (sandbox is isolated).',
    ],
  },
  {
    name: 'Chutes Inference',
    endpoint: 'https://api.chutes.ai',
    description: 'Call any model available on Chutes.',
    code: `import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["CHUTES_API_KEY"],
    base_url="https://api.chutes.ai/v1"
)

response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Summarize this..."}]
)`,
    features: [
      'OpenAI: gpt-4o, gpt-4o-mini, o1, o1-mini.',
      'Open models: Llama, Mistral, Qwen, DeepSeek.',
      'Specialized: code, vision, embedding models.',
    ],
    note:
      'Your implementation receives a CHUTES_API_KEY environment variable with credits for platform use.',
    link: { label: 'Chutes Model Catalog', href: 'https://chutes.ai/models' },
  },
];

export function ArchitectureOverview() {
  return (
    <section className="py-16 lg:py-24 bg-[#0B111A]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-12">
        <div className="text-center space-y-4">
          <p className="text-sm uppercase tracking-[0.3em] text-[#9CA3AF]">
            Architecture overview
          </p>
          <h2 className="text-3xl sm:text-4xl font-semibold text-[#F3F4F6]">
            How the Janus Architecture Fits Together
          </h2>
          <p className="text-[#9CA3AF] max-w-3xl mx-auto">
            Janus connects users to competing intelligence implementations through a
            secure gateway, TEE execution layer, and tightly controlled platform
            services.
          </p>
        </div>

        <div className="grid lg:grid-cols-[1.1fr_0.9fr] gap-8 items-start">
          <div className="space-y-4">
            <h3 className="text-2xl font-semibold text-[#F3F4F6]">
              High-Level Architecture
            </h3>
            <p className="text-[#9CA3AF]">
              User requests flow through the Janus Gateway, route into a TEE-backed
              container, and call platform services as needed. Benchmarks run against
              the same API and feed the leaderboard.
            </p>
            <ul className="list-disc list-inside space-y-2 text-sm text-[#D1D5DB]">
              <li>Gateway validates and routes all OpenAI-compatible requests.</li>
              <li>Implementations run inside Chutes CPU TEE nodes.</li>
              <li>Platform services are available via whitelisted endpoints only.</li>
              <li>Bench runner and scoring engine update the leaderboard.</li>
            </ul>
          </div>

          <div className="glass-card p-6 overflow-x-auto">
            <MermaidDiagram chart={architectureDiagram} ariaLabel="Janus architecture diagram" />
          </div>
        </div>

        <div className="glass-card p-6 space-y-6">
          <div className="space-y-3">
            <p className="text-xs uppercase tracking-[0.2em] text-[#9CA3AF]">
              Request flow
            </p>
            <h3 className="text-2xl font-semibold text-[#F3F4F6]">Request Flow</h3>
            <p className="text-sm text-[#9CA3AF]">
              When a user sends a message, the request traverses the gateway, runs in
              a TEE container, calls platform services, and streams back to the client.
            </p>
          </div>

          <div className="grid lg:grid-cols-[1.1fr_0.9fr] gap-6">
            <div className="space-y-5">
              <div className="space-y-2">
                <p className="text-sm font-semibold text-[#F3F4F6]">1. User Request</p>
                <p className="text-sm text-[#9CA3AF]">
                  Users send OpenAI-compatible chat completion requests from Janus
                  Chat, the API, or third-party apps.
                </p>
                <pre className="bg-[#0B111A] border border-[#1F2937] rounded-xl p-4 text-xs text-[#D1D5DB] whitespace-pre-wrap">
                  {requestExample}
                </pre>
              </div>

              <div className="space-y-2">
                <p className="text-sm font-semibold text-[#F3F4F6]">2. Gateway Routing</p>
                <ul className="list-disc list-inside space-y-1 text-sm text-[#D1D5DB]">
                  {gatewayRouting.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>

              <div className="space-y-2">
                <p className="text-sm font-semibold text-[#F3F4F6]">3. TEE Execution</p>
                <ul className="list-disc list-inside space-y-1 text-sm text-[#D1D5DB]">
                  {teeExecution.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>
            </div>

            <div className="space-y-5">
              <div className="space-y-2">
                <p className="text-sm font-semibold text-[#F3F4F6]">
                  4. Platform Service Calls
                </p>
                <div className="glass p-4 rounded-2xl overflow-x-auto">
                  <MermaidDiagram
                    chart={serviceSequenceDiagram}
                    ariaLabel="Platform services sequence diagram"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <p className="text-sm font-semibold text-[#F3F4F6]">
                  5. Response Streaming
                </p>
                <ul className="list-disc list-inside space-y-1 text-sm text-[#D1D5DB]">
                  {streamingNotes.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>

              <div className="space-y-2">
                <p className="text-sm font-semibold text-[#F3F4F6]">
                  6. User Receives Response
                </p>
                <p className="text-sm text-[#9CA3AF]">
                  The gateway streams responses back to the user&apos;s client with
                  real-time updates and final completion metadata.
                </p>
              </div>
            </div>
          </div>
        </div>

        <div className="space-y-6">
          <div className="text-center space-y-3">
            <p className="text-sm uppercase tracking-[0.3em] text-[#9CA3AF]">
              Platform services
            </p>
            <h3 className="text-2xl sm:text-3xl font-semibold text-[#F3F4F6]">
              Platform Services
            </h3>
            <p className="text-[#9CA3AF] max-w-3xl mx-auto">
              Your implementation can call these services from inside the container.
              All other outbound access is blocked.
            </p>
          </div>

          <div className="grid lg:grid-cols-2 gap-6">
            {platformServices.map((service) => (
              <div key={service.name} className="glass-card p-6 space-y-4">
                <div className="space-y-2">
                  <h4 className="text-xl font-semibold text-[#F3F4F6]">
                    {service.name}
                  </h4>
                  <p className="text-sm text-[#9CA3AF]">
                    Endpoint:{' '}
                    <span className="font-mono text-[#63D297]">{service.endpoint}</span>
                  </p>
                  <p className="text-sm text-[#9CA3AF]">{service.description}</p>
                </div>
                <pre className="bg-[#0B111A] border border-[#1F2937] rounded-xl p-4 text-xs text-[#D1D5DB] whitespace-pre-wrap overflow-x-auto">
                  {service.code}
                </pre>
                <div>
                  <p className="text-sm font-semibold text-[#F3F4F6]">Features</p>
                  <ul className="mt-2 space-y-1 text-sm text-[#D1D5DB] list-disc list-inside">
                    {service.features.map((feature) => (
                      <li key={feature}>{feature}</li>
                    ))}
                  </ul>
                </div>
                {service.note ? (
                  <p className="text-xs text-[#6B7280]">{service.note}</p>
                ) : null}
                {service.link ? (
                  <a
                    href={service.link.href}
                    target="_blank"
                    rel="noreferrer"
                    className="text-sm text-[#63D297] hover:underline"
                  >
                    {service.link.label}
                  </a>
                ) : null}
              </div>
            ))}
          </div>
        </div>

        <div className="glass-card p-6 space-y-6">
          <div className="space-y-3">
            <p className="text-xs uppercase tracking-[0.2em] text-[#9CA3AF]">
              Security model
            </p>
            <h3 className="text-2xl font-semibold text-[#F3F4F6]">Security Model</h3>
            <p className="text-sm text-[#9CA3AF]">
              Janus runs submissions inside a secure, isolated environment with strict
              egress controls and operational monitoring.
            </p>
          </div>

          <div className="grid lg:grid-cols-[1.1fr_0.9fr] gap-6">
            <div className="space-y-5">
              <div className="space-y-2">
                <p className="text-sm font-semibold text-[#F3F4F6]">TEE Isolation</p>
                <ul className="list-disc list-inside space-y-1 text-sm text-[#D1D5DB]">
                  {teeIsolation.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>

              <div className="space-y-2">
                <p className="text-sm font-semibold text-[#F3F4F6]">
                  Secrets Management
                </p>
                <ul className="list-disc list-inside space-y-1 text-sm text-[#D1D5DB]">
                  {secretsManagement.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>

              <div className="space-y-2">
                <p className="text-sm font-semibold text-[#F3F4F6]">Monitoring</p>
                <ul className="list-disc list-inside space-y-1 text-sm text-[#D1D5DB]">
                  {monitoring.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>
            </div>

            <div className="glass p-4 rounded-2xl space-y-4 overflow-x-auto">
              <div className="space-y-2">
                <p className="text-xs uppercase tracking-[0.2em] text-[#9CA3AF]">
                  Network egress control
                </p>
                <MermaidDiagram
                  chart={egressDiagram}
                  ariaLabel="Network egress control diagram"
                />
              </div>
              <ul className="list-disc list-inside space-y-1 text-sm text-[#D1D5DB]">
                {whitelistEnforcement.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
