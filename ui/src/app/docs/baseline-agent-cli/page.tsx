import Link from 'next/link';

import { Header, Footer } from '@/components/landing';
import { CodeBlock } from '@/components/docs/CodeBlock';
import { ConfigTable, type ConfigEntry } from '@/components/docs/ConfigTable';
import { MermaidDiagram } from '@/components/docs/MermaidDiagram';

const features = [
  {
    title: 'Dual-path routing',
    description: 'Keyword and LLM checks route simple requests to a fast path while complex tasks go to the agent.',
  },
  {
    title: 'Sandboxed agent execution',
    description: 'Claude Code runs inside Sandy with full tool access and isolated filesystem permissions.',
  },
  {
    title: 'Streaming with artifacts',
    description: 'SSE responses include reasoning content plus artifact URLs for generated files.',
  },
  {
    title: 'Chutes integrations',
    description: 'LLM, image generation, TTS, and web search are routed through Chutes APIs.',
  },
  {
    title: 'Deep research support',
    description: 'Chutes search with citations powers research-heavy prompts.',
  },
  {
    title: 'Configurable routing',
    description: 'Fine-tune complexity thresholds, routing models, and model router behavior.',
  },
];

const howItWorksSteps = [
  'Receives OpenAI-compatible chat completion requests.',
  'Runs keyword-based complexity detection followed by LLM verification.',
  'Routes simple prompts to a fast LLM path or complex prompts to the agent sandbox.',
  'Executes the Claude Code CLI agent with full tool access.',
  'Streams responses with reasoning content and artifacts over SSE.',
];

const agentCapabilities = [
  {
    name: 'Claude Code',
    summary: 'Default CLI agent with full sandbox tooling.',
    badges: ['Shell', 'Web', 'Downloads', 'Code'],
  },
  {
    name: 'Roo Code CLI',
    summary: 'Experimental CLI agent for autonomous workflows.',
    badges: ['TBD'],
  },
  {
    name: 'Cline CLI',
    summary: 'Experimental CLI agent with multi-tool support.',
    badges: ['TBD'],
  },
  {
    name: 'OpenCode',
    summary: 'Non-interactive CLI runner (capabilities pending validation).',
    badges: ['TBD'],
  },
  {
    name: 'Codex',
    summary: 'CLI output capture under investigation.',
    badges: ['TBD'],
  },
  {
    name: 'Aider',
    summary: 'Code editing workflows only.',
    badges: ['Code'],
  },
];

