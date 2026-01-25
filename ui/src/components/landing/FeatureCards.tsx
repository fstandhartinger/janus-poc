import type { CSSProperties } from 'react';

type AudienceVariant = 'user' | 'builder';

interface BenefitCardProps {
  icon: React.ReactNode;
  title: string;
  description: string;
  variant: AudienceVariant;
  delay?: number;
}

function BenefitCard({
  icon,
  title,
  description,
  variant,
  delay = 0,
}: BenefitCardProps) {
  return (
    <div
      data-reveal
      className={`reveal benefit-card ${variant}`}
      style={{ '--reveal-delay': `${delay}ms` } as CSSProperties}
    >
      <div className="benefit-icon">{icon}</div>
      <h3 className="benefit-title">{title}</h3>
      <p className="benefit-description">{description}</p>
    </div>
  );
}

export function FeatureCards() {
  const userBenefits = [
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
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 17l6-6 4 4 7-7" />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M14 4h7v7" />
        </svg>
      ),
      title: 'Always Improving',
      description:
        'A competitive marketplace of intelligence engines means you always get the best. Implementations are continuously benchmarked for quality, speed, and cost.',
    },
  ];

  const builderBenefits = [
    {
      icon: (
        <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M5 4h14v3a5 5 0 01-5 5h-4a5 5 0 01-5-5V4z" />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 12v3a4 4 0 004 4 4 4 0 004-4v-3" />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 21h8" />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M5 6H3a3 3 0 003 3" />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 6h2a3 3 0 01-3 3" />
        </svg>
      ),
      title: 'Intelligence Rodeo',
      description:
        'Compete to build the best Janus implementation. Get benchmarked on quality, speed, and cost across diverse use cases. Top performers earn TAO rewards.',
    },
    {
      icon: (
        <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z" />
        </svg>
      ),
      title: 'Build & Earn',
      description:
        'Create reusable components: research tools, memory systems, specialized agents. Earn rewards whenever your components power other submissions.',
    },
  ];

  const audienceGroups = [
    {
      id: 'users',
      label: 'For Users',
      variant: 'user' as const,
      benefits: userBenefits,
    },
    {
      id: 'builders',
      label: 'For Builders',
      variant: 'builder' as const,
      benefits: builderBenefits,
    },
  ];

  return (
    <section className="why-janus-section py-16 lg:py-24">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div data-reveal className="reveal text-center mb-12">
          <h2 className="text-3xl sm:text-4xl font-semibold text-[#F3F4F6] mb-4">
            Why Janus?
          </h2>
          <p className="text-lg text-[#9CA3AF] max-w-2xl mx-auto">
            The next generation of competitive intelligence infrastructure
          </p>
        </div>

        <div className="space-y-12">
          {audienceGroups.map((group, groupIndex) => {
            const groupDelay = groupIndex * 120;
            return (
              <div
                key={group.id}
                className="audience-group"
                role="group"
                aria-labelledby={`${group.id}-audience`}
              >
                <div
                  data-reveal
                  className="reveal audience-label"
                  style={{ '--reveal-delay': `${groupDelay}ms` } as CSSProperties}
                >
                  <h3 id={`${group.id}-audience`} className={`audience-badge ${group.variant}`}>
                    {group.label}
                  </h3>
                </div>

                <div className="benefit-grid">
                  {group.benefits.map((benefit, index) => (
                    <BenefitCard
                      key={benefit.title}
                      {...benefit}
                      variant={group.variant}
                      delay={groupDelay + (index + 1) * 120}
                    />
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
