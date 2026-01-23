'use client';

import { useState } from 'react';

const requirements = [
  {
    title: 'API Contract',
    items: [
      'Expose POST /v1/chat/completions (OpenAI-compatible).',
      'Expose GET /health with a fast response.',
      'Optional: GET /metrics and GET /debug endpoints.',
    ],
  },
  {
    title: 'Streaming Requirements',
    items: [
      'Support "stream": true for SSE responses.',
      'Stream reasoning_content for intermediate steps.',
      'Stream content for final output.',
      'Maximum 10-second gap between chunks.',
    ],
  },
  {
    title: 'Resource Limits',
    items: [
      'Container budget: 4 vCPU, 8GB RAM, 20GB disk.',
      'Request timeout: 5 minutes end-to-end.',
      'Network: whitelist egress only (platform services).',
    ],
  },
  {
    title: 'Security',
    items: [
      'No hardcoded API keys or secrets in the image.',
      'No external paid API calls.',
      'Container runs in TEE isolation.',
    ],
  },
];

export function TechRequirements() {
  const [openIndex, setOpenIndex] = useState(0);

  return (
    <section className="py-16 lg:py-24">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-10">
          <p className="text-sm uppercase tracking-[0.3em] text-[#9CA3AF]">Requirements</p>
          <h2 className="text-3xl sm:text-4xl font-semibold text-[#F3F4F6] mt-3">
            Technical Requirements
          </h2>
          <p className="text-[#9CA3AF] mt-4">
            Ensure your container meets the contract before submitting to the
            competition.
          </p>
        </div>

        <div className="space-y-4">
          {requirements.map((requirement, index) => {
            const isOpen = openIndex === index;
            return (
              <div key={requirement.title} className="glass-card p-5">
                <button
                  type="button"
                  className="w-full flex items-center justify-between text-left"
                  onClick={() => setOpenIndex(isOpen ? -1 : index)}
                  aria-expanded={isOpen}
                >
                  <span className="text-lg font-semibold text-[#F3F4F6]">
                    {requirement.title}
                  </span>
                  <span className="text-[#63D297] text-xl">
                    {isOpen ? '−' : '+'}
                  </span>
                </button>
                {isOpen && (
                  <ul className="mt-4 space-y-2 text-sm text-[#9CA3AF] list-disc list-inside">
                    {requirement.items.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
