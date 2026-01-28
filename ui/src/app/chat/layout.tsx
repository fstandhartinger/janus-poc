import { PWAInstallToast } from '@/components/PWAInstallToast';

export default function ChatLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <>
      {children}
      <PWAInstallToast />
    </>
  );
}
