import {
  Header,
  HeroSection,
  FeatureCards,
  HowItWorks,
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
        <PoweredBy />
      </main>
      <Footer />
    </div>
  );
}