const configSections: Array<{ title: string; description?: string; entries: ConfigEntry[] }> = [
  {
    title: 'Server configuration',
    entries: [
      {
        name: 'BASELINE_AGENT_CLI_HOST',
        defaultValue: '0.0.0.0',
        description: 'Server host binding for the API.',
      },
      {
        name: 'BASELINE_AGENT_CLI_PORT',
        defaultValue: '8080',
        description: 'Server port for the API.',
      },
      {
        name: 'BASELINE_AGENT_CLI_DEBUG',
        defaultValue: 'false',
        description: 'Enable debug logging and verbose output.',
      },
    ],
  },
  {
    title: 'Chutes API configuration',
    description: 'Chutes provides OpenAI-compatible inference for LLM and tools.',
    entries: [
      {
        name: 'BASELINE_AGENT_CLI_OPENAI_API_KEY',
        defaultValue: '-',
        description: 'Chutes API key (named for OpenAI client compatibility).',
      },
      {
        name: 'BASELINE_AGENT_CLI_OPENAI_BASE_URL',
        defaultValue: '-',
        description: 'Legacy alias for the Chutes API base URL.',
      },
      {
        name: 'BASELINE_AGENT_CLI_CHUTES_API_BASE',
        defaultValue: 'https://llm.chutes.ai/v1',
        description: 'Primary Chutes API base URL.',
      },
      {
        name: 'BASELINE_AGENT_CLI_MODEL',
        defaultValue: 'janus-router',
        description: 'Model name exposed to clients.',
      },
      {
        name: 'BASELINE_AGENT_CLI_DIRECT_MODEL',
        defaultValue: 'zai-org/GLM-4.7-TEE',
        description: 'Direct model used on the fast path when routing allows.',
      },
    ],
  },
  {
    title: 'Vision routing',
    entries: [
      {
        name: 'BASELINE_AGENT_CLI_VISION_MODEL_PRIMARY',
        defaultValue: 'Qwen/Qwen3-VL-235B-A22B-Instruct',
        description: 'Primary vision model for image requests.',
      },
      {
        name: 'BASELINE_AGENT_CLI_VISION_MODEL_FALLBACK',
        defaultValue: 'chutesai/Mistral-Small-3.2-24B-Instruct-2506',
        description: 'Fallback vision model for image requests.',
      },
      {
        name: 'BASELINE_AGENT_CLI_VISION_MODEL_TIMEOUT',
        defaultValue: '60.0',
        description: 'Timeout for vision model requests (seconds).',
      },
      {
        name: 'BASELINE_AGENT_CLI_ENABLE_VISION_ROUTING',
        defaultValue: 'true',
        description: 'Route image requests to vision models.',
      },
    ],
  },
  {
    title: 'Sandy sandbox',
    entries: [
      {
        name: 'SANDY_BASE_URL',
        defaultValue: '-',
        description: 'Sandy API base URL for agent execution.',
      },
      {
        name: 'SANDY_API_KEY',
        defaultValue: '-',
        description: 'Sandy API key for sandbox access.',
      },
      {
        name: 'BASELINE_AGENT_CLI_SANDY_TIMEOUT',
        defaultValue: '300',
        description: 'Sandbox timeout in seconds.',
      },
      {
        name: 'JANUS_ARTIFACT_PORT',
        defaultValue: '5173',
        description: 'Sandbox artifact server port.',
      },
      {
        name: 'JANUS_ARTIFACTS_DIR',
        defaultValue: '/workspace/artifacts',
        description: 'Filesystem path for sandbox artifacts.',
      },
    ],
  },
  {
    title: 'Agent configuration',
    entries: [
      {
        name: 'BASELINE_AGENT_CLI_AGENT_PACK_PATH',
        defaultValue: './agent-pack',
        description: 'Path to agent documentation and prompts.',
      },
      {
        name: 'BASELINE_AGENT_CLI_SYSTEM_PROMPT_PATH',
        defaultValue: './agent-pack/prompts/system.md',
        description: 'System prompt for the CLI agent.',
      },
      {
        name: 'BASELINE_AGENT_CLI_ENABLE_WEB_SEARCH',
        defaultValue: 'true',
        description: 'Enable web search tools.',
      },
      {
        name: 'BASELINE_AGENT_CLI_ENABLE_CODE_EXECUTION',
        defaultValue: 'true',
        description: 'Enable code execution tools.',
      },
      {
        name: 'BASELINE_AGENT_CLI_ENABLE_FILE_TOOLS',
        defaultValue: 'true',
        description: 'Enable file tooling.',
      },
      {
        name: 'JANUS_BASELINE_AGENT',
        defaultValue: 'claude-code',
        description: 'CLI agent command invoked in the sandbox.',
      },
    ],
  },
  {
    title: 'Routing configuration',
    entries: [
      {
        name: 'BASELINE_AGENT_CLI_ALWAYS_USE_AGENT',
        defaultValue: 'false',
        description: 'Force all requests onto the agent path.',
      },
      {
        name: 'BASELINE_AGENT_CLI_LLM_ROUTING_MODEL',
        defaultValue: 'zai-org/GLM-4.7-Flash',
        description: 'Fast model used for routing decisions.',
      },
      {
        name: 'BASELINE_AGENT_CLI_LLM_ROUTING_TIMEOUT',
        defaultValue: '3.0',
        description: 'Routing check timeout (seconds).',
      },
      {
        name: 'BASELINE_AGENT_CLI_COMPLEXITY_THRESHOLD',
        defaultValue: '100',
        description: 'Token threshold for complexity detection.',
      },
    ],
  },
  {
    title: 'Model router',
    entries: [
      {
        name: 'BASELINE_AGENT_CLI_USE_MODEL_ROUTER',
        defaultValue: 'true',
        description: 'Enable the local composite model router.',
      },
      {
        name: 'BASELINE_AGENT_CLI_ROUTER_HOST',
        defaultValue: '127.0.0.1',
        description: 'Router host.',
      },
      {
        name: 'BASELINE_AGENT_CLI_ROUTER_PORT',
        defaultValue: '8000',
        description: 'Router port.',
      },
    ],
  },
  {
    title: 'Container overrides',
    description: 'Alternative environment variables honored by container deployments.',
    entries: [
      {
        name: 'HOST',
        defaultValue: '-',
        description: 'Container host override.',
      },
      {
        name: 'PORT',
        defaultValue: '-',
        description: 'Container port override.',
      },
      {
        name: 'DEBUG',
        defaultValue: '-',
        description: 'Container debug override.',
      },
      {
        name: 'LOG_LEVEL',
        defaultValue: '-',
        description: 'Container log level override.',
      },
      {
        name: 'OPENAI_API_KEY',
        defaultValue: '-',
        description: 'Container OpenAI/Chutes API key alias.',
      },
      {
        name: 'OPENAI_BASE_URL',
        defaultValue: '-',
        description: 'Container OpenAI/Chutes base URL alias.',
      },
    ],
  },
];

const gettingStartedCode = `# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install with dev dependencies
pip install -e ".[dev]"

# Run the baseline
python -m janus_baseline_agent_cli.main`;

