export function MarketplaceHero() {
  const stats = [
    { label: 'Components', value: '47' },
    { label: 'Developers', value: '12' },
    { label: 'Distributed', value: '$8.2K' },
  ];

  return (
    <section className="relative overflow-hidden">
      <div className="absolute inset-0 aurora-glow pointer-events-none" />
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 lg:py-24">
        <div className="grid lg:grid-cols-[1.1fr_0.9fr] gap-10 items-center">
          <div className="space-y-6">
            <div className="space-y-4 animate-fade-up">
              <p className="text-sm uppercase tracking-[0.3em] text-[#9CA3AF]">
                Janus Marketplace
              </p>
              <h1 className="text-4xl sm:text-5xl lg:text-6xl font-semibold leading-tight text-[#F3F4F6]">
                Build Once,&nbsp;
                <span className="gradient-text">Earn Forever</span>
              </h1>
              <p className="text-lg sm:text-xl text-[#D1D5DB] max-w-xl">
                Submit reusable components. Earn rewards when miners use them.
                The marketplace is where Janus builders turn expertise into
                lasting leverage.
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
              <a href="#submit" className="btn-primary text-base px-8 py-3">
                Submit a Component
              </a>
              <a href="#components" className="btn-secondary text-base px-8 py-3">
                Explore Components
              </a>
            </div>
          </div>

          <div className="relative">
            <div className="glass-card p-6 lg:p-8 space-y-6 animate-fade-up" style={{ animationDelay: '180ms' }}>
              <div>
                <p className="text-sm uppercase tracking-[0.3em] text-[#9CA3AF]">
                  Marketplace Pulse
                </p>
                <h2 className="text-2xl font-semibold text-[#F3F4F6] mt-2">
                  Component Earnings Snapshot
                </h2>
              </div>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-[#9CA3AF]">Average reward split</span>
                  <span className="text-[#F3F4F6] font-semibold">14%</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-[#9CA3AF]">Top component ROI</span>
                  <span className="text-[#63D297] font-semibold">3.8x</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-[#9CA3AF]">Miners integrating</span>
                  <span className="text-[#F3F4F6] font-semibold">23</span>
                </div>
              </div>
              <div className="border-t border-[#1F2937] pt-4 text-sm text-[#9CA3AF]">
                Stats are placeholders for the PoC. Real revenue tracking
                launches in Phase 2.
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
