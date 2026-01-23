import { Header, Footer } from '@/components/landing';
import {
  ArchitectureOverview,
  BenchRunner,
  ComponentMarketplace,
  CompetitionOverview,
  FAQ,
  HeroSection,
  HowItWorks,
  Leaderboard,
  PrizePool,
  ScoringBreakdown,
  SubmissionGuide,
  SubmissionForm,
  TechRequirements,
} from './components';

export default function CompetitionPage() {
  return (
    <div className="min-h-screen aurora-bg flex flex-col">
      <Header />
      <main className="flex-1">
        <HeroSection />
        <CompetitionOverview />
        <Leaderboard />
        <HowItWorks />
        <PrizePool />
        <ComponentMarketplace />
        <ScoringBreakdown />
        <ArchitectureOverview />
        <TechRequirements />
        <BenchRunner />
        <SubmissionGuide />
        <SubmissionForm />
        <FAQ />
      </main>
      <Footer />
    </div>
  );
}
