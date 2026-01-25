'use client';

import { useEffect, useRef, useState } from 'react';

import { MermaidDiagram } from '@/components/MermaidDiagram';

import { prizePoolSnapshot } from './prizePoolData';

const diagram = `flowchart TD
    A[Daily Revenue] -->|Portion flows to| B[Prize Pool]
    B -->|Accumulates while| C{Same champion?}
    C -->|Yes| B
    C -->|No| D[New #1 Claims Pool]
    D -->|Pool resets| E[New Pool Starts]
    E --> B`;

const exampleScenario = [
  { day: 1, event: 'Miner A submits, takes #1', balance: '$100' },
  { day: 2, event: 'No change', balance: '$200' },
  { day: 3, event: 'No change', balance: '$300' },
  { day: 4, event: 'No change', balance: '$400' },
  { day: 5, event: 'Miner B takes #1, claims $400', balance: '$0 -> $100' },
  { day: 6, event: 'No change', balance: '$200' },
  { day: 7, event: 'Miner C takes #1, claims $200', balance: '$0 -> $100' },
];

const claimRules = [
  'Ties are broken by the earliest verified submission timestamp. If verification is still in progress, payouts pause until the tie is resolved.',
  'Disqualifications for security or integrity violations void the claim. The pool remains and moves to the next highest verified submission.',
  'Disputes trigger an audit window. Funds are released only after the review finishes and results are published.',
];

const transparencyItems = [
  'The current pool balance is displayed on the leaderboard and this page.',
  'All contributions and payouts are recorded on-chain on Bittensor.',
  'Historical pool data is publicly accessible and linked from the leaderboard.',
  'The system moves toward fully automated, on-chain settlement over time.',
];

const whyThisModel = [
  'Incentivizes improvement: the longer a champion holds #1, the bigger the bounty for beating them.',
  'Rewards sustained excellence: a clear bar is set and every challenger knows what is at stake.',
  'Continuous competition: there is always a reason to iterate and climb.',
  'Transparent economics: everyone can see the pool, the claims, and the reset history.',
];

