'use client';

import { usePWAInstall } from '@/hooks/usePWAInstall';
import { usePWAUpdate } from '@/hooks/usePWAUpdate';

function RefreshIcon() {
  return (
    <svg
      className="w-6 h-6 text-moss shrink-0"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M3 12a9 9 0 0 1 15.1-6.6" />
      <path d="M21 12a9 9 0 0 1-15.1 6.6" />
      <path d="M3 4v5h5" />
      <path d="M21 20v-5h-5" />
    </svg>
  );
}

function DownloadIcon() {
  return (
    <svg
      className="w-5 h-5 text-moss"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <path d="M7 10l5 5 5-5" />
      <path d="M12 15V3" />
    </svg>
  );
}

function CloseIcon() {
  return (
    <svg
      className="w-4 h-4 text-white/40"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M18 6L6 18" />
      <path d="M6 6l12 12" />
    </svg>
  );
}

export function PWAInstallToast() {
  const { showPrompt, install, dismiss, canInstall } = usePWAInstall();
  const { updateAvailable, applyUpdate } = usePWAUpdate();

  if (updateAvailable) {
    return (
      <div className="fixed bottom-4 left-4 right-4 z-50 md:hidden">
        <div className="glass-card p-4 rounded-xl border border-moss/30 shadow-lg flex items-center gap-3 animate-fade-up">
          <RefreshIcon />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-white">Update available</p>
            <p className="text-xs text-white/60">Load the newest version now</p>
          </div>
          <button
            onClick={applyUpdate}
            className="px-4 py-2 bg-moss text-black text-sm font-medium rounded-lg hover:bg-moss/90 transition-colors"
          >
            Update
          </button>
        </div>
      </div>
    );
  }

  if (!showPrompt || !canInstall) {
    return null;
  }

  return (
    <div className="fixed bottom-4 left-4 right-4 z-50 md:hidden animate-fade-up">
      <div className="glass-card p-4 rounded-xl border border-moss/30 shadow-lg">
        <div className="flex items-start gap-3">
          <div className="w-10 h-10 rounded-lg bg-moss/20 flex items-center justify-center shrink-0">
            <DownloadIcon />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-white">Install Janus</p>
            <p className="text-xs text-white/60 mt-0.5">
              Add to home screen for faster access
            </p>
          </div>
          <button
            onClick={dismiss}
            className="p-1 hover:bg-white/10 rounded-lg transition-colors shrink-0"
            aria-label="Close"
          >
            <CloseIcon />
          </button>
        </div>
        <div className="flex gap-2 mt-3">
          <button
            onClick={dismiss}
            className="flex-1 px-4 py-2 text-sm text-white/70 hover:text-white transition-colors"
          >
            Later
          </button>
          <button
            onClick={install}
            className="flex-1 px-4 py-2 bg-moss text-black text-sm font-medium rounded-lg hover:bg-moss/90 transition-colors"
          >
            Install
          </button>
        </div>
      </div>
    </div>
  );
}
