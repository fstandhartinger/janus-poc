'use client';

import Link from 'next/link';
import { HeroVideo } from './HeroVideo';

export function HeroSection() {
  return (
    <section className="relative overflow-hidden">
      <div className="absolute inset-0 aurora-glow pointer-events-none" />

      <HeroVideo />

      <div className="relative max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 pb-16 pt-12 lg:pt-20 text-center">
        <div data-reveal className="reveal">
          <p className="hero-kicker">The Open Intelligence Rodeo</p>
          <h1 className="hero-title">
            <span className="gradient-text">JANUS</span>
          </h1>
          <p className="hero-subtitle">
            Anything In. Anything Out. Build the intelligence engine for the decentralized
            intelligence network powered by Bittensor.
          </p>

          <div className="mt-10 flex flex-col sm:flex-row gap-4 justify-center">
            <Link href="/chat" className="btn-primary text-base px-8 py-3">
              Janus Chat
            </Link>
            <Link href="/competition" className="btn-secondary text-base px-8 py-3">
              Join the Competition
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}
