import {
  Header,
  HeroSection,
  FeatureCards,
  HowItWorks,
  FlexibilitySection,
  IdealsSection,
  PoweredBy,
  Footer,
  ApiSection,
  ScrollReveal,
} from '@/components/landing';

export default function LandingPage() {
  return (
    <div className="min-h-screen aurora-luxe">
      <ScrollReveal />
      <Header />
      <main>
        <HeroSection />
        <FeatureCards />
        <ApiSection />
        <HowItWorks />
        <FlexibilitySection />
        <IdealsSection />
        <PoweredBy />
      </main>
      <Footer />
    </div>
  );
}
