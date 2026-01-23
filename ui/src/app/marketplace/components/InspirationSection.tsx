export function InspirationSection() {
  const features = [
    'Memory and storage systems',
    'Web search and browser tools',
    'YouTube and social integrations',
    'Dangerzone sandboxed execution',
  ];

  return (
    <section className="py-16 lg:py-24 bg-[#0B111A]">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="glass-card p-8 lg:p-10 relative overflow-hidden">
          <div className="absolute -top-20 -right-10 w-56 h-56 bg-[#8B5CF6]/20 blur-3xl" />
          <div className="absolute -bottom-16 -left-10 w-48 h-48 bg-[#63D297]/20 blur-3xl" />
          <div className="relative grid lg:grid-cols-[1.1fr_0.9fr] gap-8 items-center">
            <div className="space-y-4">
              <p className="text-sm uppercase tracking-[0.3em] text-[#9CA3AF]">
                Standing on giants
              </p>
              <h2 className="text-3xl sm:text-4xl font-semibold text-[#F3F4F6]">
                Inspired by Squad API
              </h2>
              <p className="text-[#9CA3AF]">
                The Janus marketplace is modeled after the incredible tooling from
                Squad API. We are building on the same spirit of composability.
              </p>
              <a
                href="https://github.com/Squad-API"
                target="_blank"
                rel="noreferrer"
                className="btn-secondary text-base px-8 py-3 inline-flex"
              >
                View on GitHub
              </a>
            </div>
            <div className="bg-[#0B0F14] border border-[#1F2937] rounded-2xl p-6">
              <h3 className="text-lg font-semibold text-[#F3F4F6]">
                Features we love
              </h3>
              <ul className="mt-4 space-y-3 text-sm text-[#9CA3AF] list-disc list-inside">
                {features.map((feature) => (
                  <li key={feature}>{feature}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
