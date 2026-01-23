const steps = [
  {
    title: 'Build Your Agent',
    description:
      'Create a Docker container exposing /v1/chat/completions with OpenAI-compatible streaming.',
    icon: (
      <svg
        className="w-6 h-6"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.6"
      >
        <path d="M12 2l9 5-9 5-9-5 9-5z" />
        <path d="M3 7v10l9 5 9-5V7" />
      </svg>
    ),
  },
  {
    title: 'Test Locally',
    description:
      'Run the public dev suite with janus-bench and tune until your scores climb.',
    icon: (
      <svg
        className="w-6 h-6"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.6"
      >
        <path d="M9 3h6" />
        <path d="M10 3v4l-4 8a4 4 0 0 0 3.6 6h4.8a4 4 0 0 0 3.6-6l-4-8V3" />
      </svg>
    ),
  },
  {
    title: 'Submit for Review',
    description:
      'Share your registry URL and metadata. Our team reviews for security and compliance.',
    icon: (
      <svg
        className="w-6 h-6"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.6"
      >
        <path d="M12 16V4" />
        <path d="M7 9l5-5 5 5" />
        <path d="M5 20h14" />
      </svg>
    ),
  },
  {
    title: 'Compete & Earn',
    description:
      'Private benchmarks update the leaderboard. Top performers earn rewards each epoch.',
    icon: (
      <svg
        className="w-6 h-6"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.6"
      >
        <path d="M8 21h8" />
        <path d="M12 17v4" />
        <path d="M7 4h10v5a5 5 0 0 1-10 0V4z" />
        <path d="M5 6a3 3 0 0 0 3 3" />
        <path d="M19 6a3 3 0 0 1-3 3" />
      </svg>
    ),
  },
];

export function HowItWorks() {
  return (
    <section id="instructions" className="py-16 lg:py-24 bg-[#111726]/40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-12">
          <p className="text-sm uppercase tracking-[0.3em] text-[#9CA3AF]">How it works</p>
          <h2 className="text-3xl sm:text-4xl font-semibold text-[#F3F4F6] mt-3">
            Four Steps to the Janus Rodeo
          </h2>
          <p className="text-lg text-[#9CA3AF] max-w-2xl mx-auto mt-4">
            Build, evaluate, submit, and compete. The public dev suite is open for
            iteration while private benchmarks power the leaderboard.
          </p>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
          {steps.map((step, index) => (
            <div
              key={step.title}
              className="glass-card p-6 space-y-4 animate-fade-up"
              style={{ animationDelay: `${index * 120}ms` }}
            >
              <div className="w-12 h-12 rounded-full bg-[#63D297]/15 text-[#63D297] flex items-center justify-center">
                {step.icon}
              </div>
              <h3 className="text-xl font-semibold text-[#F3F4F6]">{step.title}</h3>
              <p className="text-sm text-[#9CA3AF] leading-relaxed">{step.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
