'use client';

import { useEffect, useRef, useState } from 'react';
import { MermaidDiagram } from '@/components/MermaidDiagram';

const rewardFlowDiagram = `flowchart LR
    subgraph Marketplace ["Component Marketplace"]
        C1[Research Node A]
        C2[Tool Integration B]
        C3[Memory System C]
    end

    subgraph Impl ["Leading Implementation"]
        IMPL[Janus #1]
    end

    subgraph Rewards ["Reward Flow"]
        POOL[Prize Pool]
        MINER[Miner Reward]
        COMP[Component Rewards]
    end

    C1 -->|Used by| IMPL
    C2 -->|Used by| IMPL
    C3 -->|Used by| IMPL
    POOL -->|80%| MINER
    POOL -->|20%| COMP
    COMP --> C1
    COMP --> C2
    COMP --> C3`;

const componentTypes = [
  {
    type: 'Research Nodes',
    description: 'Specialized research capabilities',
    examples: 'Academic paper search, news aggregation',
  },
  {
    type: 'Tool Integrations',
    description: 'Connections to external services',
    examples: 'GitHub API, database connectors',
  },
  {
    type: 'Memory Systems',
    description: 'Context management solutions',
    examples: 'Vector stores, conversation history',
  },
  {
    type: 'Reasoning Modules',
    description: 'Thinking and planning logic',
    examples: 'Chain-of-thought, tree-of-thought',
  },
  {
    type: 'Output Formatters',
    description: 'Response formatting',
    examples: 'Code syntax, markdown, structured data',
  },
];

const howItWorksSteps = [
  'You build a component and publish it to the Marketplace.',
  'Implementation developers integrate your component.',
  'When that implementation wins, you earn a share of the prize.',
  'Attribution is automatic via dependency tracking.',
];

const componentRequirements = [
  'Open source: MIT, Apache 2.0, or compatible license.',
  'Documentation: clear API docs and usage examples.',
  'Packaging: pip package, npm module, or Docker image.',
  'Versioning: semantic versioning with changelog.',
  'Testing: automated tests with over 80% coverage.',
];

const comingSoonLinks = [
  { label: 'Join the waitlist', href: '#marketplace-waitlist' },
  { label: 'Browse proposed components', href: '#' },
  { label: 'Submit component ideas', href: '#' },
];

export function ComponentMarketplace() {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [isVisible, setIsVisible] = useState(() => {
    if (typeof window === 'undefined') {
      return false;
    }
    return !('IntersectionObserver' in window);
  });

  useEffect(() => {
    if (isVisible) {
      return;
    }
    const container = containerRef.current;
    if (!container) {
      return;
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsVisible(true);
          observer.disconnect();
        }
      },
      { rootMargin: '120px' }
    );

    observer.observe(container);

    return () => observer.disconnect();
  }, [isVisible]);

  return (
    <section id="component-marketplace" className="py-16 lg:py-24 bg-[#111726]/40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid lg:grid-cols-[1.1fr_0.9fr] gap-10 items-start">
          <div className="space-y-6">
            <p className="text-sm uppercase tracking-[0.3em] text-[#9CA3AF]">
              Component marketplace
            </p>
            <h2 className="text-3xl sm:text-4xl font-semibold text-[#F3F4F6]">
              Component Marketplace
            </h2>
            <p className="text-[#9CA3AF]">
              Beyond competing with full implementations, you can contribute reusable
              components to the Janus ecosystem and earn rewards when they power the
              leading intelligence implementation.
            </p>

            <div className="glass-card p-6 space-y-4">
              <h3 className="text-xl font-semibold text-[#F3F4F6]">
                What are components?
              </h3>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm text-[#D1D5DB]">
                  <thead className="text-xs uppercase tracking-[0.2em] text-[#9CA3AF]">
                    <tr>
                      <th className="pb-2">Component type</th>
                      <th className="pb-2">Description</th>
                      <th className="pb-2">Examples</th>
                    </tr>
                  </thead>
                  <tbody>
                    {componentTypes.map((component) => (
                      <tr key={component.type} className="border-t border-[#1F2937]">
                        <td className="py-3 font-semibold text-[#F3F4F6]">
                          {component.type}
                        </td>
                        <td className="py-3 text-[#D1D5DB]">{component.description}</td>
                        <td className="py-3 text-[#9CA3AF]">{component.examples}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="glass-card p-6 space-y-4">
              <h3 className="text-xl font-semibold text-[#F3F4F6]">How it works</h3>
              <ol className="space-y-3 text-sm text-[#D1D5DB] list-decimal list-inside">
                {howItWorksSteps.map((step) => (
                  <li key={step}>{step}</li>
                ))}
              </ol>
            </div>

            <div className="glass-card p-6 space-y-4">
              <h3 className="text-xl font-semibold text-[#F3F4F6]">Reward sharing</h3>
              <p className="text-sm text-[#9CA3AF]">
                When an implementation claims the prize pool, rewards are distributed
                between the implementation developer and the component builders.
              </p>
              <div className="grid sm:grid-cols-2 gap-4 text-sm">
                <div className="glass p-4 rounded-2xl">
                  <p className="text-xs uppercase tracking-[0.2em] text-[#9CA3AF]">
                    Miner reward
                  </p>
                  <p className="text-2xl font-semibold text-[#F3F4F6] mt-2">80%</p>
                  <p className="text-[#9CA3AF] mt-2">
                    Goes to the implementation developer.
                  </p>
                </div>
                <div className="glass p-4 rounded-2xl">
                  <p className="text-xs uppercase tracking-[0.2em] text-[#9CA3AF]">
                    Component rewards
                  </p>
                  <p className="text-2xl font-semibold text-[#F3F4F6] mt-2">20%</p>
                  <p className="text-[#9CA3AF] mt-2">
                    Split across component builders by usage and value.
                  </p>
                </div>
              </div>
              <p className="text-xs text-[#6B7280] italic">
                Percentages are illustrative. Final model will be determined by
                governance.
              </p>
            </div>

            <div className="glass-card p-6 space-y-4">
              <h3 className="text-xl font-semibold text-[#F3F4F6]">
                Component requirements
              </h3>
              <ul className="list-disc list-inside space-y-2 text-sm text-[#D1D5DB]">
                {componentRequirements.map((requirement) => (
                  <li key={requirement}>{requirement}</li>
                ))}
              </ul>
            </div>

            <div className="glass-card p-6 space-y-3" id="marketplace-waitlist">
              <h3 className="text-xl font-semibold text-[#F3F4F6]">Coming soon</h3>
              <p className="text-sm text-[#9CA3AF]">
                The Marketplace is currently in development. Full launch is planned for
                Q2 2026, with early access starting in Q1 2026.
              </p>
              <ul className="space-y-2 text-sm">
                {comingSoonLinks.map((link) => (
                  <li key={link.label}>
                    <a href={link.href} className="text-[#63D297] hover:underline">
                      {link.label}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          <div ref={containerRef} className="glass-card p-6 min-h-[320px]">
            {isVisible ? (
              <MermaidDiagram
                chart={rewardFlowDiagram}
                className="w-full"
                ariaLabel="Marketplace reward flow diagram"
              />
            ) : (
              <div className="h-full flex items-center justify-center text-sm text-[#9CA3AF] animate-pulse">
                Loading marketplace reward flow...
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
