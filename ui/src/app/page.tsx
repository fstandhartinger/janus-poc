import {
  Header,
  HeroSection,
  FeatureCards,
  HowItWorks,
  PoweredBy,
  Footer,
} from '@/components/landing';

export default function LandingPage() {
  return (
    <div className="min-h-screen aurora-bg">
      <Header />
      <main>
        <HeroSection />
        <FeatureCards />
        <HowItWorks />
        <PoweredBy />
      </main>
      <Footer />
    </div>
  );
}
