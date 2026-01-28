# Spec 81: Baseline Documentation Pages

## Status: COMPLETE
**Priority:** Medium
**Complexity:** Low
**Prerequisites:** None

---

## Overview

Add a "Baselines" section to the competition page that briefly introduces the available baseline implementations, with links to dedicated pages for each baseline. Each baseline page explains the architecture with Mermaid diagrams and technical details.

---

## Functional Requirements

### FR-1: Baselines Section on Competition Page

Add a new section to the competition page between "How It Works" and "Prize Pool".

**Content:**
```
## Reference Baselines

We provide two reference baseline implementations to help you get started.
Each demonstrates a different approach to building a Janus-compatible intelligence engine.

┌─────────────────────────────────────┐  ┌─────────────────────────────────────┐
│  🤖 CLI Agent Baseline              │  │  🔗 LangChain Baseline              │
│                                     │  │                                     │
│  Sandbox-based approach using       │  │  In-process approach using          │
│  Claude Code CLI agent with         │  │  LangChain agents with              │
│  full tool access in isolated       │  │  direct tool integration.           │
│  environment.                       │  │                                     │
│                                     │  │                                     │
│  [View Documentation →]             │  │  [View Documentation →]             │
└─────────────────────────────────────┘  └─────────────────────────────────────┘
```

### FR-2: Baseline Cards Component

```tsx
// components/competition/BaselinesSection.tsx
import { Bot, Link2 } from 'lucide-react';
import Link from 'next/link';

const BASELINES = [
  {
    id: 'agent-cli',
    name: 'CLI Agent Baseline',
    icon: Bot,
    description: 'Sandbox-based approach using Claude Code CLI agent with full tool access in an isolated Sandy environment.',
    highlights: [
      'Dual-path routing (fast vs complex)',
      'Secure sandbox execution',
      'Full filesystem & code access',
      'Artifact generation',
    ],
    href: '/docs/baseline-agent-cli',
  },
  {
    id: 'langchain',
    name: 'LangChain Baseline',
    icon: Link2,
    description: 'In-process approach using LangChain agents with direct tool integration and streaming support.',
    highlights: [
      'LangChain agent framework',
      'In-process execution',
      'Extensible tool system',
      'Vision model routing',
    ],
    href: '/docs/baseline-langchain',
  },
];

export function BaselinesSection() {
  return (
    <section className="py-16">
      <div className="text-center mb-12">
        <h2 className="text-3xl font-bold mb-4">Reference Baselines</h2>
        <p className="text-gray-400 max-w-2xl mx-auto">
          We provide two reference implementations to help you get started.
          Each demonstrates a different architectural approach to building
          a Janus-compatible intelligence engine.
        </p>
      </div>

      <div className="grid md:grid-cols-2 gap-6 max-w-4xl mx-auto">
        {BASELINES.map((baseline) => (
          <BaselineCard key={baseline.id} baseline={baseline} />
        ))}
      </div>
    </section>
  );
}

function BaselineCard({ baseline }: { baseline: typeof BASELINES[0] }) {
  const Icon = baseline.icon;

  return (
    <Link href={baseline.href}>
      <div className="glass-card p-6 rounded-xl hover:border-moss-500/50 transition-all group cursor-pointer h-full">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 rounded-lg bg-moss-500/20">
            <Icon className="w-6 h-6 text-moss-500" />
          </div>
          <h3 className="text-xl font-semibold">{baseline.name}</h3>
        </div>

        <p className="text-gray-400 mb-4">{baseline.description}</p>

        <ul className="space-y-2 mb-6">
          {baseline.highlights.map((highlight, i) => (
            <li key={i} className="flex items-center gap-2 text-sm text-gray-300">
              <span className="w-1.5 h-1.5 rounded-full bg-moss-500" />
              {highlight}
            </li>
          ))}
        </ul>

        <div className="flex items-center gap-2 text-moss-500 group-hover:text-moss-400 transition-colors">
          <span className="text-sm font-medium">View Documentation</span>
          <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
        </div>
      </div>
    </Link>
  );
}
```

