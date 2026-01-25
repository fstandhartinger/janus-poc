import Link from 'next/link';
import { MermaidDiagram } from '@/components/MermaidDiagram';

const benchDiagram = `flowchart TB
    subgraph BenchRunner ["Bench Runner"]
        SUITE[Benchmark Suite]
        EXEC[Test Executor]
        EVAL[Evaluator]
    end

    subgraph Target ["Target Implementation"]
        API["/v1/chat/completions"]
    end

    subgraph Scoring ["Scoring"]
        METRICS[Metrics Collector]
        SCORE[Score Calculator]
        LDB[Leaderboard]
    end

    SUITE --> EXEC
    EXEC -->|HTTP Requests| API
    API -->|Responses| EXEC
    EXEC --> EVAL
    EVAL --> METRICS
    METRICS --> SCORE
    SCORE --> LDB`;

const benchmarkFlow = [
  'Load suite: bench runner loads test cases from the benchmark suite.',
  'Execute tests: each test sends a request to your API.',
  'Collect responses: responses are captured with timing data.',
  'Evaluate quality: LLM judges or exact match evaluate correctness.',
  'Calculate metrics: quality, speed, cost, streaming scores computed.',
  'Update leaderboard: composite score published.',
];

const benchmarkTransparency = [
  'Public benchmarks are open source.',
  'Evaluation prompts are published.',
  'Scoring formulas are documented.',
  'You can reproduce any score locally.',
];

export function BenchRunner() {
  return (
    <section id="benchmark-docs" className="py-16 lg:py-24 bg-[#111726]/50">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 space-y-8">
        <div className="glass-card p-8 grid lg:grid-cols-[1.1fr_0.9fr] gap-8 items-start">
          <div className="space-y-5">
            <p className="text-sm uppercase tracking-[0.3em] text-[#9CA3AF]">
              Bench runner integration
            </p>
            <h2 className="text-3xl font-semibold text-[#F3F4F6]">
              Test Your Implementation
            </h2>
            <p className="text-[#9CA3AF]">
              Run the public dev suite locally to validate your container before
              submitting. The same tooling powers the official leaderboard.
            </p>
            <div className="flex flex-col sm:flex-row gap-3 text-sm">
              <Link
                href="https://chutes-bench-runner-ui.onrender.com"
                target="_blank"
                rel="noreferrer"
                className="text-[#63D297] hover:underline"
              >
                Bench Runner UI
              </Link>
              <Link
                href="https://chutes-bench-runner-api-v2.onrender.com"
                target="_blank"
                rel="noreferrer"
                className="text-[#63D297] hover:underline"
              >
                Bench Runner API
              </Link>
              <Link
                href="https://github.com/fstandhartinger/janus-poc/blob/main/bench/README.md"
                target="_blank"
                rel="noreferrer"
                className="text-[#63D297] hover:underline"
              >
                CLI Documentation
              </Link>
            </div>
          </div>

          <div className="glass p-5 rounded-2xl">
            <p className="text-xs uppercase tracking-[0.2em] text-[#9CA3AF] mb-3">
              Quick start
            </p>
            <pre className="font-mono text-sm text-[#D1D5DB] whitespace-pre-wrap">
{`# Install bench runner
pip install janus-bench

# Run quick suite (5 minutes)
janus-bench run --target http://localhost:8000 --suite quick

# Run full suite (2 hours)
janus-bench run --target http://localhost:8000 --suite full

# Run specific category
janus-bench run --target http://localhost:8000 --suite coding`}
            </pre>
          </div>
        </div>

        <div className="grid lg:grid-cols-[1.1fr_0.9fr] gap-6 items-start">
          <div className="glass-card p-6 space-y-4">
            <p className="text-xs uppercase tracking-[0.2em] text-[#9CA3AF]">
              Benchmark integration
            </p>
            <h3 className="text-2xl font-semibold text-[#F3F4F6]">
              How Scoring Works
            </h3>
            <p className="text-sm text-[#9CA3AF]">
              Bench runner evaluates your implementation through the same infrastructure
              used for the official leaderboard.
            </p>
            <div className="glass p-4 rounded-2xl overflow-x-auto">
              <MermaidDiagram chart={benchDiagram} ariaLabel="Bench runner diagram" />
            </div>
          </div>

          <div className="glass-card p-6 space-y-4">
            <p className="text-xs uppercase tracking-[0.2em] text-[#9CA3AF]">
              Benchmark flow
            </p>
            <ul className="list-disc list-inside space-y-2 text-sm text-[#D1D5DB]">
              {benchmarkFlow.map((step) => (
                <li key={step}>{step}</li>
              ))}
            </ul>
            <div className="glass p-4 rounded-2xl">
              <p className="text-xs uppercase tracking-[0.2em] text-[#9CA3AF] mb-3">
                Benchmark transparency
              </p>
              <ul className="list-disc list-inside space-y-2 text-sm text-[#D1D5DB]">
                {benchmarkTransparency.map((item) => (
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
