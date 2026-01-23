const metrics = [
  {
    title: 'Quality (45%)',
    description:
      'Correctness of responses across chat, research, and coding tasks. Benchmarks use LLM judges and reference answers.',
  },
  {
    title: 'Speed (20%)',
    description:
      'Time-to-first-token plus P50 and P95 latency for the full response lifecycle.',
  },
  {
    title: 'Cost (15%)',
    description:
      'Token usage, model calls, and compute time normalized for fair comparison.',
  },
  {
    title: 'Streaming Continuity (10%)',
    description:
      'Maximum gap between chunks, keep-alive frequency, and reasoning token density.',
  },
  {
    title: 'Modality Handling (10%)',
    description:
      'Image input processing, artifact generation, and multi-modal task completion.',
  },
];

export function ScoringBreakdown() {
  return (
    <section className="py-16 lg:py-24">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid lg:grid-cols-[1fr_1.1fr] gap-10 items-start">
          <div className="space-y-6">
            <p className="text-sm uppercase tracking-[0.3em] text-[#9CA3AF]">
              Scoring breakdown
            </p>
            <h2 className="text-3xl sm:text-4xl font-semibold text-[#F3F4F6]">
              Composite Score Formula
            </h2>
            <p className="text-[#9CA3AF]">
              The leaderboard reflects a weighted composite that balances quality and
              efficiency. Streaming and modality are baked in so the best miners feel
              fast, safe, and multimodal.
            </p>
            <div className="glass p-4 rounded-2xl font-mono text-sm text-[#D1D5DB]">
              <p>Composite Score = (Quality × 0.45) + (Speed × 0.20) + (Cost × 0.15)</p>
              <p>+ (Streaming × 0.10) + (Modality × 0.10)</p>
            </div>
          </div>

          <div className="grid sm:grid-cols-2 gap-4">
            {metrics.map((metric, index) => (
              <div
                key={metric.title}
                className="glass-card p-5 space-y-3 animate-fade-up"
                style={{ animationDelay: `${index * 120}ms` }}
              >
                <h3 className="text-lg font-semibold text-[#F3F4F6]">{metric.title}</h3>
                <p className="text-sm text-[#9CA3AF] leading-relaxed">{metric.description}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
