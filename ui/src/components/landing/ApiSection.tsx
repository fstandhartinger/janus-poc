import Link from 'next/link';
import type { CSSProperties } from 'react';

const apiSnippet = `curl https://janus-gateway-bqou.onrender.com/v1/chat/completions \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "baseline",
    "messages": [
      { "role": "user", "content": "Hello Janus" }
    ],
    "stream": true
  }'`;

export function ApiSection() {
  return (
    <section className="py-16 lg:py-24">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid lg:grid-cols-[1.1fr_1fr] gap-10 lg:gap-16 items-center">
          <div data-reveal className="reveal">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#63D297]/10 text-[#63D297] text-xs font-semibold uppercase tracking-[0.2em]">
              OpenAI Compatible
            </div>
            <h2 className="mt-6 text-3xl sm:text-4xl font-semibold text-[#F3F4F6]">
              Drop-in API for agent builders
            </h2>
            <p className="mt-4 text-lg text-[#9CA3AF] leading-relaxed">
              Point your existing OpenAI SDK to Janus and keep the same request shape. The
              endpoint is a drop-in replacement for chat completions with streaming support.
            </p>
            <div className="mt-6 flex flex-wrap items-center gap-3">
              <span className="px-3 py-1 rounded-full border border-[#1F2937] text-sm text-[#D1D5DB]">
                POST /v1/chat/completions
              </span>
              <span className="px-3 py-1 rounded-full border border-[#1F2937] text-sm text-[#D1D5DB]">
                Streaming SSE
              </span>
            </div>
            <div className="mt-8 flex flex-col sm:flex-row gap-4">
              <Link href="/docs" className="btn-primary text-base px-6 py-3">
                API Documentation
              </Link>
              <Link href="/competition" className="btn-secondary text-base px-6 py-3">
                Build a Competitor
              </Link>
            </div>
          </div>

          <div data-reveal className="reveal" style={{ '--reveal-delay': '120ms' } as CSSProperties}>
            <div className="code-panel">
              <div className="code-panel-header">
                <span>curl</span>
                <span className="text-[#6B7280]">Janus Gateway</span>
              </div>
              <pre className="code-block">
                <code>{apiSnippet}</code>
              </pre>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