### FR-3: CLI Agent Baseline Documentation Page

Create `/docs/baseline-agent-cli` page with full technical documentation.

**Page Structure:**
1. Overview
2. Architecture Diagram (Mermaid)
3. How It Works
4. Request Flow
5. Configuration
6. Getting Started

```tsx
// app/docs/baseline-agent-cli/page.tsx
export default function BaselineAgentCliPage() {
  return (
    <div className="container mx-auto px-4 py-16 max-w-4xl">
      <div className="mb-8">
        <Link href="/competition" className="text-moss-500 hover:underline">
          ← Back to Competition
        </Link>
      </div>

      <h1 className="text-4xl font-bold mb-4">CLI Agent Baseline</h1>
      <p className="text-xl text-gray-400 mb-8">
        Sandbox-based reference implementation using Claude Code CLI agent
      </p>

      {/* Architecture Diagram */}
      <section className="mb-12">
        <h2 className="text-2xl font-semibold mb-4">Architecture</h2>
        <MermaidDiagram chart={AGENT_CLI_DIAGRAM} />
      </section>

      {/* How It Works */}
      <section className="mb-12">
        <h2 className="text-2xl font-semibold mb-4">How It Works</h2>
        <div className="prose prose-invert">
          <ol>
            <li><strong>Request Reception:</strong> Receives OpenAI-compatible chat completion requests</li>
            <li><strong>Complexity Detection:</strong> Analyzes request using keyword matching + LLM verification</li>
            <li><strong>Path Selection:</strong> Routes to fast path (direct LLM) or agent path (sandbox)</li>
            <li><strong>Agent Execution:</strong> Claude Code agent runs with full tool access</li>
            <li><strong>Response Streaming:</strong> SSE stream with reasoning_content and artifacts</li>
          </ol>
        </div>
      </section>

      {/* Features */}
      <section className="mb-12">
        <h2 className="text-2xl font-semibold mb-4">Features</h2>
        <div className="grid md:grid-cols-2 gap-4">
          {FEATURES.map((feature) => (
            <FeatureCard key={feature.title} {...feature} />
          ))}
        </div>
      </section>

      {/* Configuration */}
      <section className="mb-12">
        <h2 className="text-2xl font-semibold mb-4">Configuration</h2>
        <ConfigTable config={AGENT_CLI_CONFIG} />
      </section>

      {/* Getting Started */}
      <section className="mb-12">
        <h2 className="text-2xl font-semibold mb-4">Getting Started</h2>
        <CodeBlock language="bash">{GETTING_STARTED_CODE}</CodeBlock>
      </section>

      {/* GitHub Link */}
      <div className="flex justify-center">
        <a
          href="https://github.com/fstandhartinger/janus-poc/tree/main/baseline-agent-cli"
          target="_blank"
          className="btn-primary"
        >
          <Github className="w-4 h-4 mr-2" />
          View on GitHub
        </a>
      </div>
    </div>
  );
}

const AGENT_CLI_DIAGRAM = `
flowchart TB
    subgraph Request ["Incoming Request"]
        REQ["POST /v1/chat/completions"]
    end

    subgraph Routing ["Complexity Detection"]
        DETECT["Complexity Detector"]
        KEYWORDS["Keyword Check"]
        LLM_VERIFY["LLM Verification"]
    end

    subgraph FastPath ["Fast Path (Simple)"]
        FAST_LLM["Direct LLM Call"]
    end

    subgraph AgentPath ["Agent Path (Complex)"]
        SANDY["Sandy Sandbox"]
        AGENT["Claude Code Agent"]
    end

    subgraph Tools ["Agent Capabilities"]
        SEARCH["Web Search"]
        CODE["Code Execution"]
        FILES["File Operations"]
        IMG["Image Generation"]
        TTS["Text-to-Speech"]
    end

    subgraph Response ["Response"]
        SSE["SSE Stream"]
    end

    REQ --> DETECT
    DETECT --> KEYWORDS
    KEYWORDS -->|"Complex"| SANDY
    KEYWORDS -->|"Simple"| LLM_VERIFY
    LLM_VERIFY -->|"needs_agent"| SANDY
    LLM_VERIFY -->|"simple"| FAST_LLM

    FAST_LLM --> SSE
    SANDY --> AGENT
    AGENT --> Tools
    AGENT --> SSE
