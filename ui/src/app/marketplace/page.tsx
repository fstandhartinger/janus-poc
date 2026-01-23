import { Header, Footer } from '@/components/landing';
import { MarketplaceView } from './MarketplaceView';

export default function MarketplacePage() {
  return (
    <div className="min-h-screen aurora-bg flex flex-col">
      <Header />
      <MarketplaceView />
      <Footer />
    </div>
  );
}
