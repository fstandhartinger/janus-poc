import { Header, Footer } from '@/components/landing';
import {
  ScoringHero,
  RunSubmitForm,
  ActiveRuns,
  RunHistory,
} from './components';

export default function ScoringPage() {
  return (
    <div className="min-h-screen aurora-bg flex flex-col">
      <Header />
      <main className="flex-1 py-16">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 space-y-12">
          <ScoringHero />
          <RunSubmitForm />
          <ActiveRuns />
          <RunHistory />
        </div>
      </main>
      <Footer />
    </div>
  );
}
