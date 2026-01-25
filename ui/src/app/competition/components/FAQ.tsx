'use client';

import { useState, type ReactNode } from 'react';

const faqSections: { title: string; items: { question: string; answer: ReactNode }[] }[] = [
  {
    title: 'General',
    items: [
      {
        question: 'What is the Janus Competition?',
        answer: (
          <>
            <p>
              The Janus Competition is an open arena where developers compete to build
              the best intelligence engine. You submit an OpenAI-compatible (Open AI)
              API endpoint, and your implementation is scored across dozens of tasks
              measuring quality, speed, cost, and more.
            </p>
            <p>
              The top implementation earns rewards from an accumulating prize pool that
              grows as long as it holds #1 on the leaderboard (leader board).
            </p>
          </>
        ),
      },
      {
        question:
          'What is the difference between an "agent" and an "intelligence implementation"?',
        answer: (
          <p>
            We use &quot;intelligence implementation&quot; because it is more inclusive.
            Your submission does not have to be an agent with tools and loops. It can be
            a simple model router, a workflow engine, a multi-agent system, or anything
            else. What matters is that it delivers intelligent responses through a
            standard API.
          </p>
        ),
      },
      {
        question: 'Do I need to build everything from scratch?',
        answer: (
          <p>
            No. We encourage you to start from an existing implementation. Fork the
            baseline, study the current leader, and make incremental improvements. All
            submissions are open source, so you can learn from and build upon the
            community&apos;s work.
          </p>
        ),
      },
      {
        question: 'What technology stack can I use?',
        answer: (
          <>
            <p>Anything that can run in a Docker container and expose an HTTP API.</p>
            <ul className="list-disc list-inside space-y-2">
              <li>Python (FastAPI, Flask) calling LLM APIs</li>
              <li>Node.js with LangChain or custom orchestration</li>
              <li>Rust for performance-critical routing</li>
              <li>CLI agents like Claude Code, Aider, or OpenHands</li>
              <li>Workflow engines like n8n, LangGraph, or CrewAI</li>
            </ul>
          </>
        ),
      },
    ],
  },
  {
    title: 'Submissions',
    items: [
      {
        question: 'What do I actually submit?',
        answer: (
          <>
            <p>A Docker image that exposes:</p>
            <ul className="list-disc list-inside space-y-2">
              <li>
                <span className="font-semibold text-[#F3F4F6]">POST /v1/chat/completions</span>{' '}
                - the main chat API
              </li>
              <li>
                <span className="font-semibold text-[#F3F4F6]">GET /health</span> - a
                health check endpoint
              </li>
            </ul>
            <p className="mt-3">
              Plus metadata: your Bittensor hotkey, source code URL, and license.
            </p>
          </>
        ),
      },
      {
        question: 'Why must submissions be open source?',
        answer: (
          <>
            <p>Open source is fundamental to the Janus ethos. It ensures:</p>
            <ul className="list-disc list-inside space-y-2">
              <li>Community progress: everyone learns from each other</li>
              <li>Transparency: users can inspect how requests are handled</li>
              <li>Security: open code can be audited</li>
              <li>Decentralization: no single entity controls the intelligence</li>
            </ul>
          </>
        ),
      },
      {
        question: 'Can I use proprietary models in my submission?',
        answer: (
          <p>
            Yes. Your submission can call external APIs like OpenAI, Anthropic, or
            Chutes. You just cannot hide your orchestration logic; the code that decides
            what to call and how to combine results must be open source.
          </p>
        ),
      },
      {
        question: 'What licenses are allowed?',
        answer: (
          <p>
            Any OSI-approved open source license. We recommend MIT or Apache 2.0. GPL
            and AGPL are allowed but remember their copyleft requirements.
          </p>
        ),
      },
      {
        question: 'How do I include my Bittensor hotkey?',
        answer: (
          <>
            <p>
              Your hotkey (hot key) is an SS58 address that starts with &quot;5&quot;.
              Include it in the submission form.
            </p>
            <p>
              It is used for attribution on the leaderboard, prize pool payouts, and future Subnet 64 integration.
            </p>
          </>
        ),
      },
    ],
  },
  {
    title: 'Scoring',
    items: [
      {
        question: 'How is my implementation scored?',
        answer: (
          <>
            <p>Your implementation is evaluated across multiple categories:</p>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm text-[#D1D5DB]">
                <thead className="text-xs uppercase tracking-[0.2em] text-[#9CA3AF]">
                  <tr>
                    <th className="pb-2">Category</th>
                    <th className="pb-2">What it measures</th>
                  </tr>
                </thead>
                <tbody>
                  {[
                    ['Chat Quality', 'Conversational ability'],
                    ['Reasoning', 'Logic, math, planning'],
                    ['Knowledge', 'Factual accuracy'],
                    ['Research', 'Web search, synthesis'],
                    ['Coding', 'Code generation'],
                    ['Tool Use', 'API calling'],
                    ['Multimodal', 'Images, files'],
                    ['Speed', 'Latency'],
                    ['Cost', 'Efficiency'],
                    ['Streaming', 'Continuous output'],
                  ].map(([category, measure]) => (
                    <tr key={category} className="border-t border-[#1F2937]">
                      <td className="py-2 font-semibold text-[#F3F4F6]">{category}</td>
                      <td className="py-2 text-[#9CA3AF]">{measure}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="mt-3">
              Each category contributes to a composite score. Current weights are
              published on the{' '}
              <a href="#scoring" className="text-[#63D297] hover:underline">
                scoring page
              </a>
              .
            </p>
          </>
        ),
      },
      {
        question: 'What benchmarks are used?',
        answer: (
          <>
            <p>A mix of public and proprietary benchmarks:</p>
            <ul className="list-disc list-inside space-y-2">
              <li>
                Public: MMLU, TruthfulQA, GSM8K, HumanEval, MT-Bench
              </li>
              <li>
                Proprietary: Janus-specific tasks for research, tool use, streaming
              </li>
            </ul>
            <p className="mt-3">
              Public benchmarks are reproducible. Proprietary benchmarks prevent
              overfitting.
            </p>
          </>
        ),
      },
      {
        question: 'Can I run the benchmarks locally?',
        answer: (
          <>
            <p>
              Yes. Install janus-bench and run the quick suite locally to validate your
              implementation before submission.
            </p>
            <pre className="mt-3 bg-[#0B111A] border border-[#1F2937] rounded-lg p-3 text-xs text-[#D1D5DB] whitespace-pre-wrap">
{`pip install janus-bench
janus-bench run --target http://localhost:8000 --suite quick`}
            </pre>
          </>
        ),
      },
      {
        question: 'How often are benchmarks run?',
        answer: (
          <p>
            New submissions are benchmarked within 48 hours. Periodic re-evaluation
            happens weekly to catch regressions or environment changes.
          </p>
        ),
      },
    ],
  },
  {
    title: 'Prize Pool',
    items: [
      {
        question: 'How does the prize pool work?',
        answer: (
          <p>
            A portion of Janus platform revenue flows into the prize pool daily. The
            pool accumulates as long as the same implementation holds #1. When a new
            implementation takes the top spot, they claim the entire accumulated pool,
            and a new pool starts.
          </p>
        ),
      },
      {
        question: 'How big can the pool get?',
        answer: (
          <p>
            There is no cap. If the same implementation holds #1 for months, the pool
            could be substantial. This creates a bounty for beating the leader.
          </p>
        ),
      },
      {
        question: 'How do I get paid?',
        answer: (
          <p>
            When you claim #1, the pool is sent to the Bittensor coldkey associated
            with your registered hotkey. Currently this is a manual process; eventually
            it will be automated on-chain.
          </p>
        ),
      },
      {
        question: 'What if there is a tie?',
        answer: (
          <p>
            If two submissions have identical composite scores, the earlier submission
            retains #1. To claim the pool, you must have a strictly higher score.
          </p>
        ),
      },
      {
        question: 'What if I am caught cheating?',
        answer: (
          <p>
            Submissions that violate rules (malicious code, data exfiltration, benchmark
            gaming) are disqualified. If a payout was already made, we reserve the right
            to pursue clawback. Repeat offenders are banned.
          </p>
        ),
      },
    ],
  },
  {
    title: 'Technical',
    items: [
      {
        question: 'What resources does my container get?',
        answer: (
          <ul className="list-disc list-inside space-y-2">
            <li>Memory: 16 GB</li>
            <li>CPU: 4 cores</li>
            <li>Disk: 50 GB</li>
            <li>Timeout: 5 minutes per request</li>
          </ul>
        ),
      },
      {
        question: 'What services can my container call?',
        answer: (
          <>
            <p>Only whitelisted services:</p>
            <ul className="list-disc list-inside space-y-2">
              <li>proxy.janus.rodeo - web page fetching</li>
              <li>search.janus.rodeo - web search</li>
              <li>vector.janus.rodeo - vector search</li>
              <li>sandbox.janus.rodeo - code execution</li>
              <li>api.chutes.ai - LLM inference</li>
            </ul>
            <p className="mt-3">All other outbound connections are blocked.</p>
          </>
        ),
      },
      {
        question: 'Do I get API credits for Chutes?',
        answer: (
          <p>
            Yes. Your container receives a CHUTES_API_KEY with platform credits. Usage
            is metered and affects your cost score.
          </p>
        ),
      },
      {
        question: 'Can I use GPUs?',
        answer: (
          <p>
            Not currently. Containers run on CPU TEE nodes. GPU support is planned for
            future phases.
          </p>
        ),
      },
    ],
  },
  {
    title: 'Marketplace (Preview)',
    items: [
      {
        question: 'What is the Component Marketplace?',
        answer: (
          <p>
            A place where developers can publish reusable components (research tools,
            memory systems, integrations) and earn rewards when leading Janus
            implementations use them. See the{' '}
            <a href="#component-marketplace" className="text-[#63D297] hover:underline">
              Component Marketplace
            </a>{' '}
            section for details.
          </p>
        ),
      },
      {
        question: 'How do I earn from components?',
        answer: (
          <p>
            When an implementation that uses your component claims the prize pool, you
            receive a share. The exact share depends on how much value your component
            contributes.
          </p>
        ),
      },
      {
        question: 'Do I need to build a full implementation to earn?',
        answer: (
          <p>
            No. If you have a great idea for a specific capability (for example, a
            better code search tool), you can build just that component and earn when
            others integrate it.
          </p>
        ),
      },
      {
        question: 'How is component usage tracked?',
        answer: (
          <p>
            Implementations declare their dependencies. When benchmarks run, we track
            which components are invoked and how they contribute to the score.
          </p>
        ),
      },
      {
        question: 'When will the Marketplace launch?',
        answer: (
          <p>
            The Marketplace is in development. Early access starts Q1 2026, with full
            launch planned for Q2 2026. Join the waitlist to get notified.
          </p>
        ),
      },
    ],
  },
];

const helpfulLinks = [
  { label: 'Submission Portal', description: 'Submit your implementation', href: '#submission-portal' },
  { label: 'Leaderboard', description: 'See current rankings', href: '#leaderboard' },
  { label: 'Benchmark Docs', description: 'Detailed benchmark information', href: '#benchmark-docs' },
  { label: 'janus-bench on PyPI', description: 'Local testing tool', href: 'https://pypi.org/project/janus-bench/' },
  {
    label: 'Baseline Repository',
    description: 'Start from the reference implementation',
    href: 'https://github.com/fstandhartinger/janus-poc/tree/main/baseline',
  },
  { label: 'Discord Community', description: 'Get help and discuss strategies', href: '#' },
  { label: 'Marketplace Waitlist', description: 'Early access to components', href: '#marketplace-waitlist' },
];

interface FAQItemProps {
  question: string;
  answer: ReactNode;
  defaultOpen?: boolean;
}

function FAQItem({ question, answer, defaultOpen = false }: FAQItemProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div className="glass-card overflow-hidden">
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full p-6 flex items-start justify-between text-left hover:bg-white/5 transition-colors"
        aria-expanded={isOpen}
      >
        <h4 className="text-lg font-semibold text-[#F3F4F6] pr-4">{question}</h4>
        <svg
          className={`w-5 h-5 text-[#9CA3AF] flex-shrink-0 transition-transform mt-1 ${
            isOpen ? 'rotate-180' : ''
          }`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      {isOpen && (
        <div className="px-6 pb-6">
          <div className="text-sm text-[#9CA3AF] leading-relaxed space-y-3">{answer}</div>
        </div>
      )}
    </div>
  );
}

interface FAQSectionProps {
  title: string;
  items: { question: string; answer: ReactNode }[];
}

function FAQSection({ title, items }: FAQSectionProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div className="space-y-4">
      <button
        type="button"
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between text-left group"
        aria-expanded={isExpanded}
      >
        <h3 className="text-2xl font-semibold text-[#F3F4F6] group-hover:text-[#63D297] transition-colors">
          {title}
        </h3>
        <div className="flex items-center gap-2 text-sm text-[#9CA3AF]">
          <span>{items.length} questions</span>
          <svg
            className={`w-5 h-5 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </button>
      {isExpanded && (
        <div className="space-y-3">
          {items.map((item) => (
            <FAQItem key={item.question} question={item.question} answer={item.answer} />
          ))}
        </div>
      )}
    </div>
  );
}

export function FAQ() {
  return (
    <section id="faq" className="py-16 lg:py-24 bg-[#0B111A]">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 space-y-12">
        <div className="text-center">
          <p className="text-sm uppercase tracking-[0.3em] text-[#9CA3AF]">FAQ</p>
          <h2 className="text-3xl sm:text-4xl font-semibold text-[#F3F4F6] mt-3">
            Frequently Asked Questions
          </h2>
          <p className="text-[#9CA3AF] mt-4">
            Need a quick answer before you ship? Click a category to explore.
          </p>
        </div>

        <div className="space-y-8">
          {faqSections.map((section) => (
            <FAQSection key={section.title} title={section.title} items={section.items} />
          ))}
        </div>

        <div className="glass-card p-6 space-y-4">
          <h3 className="text-2xl font-semibold text-[#F3F4F6]">Helpful Links</h3>
          <ul className="space-y-3 text-sm text-[#D1D5DB]">
            {helpfulLinks.map((link) => (
              <li key={link.label}>
                <a href={link.href} className="text-[#63D297] hover:underline">
                  {link.label}
                </a>{' '}
                - {link.description}
              </li>
            ))}
          </ul>
          <p className="text-xs text-[#6B7280]">
            Search tips: open ai, openai, leader board, hot key, market place, bench
            mark, intelligence agent.
          </p>
        </div>
      </div>
    </section>
  );
}
