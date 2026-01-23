import type { CSSProperties } from 'react';

interface StepProps {
  number: number;
  title: string;
  description: string;
  delay?: number;
}

function Step({ number, title, description, delay = 0 }: StepProps) {
  return (
    <div
      data-reveal
      className="reveal flex flex-col items-center text-center"
      style={{ '--reveal-delay': `${delay}ms` } as CSSProperties}
    >
      <div className="w-12 h-12 rounded-full bg-[#63D297] text-[#111827] flex items-center justify-center font-bold text-lg mb-4">
        {number}
      </div>
      <h3 className="text-lg font-semibold text-[#F3F4F6] mb-2">{title}</h3>
      <p className="text-[#9CA3AF] text-sm leading-relaxed max-w-xs">{description}</p>
    </div>
  );
}

export function HowItWorks() {
  const steps = [
    {
      number: 1,
      title: 'Submit',
      description:
        'Miners submit Docker containers with OpenAI-compatible API endpoints',
    },
    {
      number: 2,
      title: 'Compete',
      description:
        'Benchmarks score implementations on composite metrics: quality, speed, cost',
    },
    {
      number: 3,
      title: 'Win',
      description:
        'Top performers earn rewards and recognition on the leaderboard',
    },
  ];

  return (
    <section className="py-16 lg:py-24 bg-[#111726]/50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div data-reveal className="reveal text-center mb-12">
          <h2 className="text-3xl sm:text-4xl font-semibold text-[#F3F4F6] mb-4">
            How It Works
          </h2>
          <p className="text-lg text-[#9CA3AF] max-w-2xl mx-auto">
            Join the decentralized intelligence competition in three simple steps
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-8 lg:gap-12 relative">
          {/* Connecting line (desktop only) */}
          <div className="hidden md:block absolute top-6 left-1/6 right-1/6 h-0.5 bg-gradient-to-r from-transparent via-[#374151] to-transparent" />

          {steps.map((step, index) => (
            <Step key={step.number} delay={index * 120} {...step} />
          ))}
        </div>
      </div>
    </section>
  );
}
