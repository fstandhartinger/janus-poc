import Link from 'next/link';

export function HeroSection() {
  const stats = [
    { label: 'Entries', value: '12' },
    { label: 'Rodeo Purse', value: '$50K' },
    { label: 'Benchmark Runs', value: '847' },
  ];

  return (
    <section className="relative overflow-hidden">
      <div className="absolute inset-0 aurora-glow pointer-events-none" />
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 lg:py-24">
        <div className="grid lg:grid-cols-[1.2fr_0.8fr] gap-12 items-center">
          <div className="space-y-6">
            <div className="space-y-4 animate-fade-up">
              <p className="text-sm uppercase tracking-[0.3em] text-[#9CA3AF]">
                Janus Competition — The Rodeo
              </p>
              <h1 className="text-4xl sm:text-5xl lg:text-6xl font-semibold leading-tight text-[#F3F4F6]">
                Compete to Build the Best{' '}
                <span className="gradient-text">Intelligence Engine</span>
              </h1>
              <p className="text-lg sm:text-xl text-[#D1D5DB] max-w-xl">
                The decentralized arena on Bittensor where intelligence engines compete.
                Build an OpenAI-compatible Janus implementation, score across quality,
                speed, cost, streaming continuity, and modality handling, and ride to
                the top. Permissionless entry. Real rewards for champions. Any stack.
                Any approach. One arena.
              </p>
            </div>

            <div className="flex flex-wrap gap-3 animate-fade-up" style={{ animationDelay: '120ms' }}>
              {stats.map((stat) => (
                <div
                  key={stat.label}
                  className="glass px-4 py-2 rounded-full text-sm text-[#D1D5DB] flex items-center gap-2"
                >
                  <span className="text-[#63D297] font-semibold">{stat.value}</span>
                  <span className="text-[#9CA3AF]">{stat.label}</span>
                </div>
              ))}
            </div>

            <div className="flex flex-col sm:flex-row gap-4 animate-fade-up" style={{ animationDelay: '220ms' }}>
              <a href="#instructions" className="btn-primary text-base px-8 py-3">
                Start Competing
              </a>
              <Link href="/chat" className="btn-secondary text-base px-8 py-3">
                Explore Demo Chat
              </Link>
            </div>
          </div>

          <div className="relative">
            <div className="glass-card p-6 lg:p-8 space-y-6 animate-fade-up" style={{ animationDelay: '180ms' }}>
              <div>
                <p className="text-sm uppercase tracking-[0.3em] text-[#9CA3AF]">
                  Live Snapshot
                </p>
                <h2 className="text-2xl font-semibold text-[#F3F4F6] mt-2">
                  Today&apos;s Benchmark Pulse
                </h2>
              </div>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-[#9CA3AF]">Next public run</span>
                  <span className="text-[#F3F4F6] font-semibold">03:00 UTC</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-[#9CA3AF]">Champion score</span>
                  <span className="text-[#63D297] font-semibold">78.4</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-[#9CA3AF]">Median TTFT</span>
                  <span className="text-[#F3F4F6] font-semibold">0.92s</span>
                </div>
              </div>
              <div className="border-t border-[#1F2937] pt-4 text-sm text-[#9CA3AF]">
                Scores refresh daily for public benchmarks. Private evaluation is
                ongoing for submissions in review.
              </div>
            </div>
            <div className="absolute -top-6 -right-6 w-32 h-32 rounded-full bg-[#63D297]/20 blur-3xl" />
            <div className="absolute -bottom-10 -left-8 w-40 h-40 rounded-full bg-[#FA5D19]/20 blur-3xl" />
          </div>
        </div>
      </div>
    </section>
  );
}
