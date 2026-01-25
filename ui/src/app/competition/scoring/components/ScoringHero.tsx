const highlights = [
  { label: 'Typical runtime', value: '5-120 min' },
  { label: 'Benchmarks', value: '7 suites' },
  { label: 'Submission type', value: 'URL or container' },
];

const steps = [
  'Submit your API or container image.',
  'Track live progress as tasks execute.',
  'Review scores and benchmark breakdowns.',
];

export function ScoringHero() {
  return (
    <section className="relative overflow-hidden">
      <div className="absolute inset-0 aurora-glow pointer-events-none" />
      <div className="grid lg:grid-cols-[1.15fr_0.85fr] gap-10 items-start">
        <div className="space-y-6">
          <div className="space-y-4 animate-fade-up">
            <p className="text-sm uppercase tracking-[0.3em] text-[#9CA3AF]">
              Competition scoring
            </p>
            <h1 className="text-4xl sm:text-5xl font-semibold leading-tight text-[#F3F4F6]">
              Launch a Scoring Run
            </h1>
            <p className="text-lg text-[#D1D5DB] max-w-2xl">
              Evaluate your Janus implementation against the official benchmark suite.
              Monitor progress in real time, track detailed scores, and see how your
              system compares to the leaderboard.
            </p>
          </div>

          <div className="flex flex-wrap gap-3 animate-fade-up" style={{ animationDelay: '120ms' }}>
            {highlights.map((highlight) => (
              <div
                key={highlight.label}
                className="glass px-4 py-2 rounded-full text-sm text-[#D1D5DB] flex items-center gap-2"
              >
                <span className="text-[#63D297] font-semibold">{highlight.value}</span>
                <span className="text-[#9CA3AF]">{highlight.label}</span>
              </div>
            ))}
          </div>

          <div className="flex flex-col sm:flex-row gap-4 animate-fade-up" style={{ animationDelay: '220ms' }}>
            <a href="#submit-run" className="btn-primary text-base px-8 py-3">
              Start a Run
            </a>
            <a href="/competition#leaderboard" className="btn-secondary text-base px-8 py-3">
              View Leaderboard
            </a>
          </div>
        </div>

        <div className="relative">
          <div className="glass-card p-6 lg:p-8 space-y-6 animate-fade-up" style={{ animationDelay: '180ms' }}>
            <div>
              <p className="text-sm uppercase tracking-[0.3em] text-[#9CA3AF]">
                Run checklist
              </p>
              <h2 className="text-2xl font-semibold text-[#F3F4F6] mt-2">
                What happens next
              </h2>
            </div>
            <ol className="space-y-4 text-sm text-[#D1D5DB]">
              {steps.map((step, index) => (
                <li key={step} className="flex gap-3">
                  <span className="w-6 h-6 rounded-full bg-[#63D297]/15 text-[#63D297] flex items-center justify-center text-xs font-semibold">
                    {index + 1}
                  </span>
                  <span>{step}</span>
                </li>
              ))}
            </ol>
            <div className="border-t border-[#1F2937] pt-4 text-sm text-[#9CA3AF]">
              Runs stream progress events every few seconds. You can close this page and
              return later to see full results.
            </div>
          </div>
          <div className="absolute -top-6 -right-6 w-32 h-32 rounded-full bg-[#63D297]/20 blur-3xl" />
          <div className="absolute -bottom-10 -left-8 w-40 h-40 rounded-full bg-[#FA5D19]/20 blur-3xl" />
        </div>
      </div>
    </section>
  );
}
