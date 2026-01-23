import Image from 'next/image';
import Link from 'next/link';

export function HeroSection() {
  return (
    <section className="relative min-h-[80vh] flex items-center">
      {/* Aurora background overlay */}
      <div className="absolute inset-0 aurora-glow pointer-events-none" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 lg:py-24">
        <div className="grid lg:grid-cols-2 gap-12 lg:gap-16 items-center">
          {/* Text Content */}
          <div className="text-center lg:text-left">
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-semibold leading-tight mb-6">
              <span className="gradient-text">JANUS</span>
            </h1>
            <p className="text-xl sm:text-2xl text-[#D1D5DB] mb-4">
              The Open Intelligence Rodeo
            </p>
            <p className="text-lg text-[#9CA3AF] mb-8 max-w-xl mx-auto lg:mx-0">
              Anything In. Anything Out. Compete to build the best AI agent on the
              decentralized intelligence network powered by Bittensor Subnet 64.
            </p>

            {/* CTA Buttons */}
            <div className="flex flex-col sm:flex-row gap-4 justify-center lg:justify-start">
              <Link href="/chat" className="btn-primary text-base px-8 py-3">
                Try Manus Chat
              </Link>
              <Link href="/competition" className="btn-secondary text-base px-8 py-3">
                Join the Competition
              </Link>
            </div>
          </div>

          {/* Hero Image */}
          <div className="relative flex justify-center lg:justify-end">
            <div className="relative w-full max-w-lg lg:max-w-xl">
              <Image
                src="/hero-img.png"
                alt="Janus riding an iridescent bull"
                width={600}
                height={600}
                priority
                className="w-full h-auto drop-shadow-2xl"
              />
              {/* Glow effect behind image */}
              <div className="absolute inset-0 -z-10 blur-3xl opacity-30">
                <div className="w-full h-full bg-gradient-to-br from-[#63D297] via-[#8B5CF6] to-[#FA5D19]" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
