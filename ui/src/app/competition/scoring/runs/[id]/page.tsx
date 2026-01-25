import { Suspense } from 'react';
import { Header, Footer } from '@/components/landing';
import { RunDetailContent } from './RunDetailContent';

export default function RunDetailPage({ params }: { params: { id: string } }) {
  return (
    <div className="min-h-screen aurora-bg flex flex-col">
      <Header />
      <main className="flex-1 py-16">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <Suspense fallback={<RunDetailSkeleton />}>
            <RunDetailContent runId={params.id} />
          </Suspense>
        </div>
      </main>
      <Footer />
    </div>
  );
}

function RunDetailSkeleton() {
  return (
    <div className="animate-pulse space-y-6">
      <div className="h-8 bg-white/10 rounded w-1/3" />
      <div className="glass-card p-8 space-y-4">
        <div className="h-20 bg-white/10 rounded" />
        <div className="h-40 bg-white/10 rounded" />
      </div>
    </div>
  );
}
