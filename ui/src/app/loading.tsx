export default function Loading() {
  return (
    <div className="min-h-screen aurora-bg flex items-center justify-center px-6 py-16">
      <div className="w-full max-w-md rounded-2xl border border-ink-700 bg-ink-900/70 p-8 text-center shadow-xl">
        <div className="mx-auto mb-4 h-10 w-10 animate-spin rounded-full border-2 border-ink-700 border-t-moss" />
        <p className="text-sm uppercase tracking-[0.3em] text-ink-500">Loading</p>
        <p className="mt-2 text-sm text-ink-400">
          Preparing your Janus experience...
        </p>
      </div>
    </div>
  );
}
