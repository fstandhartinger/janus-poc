'use client';

import Link from 'next/link';
import { useEffect } from 'react';

interface GlobalErrorProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function GlobalError({ error, reset }: GlobalErrorProps) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="min-h-screen aurora-bg flex items-center justify-center px-6 py-16">
      <div className="w-full max-w-lg rounded-2xl border border-ink-700 bg-ink-900/70 p-8 text-center shadow-xl">
        <p className="text-xs uppercase tracking-[0.3em] text-ink-500">System error</p>
        <h1 className="mt-3 text-2xl font-semibold text-ink-100">We hit a snag</h1>
        <p className="mt-2 text-sm text-ink-400">
          Please try again, or head back home if the issue persists.
        </p>
        <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:justify-center">
          <button
            type="button"
            onClick={reset}
            className="rounded-full border border-moss/40 bg-moss/10 px-5 py-2 text-sm font-semibold text-moss transition hover:bg-moss/20"
          >
            Try again
          </button>
          <Link
            href="/"
            className="rounded-full border border-ink-700 px-5 py-2 text-sm font-semibold text-ink-200 transition hover:border-ink-500 hover:text-ink-100"
          >
            Go home
          </Link>
        </div>
      </div>
    </div>
  );
}