export function PrizePool() {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [isVisible, setIsVisible] = useState(() => {
    if (typeof window === 'undefined') {
      return false;
    }
    return !('IntersectionObserver' in window);
  });
  const [scenarioExpanded, setScenarioExpanded] = useState(false);

  useEffect(() => {
    if (isVisible) {
      return;
    }
    const container = containerRef.current;
    if (!container) {
      return;
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsVisible(true);
          observer.disconnect();
        }
      },
      { rootMargin: '120px' }
    );

    observer.observe(container);

    return () => observer.disconnect();
  }, [isVisible]);

  return (
    <section id="prize-pool" className="py-16 lg:py-24 bg-[#0B111A]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-12">
        <div className="grid lg:grid-cols-[1.1fr_0.9fr] gap-10 items-start">
          <div className="space-y-4">
            <p className="text-sm uppercase tracking-[0.3em] text-[#9CA3AF]">Prize pool</p>
            <h2 className="text-3xl sm:text-4xl font-semibold text-[#F3F4F6]">
              The Prize Pool
            </h2>
            <p className="text-[#9CA3AF]">
              The Janus competition features a unique accumulating prize pool that
              rewards sustained excellence and keeps the competition moving. The pool
              grows daily while a champion holds the top spot, and the next
              breakthrough claims the entire balance.
            </p>
            <p className="text-[#9CA3AF]">
              This is not a one time hackathon. It is a continuous race where the prize
              for beating the leader gets bigger every day.
            </p>
          </div>

          <div className="glass-card p-6 space-y-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-[#63D297]/15 text-[#63D297] flex items-center justify-center">
                <svg
                  className="w-5 h-5"
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
              </div>
              <div>
                <p className="text-xs uppercase tracking-[0.2em] text-[#9CA3AF]">
                  Current prize pool
                </p>
                <p className="text-3xl font-semibold text-[#F3F4F6]">
                  {prizePoolSnapshot.amountDisplay}
                </p>
              </div>
            </div>
            <div className="grid gap-3 text-sm text-[#9CA3AF]">
              <div className="flex items-center justify-between">
                <span>Accumulating since</span>
                <span className="text-[#F3F4F6] font-semibold">
                  {prizePoolSnapshot.accumulatingSince}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span>Days at #1</span>
                <span className="text-[#F3F4F6] font-semibold">
                  {prizePoolSnapshot.daysAtTop}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span>Current champion</span>
                <span className="text-[#F3F4F6] font-semibold">
                  {prizePoolSnapshot.champion}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span>Miner</span>
                <span className="text-[#F3F4F6] font-semibold">
                  {prizePoolSnapshot.miner}
                </span>
              </div>
            </div>
            <div className="flex flex-wrap gap-3 pt-2">
              <a href="#pool-history" className="text-sm text-[#63D297] hover:underline">
                View Pool History
              </a>
              <a href="#pool-rules" className="text-sm text-[#63D297] hover:underline">
                Claim Rules
              </a>
            </div>
          </div>
        </div>

        <div className="grid lg:grid-cols-[1.1fr_0.9fr] gap-10 items-start">
          <div ref={containerRef} className="glass-card p-6 min-h-[300px]">
            {isVisible ? (
              <MermaidDiagram
                chart={diagram}
                className="w-full"
                ariaLabel="Prize pool accumulation diagram"
              />
            ) : (
              <div className="h-full flex items-center justify-center text-sm text-[#9CA3AF] animate-pulse">
                Loading prize pool diagram...
              </div>
            )}
          </div>

          <div className="space-y-4">
            <h3 className="text-2xl font-semibold text-[#F3F4F6]">How It Works</h3>
            <ol className="space-y-3 text-sm text-[#9CA3AF] list-decimal list-inside">
              <li>
                <span className="text-[#F3F4F6] font-semibold">Daily contribution:</span>{' '}
                A portion of Janus platform revenue flows into the pool every day.
              </li>
              <li>
                <span className="text-[#F3F4F6] font-semibold">Accumulation:</span>{' '}
                The pool grows as long as the same implementation holds the #1 rank.
              </li>
              <li>
                <span className="text-[#F3F4F6] font-semibold">Claim:</span>{' '}
                When a new implementation takes the top spot, the miner behind it
                claims the entire accumulated pool.
              </li>
              <li>
                <span className="text-[#F3F4F6] font-semibold">Reset:</span> After payout,
                the pool resets to zero and begins accumulating again.
              </li>
            </ol>
          </div>
        </div>

        <div className="glass-card overflow-hidden">
          <button
            type="button"
            onClick={() => setScenarioExpanded(!scenarioExpanded)}
            className="w-full p-6 flex items-center justify-between text-left hover:bg-white/5 transition-colors"
            aria-expanded={scenarioExpanded}
            aria-controls="example-scenario"
          >
            <div>
              <p className="text-xs uppercase tracking-[0.2em] text-[#9CA3AF]">
                Example scenario
              </p>
              <p className="text-sm text-[#6B7280] mt-1">
                {scenarioExpanded ? 'Click to collapse' : 'See how the prize pool grows and resets'}
              </p>
            </div>
            <svg
              className={`w-5 h-5 text-[#9CA3AF] transition-transform ${scenarioExpanded ? 'rotate-180' : ''}`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>
          {scenarioExpanded && (
            <div id="example-scenario" className="px-6 pb-6 overflow-x-auto">
              <table className="w-full text-left border-separate border-spacing-y-2">
                <thead>
                  <tr className="text-xs uppercase tracking-[0.2em] text-[#9CA3AF]">
                    <th className="pb-2">Day</th>
                    <th className="pb-2">Event</th>
                    <th className="pb-2">Pool balance</th>
                  </tr>
                </thead>
                <tbody>
                  {exampleScenario.map((row) => (
                    <tr key={row.day} className="bg-[#0F172A]/40 rounded-lg">
                      <td className="py-3 px-3 font-semibold text-[#F3F4F6]">{row.day}</td>
                      <td className="py-3 px-3 text-[#D1D5DB]">{row.event}</td>
                      <td className="py-3 px-3 text-[#9CA3AF]">{row.balance}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div className="grid lg:grid-cols-2 gap-6">
          <div className="glass-card p-6 space-y-4">
            <h3 className="text-2xl font-semibold text-[#F3F4F6]">Why This Model?</h3>
            <ul className="space-y-3 text-sm text-[#9CA3AF] list-disc list-inside">
              {whyThisModel.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>

          <div id="pool-history" className="glass-card p-6 space-y-4">
            <h3 className="text-2xl font-semibold text-[#F3F4F6]">Pool Transparency</h3>
            <ul className="space-y-3 text-sm text-[#9CA3AF] list-disc list-inside">
              {transparencyItems.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>
        </div>

        <div className="space-y-4">
          <h3 className="text-2xl font-semibold text-[#F3F4F6]">Payout Process</h3>
          <div className="grid lg:grid-cols-2 gap-6">
            <div className="glass-card p-6 space-y-3">
              <p className="text-sm uppercase tracking-[0.2em] text-[#9CA3AF]">
                Current (Phase 1 - Manual)
              </p>
              <ol className="space-y-2 text-sm text-[#9CA3AF] list-decimal list-inside">
                <li>New #1 is verified via benchmark run.</li>
                <li>Results are reviewed for integrity.</li>
                <li>Payout is initiated to the miner&apos;s Bittensor coldkey.</li>
                <li>The pool resets and the transaction is logged.</li>
              </ol>
            </div>
            <div className="glass-card p-6 space-y-3">
              <p className="text-sm uppercase tracking-[0.2em] text-[#9CA3AF]">
                Future (Phase 2 - Automated)
              </p>
              <ol className="space-y-2 text-sm text-[#9CA3AF] list-decimal list-inside">
                <li>Benchmark results trigger on-chain verification.</li>
                <li>Smart contracts transfer the pool to the winner.</li>
                <li>The pool resets atomically.</li>
                <li>No manual intervention is required.</li>
              </ol>
            </div>
          </div>
        </div>

        <div id="pool-rules" className="glass-card p-6 space-y-4">
          <h3 className="text-2xl font-semibold text-[#F3F4F6]">Claim Rules</h3>
          <ul className="space-y-3 text-sm text-[#9CA3AF] list-disc list-inside">
            {claimRules.map((rule) => (
              <li key={rule}>{rule}</li>
            ))}
          </ul>
          <p className="text-sm text-[#9CA3AF]">
            Questions about rulings or disputes should be raised in the competition issue
            tracker before payouts are finalized.
          </p>
        </div>
      </div>
    </section>
  );
}
