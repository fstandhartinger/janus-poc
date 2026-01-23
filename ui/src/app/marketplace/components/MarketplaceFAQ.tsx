'use client';

import { useState } from 'react';

const faqs = [
  {
    question: 'How do rewards work?',
    answer:
      'When a miner using your component earns rewards, a percentage is distributed to component developers based on usage attribution.',
  },
  {
    question: 'What makes a good component?',
    answer:
      'Clear API contract, strong documentation, reliable performance, and security compliance are the most important signals.',
  },
  {
    question: 'Can I use external APIs?',
    answer:
      'Yes, but external dependencies must be whitelisted and comply with Janus security guardrails.',
  },
  {
    question: 'How is usage tracked?',
    answer:
      'Miners declare component dependencies in their submissions, and the platform tracks invocations during benchmark runs.',
  },
  {
    question: 'What is the revenue share?',
    answer:
      'Initial proposal: 10 to 20 percent of miner rewards are distributed to component developers.',
  },
];

export function MarketplaceFAQ() {
  const [openIndex, setOpenIndex] = useState<number | null>(0);

  return (
    <section className="py-16 lg:py-24">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-10">
          <p className="text-sm uppercase tracking-[0.3em] text-[#9CA3AF]">FAQ</p>
          <h2 className="text-3xl sm:text-4xl font-semibold text-[#F3F4F6] mt-3">
            Marketplace Questions Answered
          </h2>
          <p className="text-[#9CA3AF] mt-4">
            Everything you need to know before shipping your first component.
          </p>
        </div>

        <div className="space-y-4">
          {faqs.map((faq, index) => {
            const isOpen = openIndex === index;
            return (
              <div key={faq.question} className="glass-card p-5">
                <button
                  type="button"
                  className="w-full flex items-center justify-between text-left"
                  onClick={() => setOpenIndex(isOpen ? null : index)}
                  aria-expanded={isOpen}
                >
                  <span className="text-lg font-semibold text-[#F3F4F6]">
                    {faq.question}
                  </span>
                  <span className="text-[#63D297] text-xl">{isOpen ? '-' : '+'}</span>
                </button>
                {isOpen && (
                  <p className="mt-4 text-sm text-[#9CA3AF] leading-relaxed">
                    {faq.answer}
                  </p>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