`;
```

### FR-4: LangChain Baseline Documentation Page

Create `/docs/baseline-langchain` page with full technical documentation.

```tsx
// app/docs/baseline-langchain/page.tsx
export default function BaselineLangChainPage() {
  return (
    <div className="container mx-auto px-4 py-16 max-w-4xl">
      {/* Similar structure to agent-cli page */}

      <h1 className="text-4xl font-bold mb-4">LangChain Baseline</h1>
      <p className="text-xl text-gray-400 mb-8">
        In-process reference implementation using LangChain agents
      </p>

      {/* Architecture Diagram */}
      <section className="mb-12">
        <h2 className="text-2xl font-semibold mb-4">Architecture</h2>
        <MermaidDiagram chart={LANGCHAIN_DIAGRAM} />
      </section>

      {/* ... rest of sections ... */}
    </div>
  );
}

const LANGCHAIN_DIAGRAM = `
flowchart TB
    subgraph Request ["Incoming Request"]
        REQ["POST /v1/chat/completions"]
    end

    subgraph Processing ["Request Processing"]
        VISION_CHECK["Vision Check"]
        AGENT_CREATE["Create LangChain Agent"]
    end

    subgraph VisionPath ["Vision Path"]
        VISION_LLM["Vision Model"]
    end

    subgraph AgentPath ["Agent Path"]
        AGENT["LangChain Agent"]
        TOOLS["Tool Executor"]
    end

    subgraph Tools ["Available Tools"]
        IMG["image_generation"]
        TTS["text_to_speech"]
        SEARCH["web_search"]
        CODE["code_execution"]
    end

    subgraph Response ["Response"]
        SSE["SSE Stream"]
    end

    REQ --> VISION_CHECK
    VISION_CHECK -->|"Has Images"| VISION_LLM
    VISION_CHECK -->|"No Images"| AGENT_CREATE
    VISION_LLM --> SSE

    AGENT_CREATE --> AGENT
    AGENT --> TOOLS
    TOOLS --> IMG & TTS & SEARCH & CODE
    AGENT --> SSE
`;
```

### FR-5: Mermaid Diagram Component

Reusable component for rendering Mermaid diagrams with Chutes styling.

```tsx
// components/docs/MermaidDiagram.tsx
'use client';

import mermaid from 'mermaid';
import { useEffect, useRef, useState } from 'react';

interface MermaidDiagramProps {
  chart: string;
  className?: string;
}

export function MermaidDiagram({ chart, className }: MermaidDiagramProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [svg, setSvg] = useState<string>('');

  useEffect(() => {
    mermaid.initialize({
      startOnLoad: false,
      theme: 'base',
      themeVariables: {
        primaryColor: '#1a1a2e',
        primaryTextColor: '#ffffff',
        primaryBorderColor: '#63D297',
        lineColor: '#63D297',
        secondaryColor: '#16213e',
        tertiaryColor: '#0f0f23',
        background: '#0a0a0f',
        mainBkg: '#1a1a2e',
        nodeBorder: '#333',
        clusterBkg: 'rgba(99, 210, 151, 0.1)',
        clusterBorder: '#63D297',
        titleColor: '#ffffff',
        edgeLabelBackground: '#1a1a2e',
      },
    });

    const renderDiagram = async () => {
      const id = `mermaid-${Math.random().toString(36).slice(2)}`;
      const { svg } = await mermaid.render(id, chart);
      setSvg(svg);
    };

    renderDiagram();
  }, [chart]);

  return (
    <div
      ref={containerRef}
      className={cn(
        'glass-card p-6 rounded-xl overflow-auto',
        className
      )}
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  );
}
```

