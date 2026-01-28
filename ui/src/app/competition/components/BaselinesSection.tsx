import Link from 'next/link';

const baselines = [
  {
    id: 'agent-cli',
    name: 'CLI Agent Baseline',
    description:
      'Sandbox-based approach using the Claude Code CLI agent with full tool access inside an isolated Sandy environment.',
    highlights: [
      'Dual-path routing (fast vs complex)',
      'Secure sandbox execution',
      'Full filesystem and code access',
      'Artifact generation',
    ],
    href: '/docs/baseline-agent-cli',
    icon: (
      <svg
        className="w-6 h-6"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.6"
      >
        <rect x="4" y="6" width="16" height="12" rx="3" />
        <path d="M9 6V4" />
        <path d="M15 6V4" />
        <circle cx="9" cy="12" r="1" />
        <circle cx="15" cy="12" r="1" />
        <path d="M9 16h6" />
      </svg>
    ),
  },
  {
    id: 'langchain',
    name: 'LangChain Baseline',
    description:
      'In-process approach using LangChain agents with direct tool integration and streaming support.',
    highlights: [
      'LangChain agent framework',
      'In-process execution',
      'Extensible tool system',
      'Vision model routing',
    ],
    href: '/docs/baseline-langchain',
    icon: (
      <svg
        className="w-6 h-6"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.6"
      >
        <path d="M10 7l-2 2a4 4 0 0 0 0 6 4 4 0 0 0 6 0l1-1" />
        <path d="M14 17l2-2a4 4 0 0 0 0-6 4 4 0 0 0-6 0l-1 1" />
      </svg>
    ),
  },
];

export function BaselinesSection() {
  return (
    <section id="reference-baselines" className="py-16 lg:py-24 bg-[#0B111A]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-12">
          <p className="text-sm uppercase tracking-[0.3em] text-[#9CA3AF]">
            Reference baselines
          </p>
          <h2 className="text-3xl sm:text-4xl font-semibold text-[#F3F4F6] mt-3">
            Reference Baselines
          </h2>
          <p className="text-[#9CA3AF] max-w-2xl mx-auto mt-4">
            We provide two reference implementations to help you get started.
            Each demonstrates a different architectural approach to building a
            Janus-compatible intelligence engine.
          </p>
        </div>

        <div className="grid md:grid-cols-2 gap-6 max-w-5xl mx-auto">
          {baselines.map((baseline, index) => (
            <BaselineCard key={baseline.id} baseline={baseline} index={index} />
          ))}
        </div>
      </div>
    </section>
  );
}

function BaselineCard({
  baseline,
  index,
}: {
  baseline: (typeof baselines)[number];
  index: number;
}) {
  return (
    <Link href={baseline.href} className="group h-full">
      <div
        className="glass-card p-6 rounded-xl transition-all h-full flex flex-col animate-fade-up"
        style={{ animationDelay: `${index * 120}ms` }}
      >
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 rounded-lg bg-[#63D297]/15 text-[#63D297]">
            {baseline.icon}
          </div>
          <h3 className="text-xl font-semibold text-[#F3F4F6]">
            {baseline.name}
          </h3>
        </div>

        <p className="text-[#9CA3AF] mb-4 flex-1">{baseline.description}</p>

        <ul className="space-y-2 mb-6">
          {baseline.highlights.map((highlight) => (
            <li key={highlight} className="flex items-center gap-2 text-sm text-[#D1D5DB]">
              <span className="w-1.5 h-1.5 rounded-full bg-[#63D297]" />
              {highlight}
            </li>
          ))}
        </ul>

        <div className="flex items-center gap-2 text-[#63D297] group-hover:text-[#7FDAA8] transition-colors">
          <span className="text-sm font-medium">View Documentation</span>
          <svg
            className="w-4 h-4 transition-transform group-hover:translate-x-1"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.6"
          >
            <path d="M5 12h14" />
            <path d="M13 6l6 6-6 6" />
          </svg>
        </div>
      </div>
    </Link>
  );
}