const simpleRequest = `curl -X POST http://localhost:8080/v1/chat/completions \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "baseline",
    "messages": [{"role": "user", "content": "What is 2+2?"}],
    "stream": true
  }'`;

const complexRequest = `curl -X POST http://localhost:8080/v1/chat/completions \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "baseline",
    "messages": [{"role": "user", "content": "Generate an image of a sunset and analyze its colors"}],
    "stream": true
  }'`;

const agentCliDiagram = `flowchart TB
    subgraph Request ["Incoming Request"]
        REQ["POST /v1/chat/completions"]
    end

    subgraph Routing ["Complexity Detection"]
        DETECT["Complexity Detector"]
        KEYWORDS["Keyword Check"]
        LLM_VERIFY["LLM Verification (GLM-4.7-Flash)"]
    end

    subgraph FastPath ["Fast Path (Simple Requests)"]
        FAST_LLM["Direct LLM Call"]
        FAST_STREAM["Stream Response"]
    end

    subgraph ComplexPath ["Complex Path (Agent Sandbox)"]
        SANDY["Sandy Sandbox"]
        AGENT["Claude Code CLI Agent"]
        TOOLS["Available Tools"]
    end

    subgraph Tools ["Agent Capabilities"]
        SEARCH["Web Search"]
        CODE["Code Execution"]
        FILES["File Operations"]
        CHUTES_API["Chutes API (Images, TTS, LLM)"]
    end

    subgraph Response ["Response"]
        SSE["SSE Stream"]
        REASONING["reasoning_content"]
        CONTENT["content"]
        ARTIFACTS["artifacts (files)"]
    end

    REQ --> DETECT
    DETECT --> KEYWORDS
    KEYWORDS -->|"Complex keywords found"| SANDY
    KEYWORDS -->|"No keywords match"| LLM_VERIFY
    LLM_VERIFY -->|"needs_agent: true"| SANDY
    LLM_VERIFY -->|"needs_agent: false"| FAST_LLM
    LLM_VERIFY -->|"Error/Timeout"| SANDY

    FAST_LLM --> FAST_STREAM
    FAST_STREAM --> SSE

    SANDY --> AGENT
    AGENT --> TOOLS
    TOOLS --> SEARCH
    TOOLS --> CODE
    TOOLS --> FILES
    TOOLS --> CHUTES_API
    AGENT --> SSE

    SSE --> REASONING
    SSE --> CONTENT
    SSE --> ARTIFACTS`;

export default function BaselineAgentCliPage() {
  return (
    <div className="min-h-screen aurora-bg flex flex-col">
      <Header />
      <main className="flex-1 py-16 lg:py-24">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 space-y-12">
          <div>
            <Link
              href="/competition"
              className="text-[#63D297] hover:underline inline-flex items-center gap-2"
            >
              <svg
                className="w-4 h-4"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.6"
              >
                <path d="M19 12H5" />
                <path d="M11 6l-6 6 6 6" />
              </svg>
              Back to Competition
            </Link>
          </div>

          <header className="space-y-4">
            <h1 className="text-3xl sm:text-4xl font-semibold text-[#F3F4F6]">
              CLI Agent Baseline
            </h1>
            <p className="text-lg text-[#9CA3AF]">
              Sandbox-based reference implementation using a Claude Code CLI agent to handle
              complex work while a fast path serves simple requests.
            </p>
          </header>

          <section className="space-y-4">
            <h2 className="text-2xl font-semibold text-[#F3F4F6]">Architecture</h2>
            <MermaidDiagram chart={agentCliDiagram} ariaLabel="CLI agent baseline architecture" />
          </section>

          <section className="space-y-4">
            <h2 className="text-2xl font-semibold text-[#F3F4F6]">How It Works</h2>
            <ol className="space-y-3 text-sm text-[#D1D5DB] list-decimal list-inside">
              {howItWorksSteps.map((step) => (
                <li key={step}>{step}</li>
              ))}
            </ol>
          </section>

          <section className="space-y-4">
            <h2 className="text-2xl font-semibold text-[#F3F4F6]">Request Flow</h2>
            <p className="text-sm text-[#9CA3AF]">
              Use the same OpenAI-compatible payloads. Simple requests route through the fast path,
              while complex tasks go to the CLI agent sandbox.
            </p>
            <div className="grid lg:grid-cols-2 gap-6">
              <div className="space-y-3">
                <p className="text-xs uppercase tracking-[0.2em] text-[#9CA3AF]">Simple request</p>
                <CodeBlock language="bash">{simpleRequest}</CodeBlock>
              </div>
              <div className="space-y-3">
                <p className="text-xs uppercase tracking-[0.2em] text-[#9CA3AF]">Complex request</p>
                <CodeBlock language="bash">{complexRequest}</CodeBlock>
              </div>
            </div>
          </section>

          <section className="space-y-4">
            <h2 className="text-2xl font-semibold text-[#F3F4F6]">Features</h2>
            <div className="grid sm:grid-cols-2 gap-4">
              {features.map((feature) => (
                <FeatureCard key={feature.title} {...feature} />
              ))}
            </div>
          </section>

          <section className="space-y-4">
            <h2 className="text-2xl font-semibold text-[#F3F4F6]">CLI Agent Capabilities</h2>
            <p className="text-sm text-[#9CA3AF]">
              Use <span className="text-[#F3F4F6]">JANUS_BASELINE_AGENT</span> or{' '}
              <span className="text-[#F3F4F6]">X-Baseline-Agent</span> to select the CLI agent.
              Badges reflect currently verified capabilities.
            </p>
            <div className="grid sm:grid-cols-2 gap-4">
              {agentCapabilities.map((agent) => (
                <AgentCapabilityCard key={agent.name} {...agent} />
              ))}
            </div>
          </section>

          <section className="space-y-6">
            <h2 className="text-2xl font-semibold text-[#F3F4F6]">Configuration</h2>
            <p className="text-sm text-[#9CA3AF]">
              Legacy BASELINE-prefixed variables are still accepted. Use the tables below for the
              complete list of available settings.
            </p>
            <div className="space-y-6">
              {configSections.map((section) => (
                <ConfigTable
                  key={section.title}
                  title={section.title}
                  description={section.description}
                  entries={section.entries}
                />
              ))}
            </div>
          </section>

          <section className="space-y-4">
            <h2 className="text-2xl font-semibold text-[#F3F4F6]">Getting Started</h2>
            <CodeBlock language="bash" title="Local setup">
              {gettingStartedCode}
            </CodeBlock>
          </section>

          <div className="flex justify-center">
            <a
              href="https://github.com/fstandhartinger/janus-poc/tree/main/baseline-agent-cli"
              target="_blank"
              rel="noreferrer"
              className="btn-primary inline-flex items-center gap-2"
            >
              <GithubIcon className="w-4 h-4" />
              View on GitHub
            </a>
          </div>
        </div>
      </main>
      <Footer />
    </div>
  );
}

