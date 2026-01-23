import { Header, Footer } from '@/components/landing';
import {
  ArchitectureOverview,
  BenchRunner,
  FAQ,
  HeroSection,
  HowItWorks,
  Leaderboard,
  ScoringBreakdown,
  SubmissionForm,
  TechRequirements,
} from './components';

export default function CompetitionPage() {
  return (
    <div className="min-h-screen aurora-bg flex flex-col">
      <Header />
      <main className="flex-1">
        <HeroSection />
        <Leaderboard />
        <HowItWorks />
        <ScoringBreakdown />
        <ArchitectureOverview />
        <TechRequirements />
        <BenchRunner />
        <SubmissionForm />
        <FAQ />
      </main>
      <Footer />
    </div>
  );
}
