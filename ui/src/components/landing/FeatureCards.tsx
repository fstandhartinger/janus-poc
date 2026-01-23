import type { CSSProperties } from 'react';

interface FeatureCardProps {
  icon: React.ReactNode;
  title: string;
  description: string;
  delay?: number;
}

function FeatureCard({ icon, title, description, delay = 0 }: FeatureCardProps) {
  return (
    <div
      data-reveal
      className="reveal glass-card p-6 sm:p-8"
      style={{ '--reveal-delay': `${delay}ms` } as CSSProperties}
    >
      <div className="w-12 h-12 rounded-xl bg-[#63D297]/10 flex items-center justify-center text-[#63D297] mb-4">
        {icon}
      </div>
      <h3 className="text-xl font-semibold text-[#F3F4F6] mb-3">{title}</h3>
      <p className="text-[#9CA3AF] leading-relaxed">{description}</p>
    </div>
  );
}

export function FeatureCards() {
  const features = [
    {
      icon: (
        <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
        </svg>
      ),
      title: 'Anything In, Anything Out',
      description:
        'Multimodal input (text, images, files) and multimodal output (text, code, images, artifacts). Your Janus engine handles it all.',
    },
    {
      icon: (
        <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M16 8v8m-4-5v5m-4-2v2m-2 4h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
        </svg>
      ),
      title: 'Intelligence Rodeo',
      description:
        'Compete to build the best intelligence engine. Benchmarks score implementations on many use cases and composite metrics: quality, speed, cost. Top performers earn rewards.',
    },
    {
      icon: (
        <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z" />
        </svg>
      ),
      title: 'Build & Earn',
      description:
        'Publish reusable components (research nodes, tools, memory systems). Earn rewards whenever another Janus submission uses your component.',
    },
  ];

  return (
    <section className="py-16 lg:py-24">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div data-reveal className="reveal text-center mb-12">
          <h2 className="text-3xl sm:text-4xl font-semibold text-[#F3F4F6] mb-4">
            Why Janus?
          </h2>
          <p className="text-lg text-[#9CA3AF] max-w-2xl mx-auto">
            The next generation of competitive intelligence infrastructure
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-6 lg:gap-8">
          {features.map((feature, index) => (
            <FeatureCard key={index} {...feature} delay={index * 120} />
          ))}
        </div>
      </div>
    </section>
  );
}
