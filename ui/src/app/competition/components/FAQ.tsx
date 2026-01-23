'use client';

import { useState } from 'react';

const faqs = [
  {
    question: 'What technology can I use?',
    answer:
      'Any stack works: CLI implementations, workflow engines, custom Python/Node, or hybrid systems. We only enforce the OpenAI API contract.',
  },
  {
    question: 'How do I stream intermediate steps?',
    answer:
      'Stream reasoning_content in your SSE chunks. The streaming spec (05) details the expected payloads and cadence.',
  },
  {
    question: 'What models can I call?',
    answer:
      'Use the Chutes inference proxy for any public Chutes model. External paid APIs are blocked by the network guardrails.',
  },
  {
    question: 'How often is the leaderboard updated?',
    answer:
      'Public benchmarks refresh daily. Real-time updates arrive once the automated submission pipeline launches.',
  },
  {
    question: 'What are the prizes?',
    answer:
      'Prize pool allocations are announced each epoch. Top 3 competitors earn rewards when the round closes.',
  },
];

export function FAQ() {
  const [openIndex, setOpenIndex] = useState<number | null>(0);

  return (
    <section className="py-16 lg:py-24 bg-[#0B111A]">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-10">
          <p className="text-sm uppercase tracking-[0.3em] text-[#9CA3AF]">FAQ</p>
          <h2 className="text-3xl sm:text-4xl font-semibold text-[#F3F4F6] mt-3">
            Rodeo Questions Answered
          </h2>
          <p className="text-[#9CA3AF] mt-4">
            Need a quick answer before you ride? Start here.
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
                  <span className="text-[#63D297] text-xl">{isOpen ? '−' : '+'}</span>
                </button>
                {isOpen && (
                  <p className="mt-4 text-sm text-[#9CA3AF] leading-relaxed">{faq.answer}</p>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
