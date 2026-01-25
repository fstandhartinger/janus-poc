import Link from 'next/link';

export function ScoringNav() {
  return (
    <section className="py-8 bg-[#111726]/50">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="glass-card p-6 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h3 className="text-lg font-semibold text-[#F3F4F6]">
              Ready to Test Your Implementation?
            </h3>
            <p className="text-[#9CA3AF] text-sm mt-1">
              Run the official benchmarks against your API or container
            </p>
          </div>
          <Link
            href="/competition/scoring"
            className="px-6 py-3 bg-[#63D297] text-[#0F1419] font-semibold rounded-lg
                     hover:bg-[#63D297]/90 transition"
          >
            Start Scoring Run
          </Link>
        </div>
      </div>
    </section>
  );
}
