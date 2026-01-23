import type { CSSProperties } from 'react';

const ideals = [
  { title: 'Decentralized', description: 'No single company controls the network.' },
  { title: 'Permissionless', description: 'Anyone can compete, no approval needed.' },
  { title: 'Open Source', description: 'Transparent, auditable, and forkable.' },
  { title: 'Censorship Resistant', description: 'No government can shut it down.' },
  { title: 'Community Owned', description: 'Rewards flow to builders, not shareholders.' },
  { title: 'No Gatekeepers', description: 'No corporate overlords decide who can build.' },
  { title: 'Affordable', description: 'Open competition keeps pricing fair.' },
];

export function IdealsSection() {
  return (
    <section className="py-16 lg:py-24">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid lg:grid-cols-[1.1fr_1fr] gap-10 lg:gap-14 items-start">
          <div data-reveal className="reveal space-y-6">
            <p className="text-sm uppercase tracking-[0.3em] text-[#9CA3AF]">
              Built on Bittensor Ideals
            </p>
            <h2 className="text-3xl sm:text-4xl font-semibold text-[#F3F4F6]">
              Built on Bittensor Ideals
            </h2>
            <p className="text-lg text-[#D1D5DB] leading-relaxed">
              Janus is not just another intelligence platform - it is a return to the original
              promise of the internet: open, permissionless, and owned by no one.
            </p>
            <p className="text-[#9CA3AF]">
              We believe intelligence should be a public utility, not a corporate moat.
            </p>
          </div>

          <div
            data-reveal
            className="reveal"
            style={{ '--reveal-delay': '120ms' } as CSSProperties}
          >
            <div className="glass-card p-6 sm:p-8">
              <div className="grid sm:grid-cols-2 gap-4">
                {ideals.map((ideal) => (
                  <div key={ideal.title} className="flex gap-3">
                    <span className="mt-1 h-2 w-2 rounded-full bg-[#63D297]" />
                    <div>
                      <p className="text-sm font-semibold text-[#F3F4F6]">{ideal.title}</p>
                      <p className="text-sm text-[#9CA3AF] leading-relaxed">{ideal.description}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
