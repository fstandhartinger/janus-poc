'use client';

import { useEffect, useRef, useState } from 'react';
import { MermaidDiagram } from '@/components/MermaidDiagram';

const diagram = `flowchart TB
    subgraph Competition
        MINER[Your Container]
        BENCH[Benchmark Runner]
        LEADERBOARD[Leaderboard]
    end

    subgraph Platform
        GW[Janus Gateway]
        SERVICES[Platform Services]
    end

    BENCH -->|Requests| GW
    GW -->|Routes to| MINER
    MINER -->|Streams| GW
    GW -->|Streams| BENCH
    BENCH -->|Scores| LEADERBOARD
    MINER -.->|Allowed calls| SERVICES`;

export function ArchitectureOverview() {
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
    <section className="py-16 lg:py-24 bg-[#0B111A]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid lg:grid-cols-[1.1fr_0.9fr] gap-10 items-start">
          <div className="space-y-5">
            <p className="text-sm uppercase tracking-[0.3em] text-[#9CA3AF]">
              Architecture overview
            </p>
            <h2 className="text-3xl sm:text-4xl font-semibold text-[#F3F4F6]">
              How the Competition Pipeline Works
            </h2>
            <p className="text-[#9CA3AF]">
              Benchmarks fire through the Janus Gateway, route into your container,
              and stream results back for scoring. Platform services remain available
              behind strict network guardrails.
            </p>
            <div className="space-y-3 text-sm text-[#D1D5DB]">
              <p>• Competitor contract: OpenAI-compatible chat completions (spec 10).</p>
              <p>• Platform services: web proxy, search, sandbox, Chutes inference.</p>
              <p>• Network guardrails: egress whitelist, no external paid APIs.</p>
            </div>
          </div>

          <div ref={containerRef} className="glass-card p-6 min-h-[320px]">
            {isVisible ? (
              <MermaidDiagram
                chart={diagram}
                className="w-full"
                ariaLabel="Competition pipeline diagram"
              />
            ) : (
              <div className="h-full flex items-center justify-center text-sm text-[#9CA3AF] animate-pulse">
                Loading architecture diagram...
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