function FeatureCard({ title, description }: { title: string; description: string }) {
  return (
    <div className="glass-card p-4 space-y-2">
      <h3 className="text-lg font-semibold text-[#F3F4F6]">{title}</h3>
      <p className="text-sm text-[#9CA3AF]">{description}</p>
    </div>
  );
}

function AgentCapabilityCard({
  name,
  summary,
  badges,
}: {
  name: string;
  summary: string;
  badges: string[];
}) {
  return (
    <div className="glass-card p-4 space-y-3">
      <div className="space-y-1">
        <h3 className="text-lg font-semibold text-[#F3F4F6]">{name}</h3>
        <p className="text-sm text-[#9CA3AF]">{summary}</p>
      </div>
      <div className="flex flex-wrap gap-2">
        {badges.map((badge) => (
          <span
            key={`${name}-${badge}`}
            className={`px-2 py-1 rounded-md text-[10px] uppercase tracking-[0.2em] ${
              badge === 'TBD'
                ? 'bg-white/10 text-[#9CA3AF]'
                : 'bg-[#63D297]/15 text-[#63D297]'
            }`}
          >
            {badge}
          </span>
        ))}
      </div>
    </div>
  );
}

function GithubIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="currentColor"
      aria-hidden="true"
    >
      <path d="M12 2C6.48 2 2 6.58 2 12.26c0 4.5 2.87 8.31 6.84 9.66.5.1.68-.22.68-.49 0-.24-.01-.87-.01-1.7-2.78.62-3.37-1.38-3.37-1.38-.46-1.2-1.11-1.52-1.11-1.52-.9-.64.07-.63.07-.63 1 .07 1.53 1.05 1.53 1.05.9 1.57 2.36 1.12 2.94.86.09-.67.35-1.12.63-1.38-2.22-.26-4.56-1.14-4.56-5.08 0-1.12.39-2.03 1.03-2.75-.1-.26-.45-1.3.1-2.7 0 0 .84-.27 2.75 1.03.8-.23 1.66-.35 2.52-.35.86 0 1.72.12 2.52.35 1.9-1.3 2.74-1.03 2.74-1.03.55 1.4.2 2.44.1 2.7.64.72 1.03 1.63 1.03 2.75 0 3.95-2.35 4.81-4.58 5.06.36.32.68.94.68 1.9 0 1.37-.01 2.47-.01 2.8 0 .27.18.6.69.49 3.96-1.35 6.82-5.16 6.82-9.66C22 6.58 17.52 2 12 2z" />
    </svg>
  );
}