---

## Files to Create

| File | Purpose |
|------|---------|
| `ui/src/components/competition/BaselinesSection.tsx` | Baselines overview cards |
| `ui/src/app/docs/baseline-agent-cli/page.tsx` | CLI agent documentation |
| `ui/src/app/docs/baseline-langchain/page.tsx` | LangChain documentation |
| `ui/src/components/docs/MermaidDiagram.tsx` | Reusable Mermaid renderer |
| `ui/src/components/docs/CodeBlock.tsx` | Code snippet component |
| `ui/src/components/docs/ConfigTable.tsx` | Configuration table component |

## Files to Modify

| File | Changes |
|------|---------|
| `ui/src/app/competition/page.tsx` | Add BaselinesSection |

---

## UI/UX Design

### Competition Page Section

```
┌─────────────────────────────────────────────────────────────────┐
│                     Reference Baselines                         │
│                                                                 │
│  We provide two reference implementations to help you get       │
│  started. Each demonstrates a different architectural approach. │
│                                                                 │
│  ┌─────────────────────────┐  ┌─────────────────────────────┐  │
│  │  🤖 CLI Agent Baseline  │  │  🔗 LangChain Baseline      │  │
│  │                         │  │                             │  │
│  │  Sandbox-based using    │  │  In-process using           │  │
│  │  Claude Code CLI agent  │  │  LangChain agents           │  │
│  │                         │  │                             │  │
│  │  • Dual-path routing    │  │  • LangChain framework      │  │
│  │  • Secure sandbox       │  │  • In-process execution     │  │
│  │  • Full tool access     │  │  • Extensible tools         │  │
│  │  • Artifact generation  │  │  • Vision routing           │  │
│  │                         │  │                             │  │
│  │  View Documentation →   │  │  View Documentation →       │  │
│  └─────────────────────────┘  └─────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Documentation Page Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  ← Back to Competition                                          │
│                                                                 │
│  CLI Agent Baseline                                             │
│  Sandbox-based reference implementation                         │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                                                         │   │
│  │               [Mermaid Architecture Diagram]            │   │
│  │                                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ## How It Works                                                │
│  1. Request Reception...                                        │
│  2. Complexity Detection...                                     │
│                                                                 │
│  ## Features                                                    │
│  ┌──────────────┐  ┌──────────────┐                            │
│  │ Dual Routing │  │ Sandbox Exec │                            │
│  └──────────────┘  └──────────────┘                            │
│                                                                 │
│  ## Configuration                                               │
│  | Variable | Default | Description |                          │
│  |----------|---------|-------------|                          │
│                                                                 │
│  ## Getting Started                                             │
│  ```bash                                                        │
│  pip install -e ".[dev]"                                        │
│  python -m janus_baseline_agent_cli.main                        │
│  ```                                                            │
│                                                                 │
│              [View on GitHub]                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Acceptance Criteria

- [ ] Baselines section appears on competition page
- [ ] Two baseline cards with brief descriptions
- [ ] Links navigate to respective documentation pages
- [ ] Documentation pages have Mermaid architecture diagrams
- [ ] Diagrams use Chutes design system colors
- [ ] Configuration tables show all environment variables
- [ ] Getting started code blocks are copy-able
- [ ] GitHub links point to correct repositories
- [ ] Mobile responsive layout

---

## Testing Checklist

- [ ] Baselines section renders correctly
- [ ] Cards are clickable and navigate to docs
- [ ] Mermaid diagrams render without errors
- [ ] Diagrams are readable on all screen sizes
- [ ] Back to Competition link works
- [ ] Code blocks have syntax highlighting
- [ ] Configuration tables are complete
- [ ] External GitHub links open in new tab

---

## Notes

- Pull Mermaid diagram content from README.md files
- Keep explanations concise - link to GitHub for full details
- Consider adding comparison table between baselines
- Future: Add more baselines as community contributes them

NR_OF_TRIES: 1
