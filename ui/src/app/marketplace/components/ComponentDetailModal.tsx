'use client';

import { useEffect } from 'react';
import { Component, ComponentCategory, ComponentStatus } from './types';

const categoryStyles: Record<ComponentCategory, string> = {
  research: 'bg-[#3B82F6]/15 text-[#93C5FD]',
  coding: 'bg-[#63D297]/15 text-[#63D297]',
  memory: 'bg-[#8B5CF6]/15 text-[#C4B5FD]',
  tools: 'bg-[#F59E0B]/15 text-[#FCD34D]',
  models: 'bg-[#FA5D19]/15 text-[#FDBA74]',
};

const categoryLabels: Record<ComponentCategory, string> = {
  research: 'Research',
  coding: 'Coding',
  memory: 'Memory',
  tools: 'Tools',
  models: 'Models',
};

const statusStyles: Record<ComponentStatus, string> = {
  available: 'bg-[#63D297]/15 text-[#63D297]',
  coming_soon: 'bg-[#8B5CF6]/15 text-[#C4B5FD]',
  deprecated: 'bg-[#FA5D19]/15 text-[#FDBA74]',
};

const statusLabels: Record<ComponentStatus, string> = {
  available: 'Available',
  coming_soon: 'Coming Soon',
  deprecated: 'Deprecated',
};

interface ComponentDetailModalProps {
  component: Component | null;
  onClose: () => void;
}

export function ComponentDetailModal({ component, onClose }: ComponentDetailModalProps) {
  useEffect(() => {
    if (!component) {
      return;
    }
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose();
      }
    };

    document.body.style.overflow = 'hidden';
    window.addEventListener('keydown', handleKeyDown);

    return () => {
      document.body.style.overflow = '';
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [component, onClose]);

  if (!component) {
    return null;
  }

  const rating = component.rating ?? 0;
  const totalCalls = component.totalCalls ?? 0;
  const earnings = component.earnings ?? 0;
  const versionHistory = component.versionHistory ?? [];
  const reviews = component.reviews ?? [];

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center p-4 sm:p-6 overflow-y-auto">
      <div
        className="absolute inset-0 bg-black/70 backdrop-blur-sm"
        onClick={onClose}
        aria-hidden
      />
      <div
        className="relative w-full max-w-3xl bg-[#0B111A] border border-[#1F2937] rounded-2xl shadow-2xl"
        role="dialog"
        aria-modal="true"
      >
        <div className="flex items-start justify-between p-6 border-b border-[#1F2937]">
          <div className="flex items-start gap-4">
            <div className="component-card-thumbnail rounded-xl p-3">
              <img
                src={component.icon ?? '/marketplace/tools.svg'}
                alt=""
                loading="lazy"
                decoding="async"
                className="h-10 w-10"
              />
            </div>
            <div>
              <h2 className="text-2xl font-semibold text-[#F3F4F6]">
                {component.name}
              </h2>
              <p className="text-sm text-[#9CA3AF]">by {component.author}</p>
              <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-[#9CA3AF]">
                <span className={`px-3 py-1 rounded-full ${categoryStyles[component.category]}`}>
                  {categoryLabels[component.category]}
                </span>
                <span className={`px-3 py-1 rounded-full ${statusStyles[component.status]}`}>
                  {statusLabels[component.status]}
                </span>
                <span>v{component.version}</span>
              </div>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-[#9CA3AF] hover:text-[#F3F4F6]"
            aria-label="Close component details"
          >
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <line x1="5" y1="5" x2="19" y2="19" />
              <line x1="19" y1="5" x2="5" y2="19" />
            </svg>
          </button>
        </div>

        <div className="p-6 space-y-6">
          <div className="space-y-2">
            <h3 className="text-lg font-semibold text-[#F3F4F6]">Description</h3>
            <p className="text-sm text-[#9CA3AF] leading-relaxed">
              {component.longDescription ?? component.description}
            </p>
          </div>

          <div className="grid sm:grid-cols-3 gap-4">
            <div className="glass p-4 rounded-xl">
              <p className="text-xs uppercase tracking-[0.2em] text-[#9CA3AF]">Miners</p>
              <p className="text-xl font-semibold text-[#F3F4F6] mt-2">
                {component.usageCount}
              </p>
            </div>
            <div className="glass p-4 rounded-xl">
              <p className="text-xs uppercase tracking-[0.2em] text-[#9CA3AF]">Total Calls</p>
              <p className="text-xl font-semibold text-[#F3F4F6] mt-2">
                {totalCalls.toLocaleString()}
              </p>
            </div>
            <div className="glass p-4 rounded-xl">
              <p className="text-xs uppercase tracking-[0.2em] text-[#9CA3AF]">Earnings</p>
              <p className="text-xl font-semibold text-[#63D297] mt-2">
                ${earnings.toLocaleString()}
              </p>
            </div>
          </div>

          <div className="space-y-2">
            <h3 className="text-lg font-semibold text-[#F3F4F6]">Integration Guide</h3>
            <pre className="bg-[#0B0F14] border border-[#1F2937] rounded-xl p-4 text-xs text-[#D1D5DB] overflow-x-auto">
              <code className="font-mono">
                {component.integrationExample ?? 'Integration guide coming soon.'}
              </code>
            </pre>
          </div>

          <div className="space-y-2">
            <h3 className="text-lg font-semibold text-[#F3F4F6]">API Contract</h3>
            <div className="glass p-4 rounded-xl space-y-2 text-sm text-[#D1D5DB]">
              <div className="flex items-center justify-between">
                <span className="text-[#9CA3AF]">Type</span>
                <span className="uppercase tracking-[0.2em] text-xs">{component.contract.type}</span>
              </div>
              {component.contract.url && (
                <div className="flex items-center justify-between">
                  <span className="text-[#9CA3AF]">Spec</span>
                  <span className="text-[#F3F4F6] truncate max-w-[60%]">
                    {component.contract.url}
                  </span>
                </div>
              )}
              {component.contract.tools && (
                <div className="flex items-start justify-between gap-4">
                  <span className="text-[#9CA3AF]">Tools</span>
                  <span className="text-right text-[#F3F4F6]">
                    {component.contract.tools.join(', ')}
                  </span>
                </div>
              )}
            </div>
          </div>

          <div className="grid sm:grid-cols-2 gap-4">
            <div className="glass p-4 rounded-xl">
              <h4 className="text-sm font-semibold text-[#F3F4F6]">Version History</h4>
              <ul className="mt-3 space-y-2 text-sm text-[#9CA3AF]">
                {versionHistory.length > 0 ? (
                  versionHistory.map((version) => <li key={version}>v{version}</li>)
                ) : (
                  <li>Version history coming soon.</li>
                )}
              </ul>
            </div>
            <div className="glass p-4 rounded-xl">
              <h4 className="text-sm font-semibold text-[#F3F4F6]">Reviews</h4>
              <div className="mt-3 space-y-3 text-sm text-[#9CA3AF]">
                {rating > 0 ? (
                  <p>Average rating: {rating.toFixed(1)} / 5</p>
                ) : (
                  <p>No ratings yet.</p>
                )}
                {reviews.length > 0 ? (
                  reviews.map((review) => (
                    <div key={review.author} className="border-t border-[#1F2937] pt-2">
                      <p className="text-[#F3F4F6] text-xs">{review.author}</p>
                      <p>{review.comment}</p>
                    </div>
                  ))
                ) : (
                  <p>Reviews are coming soon.</p>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
