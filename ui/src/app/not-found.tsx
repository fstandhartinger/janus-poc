import Link from 'next/link';

export default function NotFound() {
  return (
    <div className="min-h-screen aurora-bg flex items-center justify-center px-6 py-16">
      <div className="w-full max-w-lg rounded-2xl border border-ink-700 bg-ink-900/70 p-8 text-center shadow-xl">
        <p className="text-xs uppercase tracking-[0.3em] text-ink-500">404</p>
        <h1 className="mt-3 text-2xl font-semibold text-ink-100">Page not found</h1>
        <p className="mt-2 text-sm text-ink-400">
          The page you are looking for does not exist. Let&apos;s get you back on track.
        </p>
        <Link
          href="/"
          className="mt-6 inline-flex rounded-full border border-moss/40 bg-moss/10 px-5 py-2 text-sm font-semibold text-moss transition hover:bg-moss/20"
        >
          Return home
        </Link>
      </div>
    </div>
  );
}
