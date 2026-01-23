'use client';

import { useEffect, useRef, useState } from 'react';
import { MermaidDiagram } from '@/components/MermaidDiagram';

const diagram = `flowchart LR
    DEV[Component Developer]
    REG[Marketplace Registry]
    MINER[Miner Implementation]
    BENCH[Benchmarks]
    REWARDS[Reward Pool]

    DEV -->|Submit| REG
    REG -->|Discover| MINER
    MINER -->|Uses| REG
    BENCH -->|Scores| MINER
    MINER -->|Wins| REWARDS
    REWARDS -->|Share| DEV`;

const steps = [
  {
    title: 'Submit',
    description: 'Developers upload a component manifest, API contract, and docs.',
  },
  {
    title: 'Review',
    description: 'Security, quality, and compliance checks keep the marketplace safe.',
  },
  {
    title: 'Publish',
    description: 'Approved components become discoverable to all miners.',
  },
  {
    title: 'Integrate',
    description: 'Miners add components to their Janus implementations.',
  },
  {
    title: 'Earn',
    description: 'Reward shares flow back to component developers when miners win.',
  },
];

export function HowItWorks() {
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
    <section className="py-16 lg:py-24 bg-[#0B111A]" id="how-it-works">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid lg:grid-cols-[1.1fr_0.9fr] gap-10 items-start">
          <div className="space-y-6">
            <p className="text-sm uppercase tracking-[0.3em] text-[#9CA3AF]">
              How it works
            </p>
            <h2 className="text-3xl sm:text-4xl font-semibold text-[#F3F4F6]">
              A Marketplace That Rewards Builders
            </h2>
            <p className="text-[#9CA3AF]">
              Build reusable capabilities once and earn every time a miner relies
              on your component during benchmarks.
            </p>
            <div className="space-y-4">
              {steps.map((step, index) => (
                <div key={step.title} className="flex gap-4">
                  <div className="h-8 w-8 rounded-full bg-[#63D297]/15 text-[#63D297] flex items-center justify-center text-sm font-semibold">
                    {index + 1}
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-[#F3F4F6]">
                      {step.title}
                    </h3>
                    <p className="text-sm text-[#9CA3AF]">{step.description}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div ref={containerRef} className="glass-card p-6 min-h-[320px]">
            {isVisible ? (
              <MermaidDiagram
                chart={diagram}
                className="w-full"
                ariaLabel="Marketplace flow diagram"
              />
            ) : (
              <div className="h-full flex items-center justify-center text-sm text-[#9CA3AF] animate-pulse">
                Loading marketplace flow...
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
