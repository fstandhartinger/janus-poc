import { Header, Footer } from '@/components/landing';
import Link from 'next/link';

export default function MarketplacePage() {
  return (
    <div className="min-h-screen aurora-bg flex flex-col">
      <Header />
      <main className="flex-1 flex items-center justify-center">
        <div className="text-center px-4">
          <h1 className="text-4xl font-semibold text-[#F3F4F6] mb-4">
            Marketplace
          </h1>
          <p className="text-[#9CA3AF] mb-8 max-w-md mx-auto">
            The component marketplace is coming soon. Submit reusable components
            and earn rewards when other miners use them.
          </p>
          <Link href="/" className="btn-primary">
            Back to Home
          </Link>
        </div>
      </main>
      <Footer />
    </div>
  );
}
