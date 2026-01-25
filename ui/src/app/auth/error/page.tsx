import Link from 'next/link';

export default function AuthErrorPage({
  searchParams,
}: {
  searchParams?: { error?: string };
}) {
  const error = searchParams?.error || 'unknown';

  return (
    <div className="min-h-screen flex items-center justify-center px-6 py-12 bg-ink-950">
      <div className="glass-card max-w-md w-full p-8 text-center space-y-4">
        <h1 className="text-xl text-ink-100">Sign-in failed</h1>
        <p className="text-sm text-ink-400">
          We couldn&apos;t complete your sign-in request. Error: <span className="text-ink-200">{error}</span>
        </p>
        <Link href="/chat" className="btn-primary w-full">
          Back to chat
        </Link>
      </div>
    </div>
  );
}
