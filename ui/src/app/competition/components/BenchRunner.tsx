import Link from 'next/link';

export function BenchRunner() {
  return (
    <section className="py-16 lg:py-24 bg-[#111726]/50">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
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
            <p className="text-xs uppercase tracking-[0.2em] text-[#6B7280] mb-3">
              Quick start
            </p>
            <pre className="font-mono text-sm text-[#D1D5DB] whitespace-pre-wrap">
{`# Install the CLI
pip install janus-bench

# Run against your local implementation
janus-bench run --target http://localhost:8001 --suite public/dev

# View results
janus-bench report --format table`}
            </pre>
          </div>
        </div>
      </div>
    </section>
  );
}
