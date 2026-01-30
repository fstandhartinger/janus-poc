'use client';

import { useCallback, useEffect, useRef } from 'react';

interface MermaidDiagramModalProps {
  svg: string;
  ariaLabel?: string;
  onClose: () => void;
}

export function MermaidDiagramModal({ svg, ariaLabel, onClose }: MermaidDiagramModalProps) {
  const modalRef = useRef<HTMLDivElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  // Store onClose in a ref to avoid re-running effects when callback changes
  const onCloseRef = useRef(onClose);

  // Keep ref updated with latest callback
  useEffect(() => {
    onCloseRef.current = onClose;
  }, [onClose]);

  // Focus close button on mount
  useEffect(() => {
    closeButtonRef.current?.focus();
  }, []);

  // Escape key handler - use ref to avoid dependency on onClose
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        onCloseRef.current();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, []); // Empty dependency array - uses ref

  // Lock body scroll while modal is open
  useEffect(() => {
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = '';
    };
  }, []);

  // Handle backdrop click - only close if clicking the backdrop itself
  const handleBackdropClick = useCallback((e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      e.stopPropagation();
      onCloseRef.current();
    }
  }, []);

  // Handle close button click
  const handleCloseClick = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    onCloseRef.current();
  }, []);

  // Prevent clicks inside modal content from propagating
  const handleContentClick = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
  }, []);

  return (
    <div
      ref={modalRef}
      className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/90 backdrop-blur-sm animate-fade-in"
      onClick={handleBackdropClick}
      role="dialog"
      aria-modal="true"
      aria-label={ariaLabel ?? 'Diagram full view'}
    >
      <button
        ref={closeButtonRef}
        onClick={handleCloseClick}
        className="absolute top-4 right-4 text-white/60 hover:text-white transition-colors z-10"
        aria-label="Close diagram"
      >
        <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
          <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>

      <div
        className="relative max-w-[90vw] max-h-[90vh] overflow-auto bg-[#0B0F14] rounded-2xl p-8 shadow-2xl"
        onClick={handleContentClick}
      >
        <div
          className="mermaid-modal-content"
          role="img"
          aria-label={ariaLabel}
          dangerouslySetInnerHTML={{ __html: svg }}
        />
        <div className="absolute -inset-4 bg-[#63D297]/10 blur-3xl -z-10 rounded-full pointer-events-none" />
      </div>
    </div>
  );
}
