'use client';

import type { ReactNode } from 'react';

export interface ResearchStage {
  id: string;
  label: string;
  status: 'pending' | 'running' | 'complete' | 'error';
  detail?: string;
}

const STAGES = [
  { id: '1', label: 'Finding Sources' },
  { id: '2', label: 'Preparing Sandbox' },
  { id: '3', label: 'Installing Browser' },
  { id: '4', label: 'Launching Browser' },
  { id: '5', label: 'Crawling Pages' },
  { id: '6', label: 'Synthesizing Notes' },
  { id: '7', label: 'Drafting Report' },
  { id: '8', label: 'Cleaning Up' },
];

interface DeepResearchProgressProps {
  stages: ResearchStage[];
  isActive: boolean;
}

const StatusIcon = ({ status }: { status: ResearchStage['status'] }): ReactNode => {
  const baseClass = 'w-4 h-4';

  if (status === 'complete') {
    return (
      <svg viewBox="0 0 24 24" className={`${baseClass} text-moss`} fill="none" stroke="currentColor" strokeWidth="2">
        <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
      </svg>
    );
  }

  if (status === 'running') {
    return (
      <svg viewBox="0 0 24 24" className={`${baseClass} text-moss animate-spin`} fill="none" stroke="currentColor" strokeWidth="2">
        <circle cx="12" cy="12" r="10" strokeOpacity="0.3" />
        <path strokeLinecap="round" d="M22 12a10 10 0 0 1-10 10" />
      </svg>
    );
  }

  if (status === 'error') {
    return (
      <svg viewBox="0 0 24 24" className={`${baseClass} text-red-500`} fill="none" stroke="currentColor" strokeWidth="2">
        <path strokeLinecap="round" strokeLinejoin="round" d="M6 6l12 12M18 6l-12 12" />
      </svg>
    );
  }

  return (
    <svg viewBox="0 0 24 24" className={`${baseClass} text-ink-500`} fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="9" />
    </svg>
  );
};

export function DeepResearchProgress({ stages, isActive }: DeepResearchProgressProps) {
  if (!isActive) return null;

  return (
    <div className="mb-4 p-4 rounded-lg border border-moss/30 bg-moss/5">
      <div className="text-sm font-semibold text-moss mb-3">
        Deep Research in Progress
      </div>
      <div className="space-y-2">
        {STAGES.map((stage) => {
          const stageData = stages.find((item) => item.label === stage.label);
          const status = stageData?.status || 'pending';

          return (
            <div key={stage.id} className="flex items-center gap-2 text-sm">
              <StatusIcon status={status} />
              <span className={status === 'running' ? 'text-moss' : 'text-ink-400'}>
                {stage.label}
              </span>
              {stageData?.detail && (
                <span className="text-xs text-ink-500">
                  {stageData.detail}
                </span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
