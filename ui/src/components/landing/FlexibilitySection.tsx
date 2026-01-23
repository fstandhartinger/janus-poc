import type { CSSProperties } from 'react';

const stacks = [
  'CLI agents (Claude Code, Aider, OpenHands)',
  'Workflow engines (n8n, LangGraph, CrewAI)',
  'Custom model orchestration',
  'Simple model switchers',
  'Complex multi-agent systems',
];

export function FlexibilitySection() {
  return (
    <section className="py-16 lg:py-24 bg-[#111726]/45">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid lg:grid-cols-[1fr_1.1fr] gap-10 lg:gap-14 items-start">
          <div data-reveal className="reveal space-y-6">
            <p className="text-sm uppercase tracking-[0.3em] text-[#9CA3AF]">
              Any Stack. Any Approach.
            </p>
            <h2 className="text-3xl sm:text-4xl font-semibold text-[#F3F4F6]">
              Any Stack. Any Approach.
            </h2>
            <p className="text-lg text-[#D1D5DB] leading-relaxed">
              Your Janus submission can be built with the tools you already trust. Build
              something simple or orchestrate a complex system - it all fits.
            </p>
            <p className="text-[#9CA3AF]">
              As long as it speaks the OpenAI-compatible API and streams reasoning, you&apos;re in.
            </p>
          </div>

          <div
            data-reveal
            className="reveal space-y-4"
            style={{ '--reveal-delay': '120ms' } as CSSProperties}
          >
            <div className="glass-card p-6 sm:p-8">
              <ul className="space-y-3 text-[#D1D5DB]">
                {stacks.map((stack) => (
                  <li key={stack} className="flex items-center gap-3 text-sm">
                    <span className="h-2 w-2 rounded-full bg-[#FA5D19]" />
                    <span>{stack}</span>
                  </li>
                ))}
              </ul>
            </div>
            <p className="text-sm text-[#9CA3AF]">
              Network access and tool usage are sandboxed and controlled. Builders use
              whitelisted services for security and fair competition.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
