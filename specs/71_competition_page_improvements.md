# Spec 70: Competition Page Improvements

## Status: DRAFT

## Context / Why

The competition page is comprehensive but excessively long and has several issues:

1. Mermaid diagrams are static - should be clickable to view full-size
2. UML sequence diagram incorrectly shows "gpt-4o-mini" (Chutes doesn't offer OpenAI models)
3. Rodeo rankings table needs updated entries reflecting actual baselines
4. Several sections always expanded make page feel overwhelming
5. Prize pool amount outdated
6. "Bittensor Hotkey Requirement" section uses crypto-heavy terminology that may alienate developers unfamiliar with Bittensor

## Goals

- Add clickable Mermaid diagrams with full-size modal view
- Fix model reference to use DeepSeek V3.2 instead of gpt-4o-mini
- Update leaderboard with correct baseline names and realistic entries
- Collapse verbose sections by default to make page feel lighter
- Update prize pool to $47,250
- Replace technical Bittensor hotkey section with accessible "How Miners Earn" explanation

## Functional Requirements

### FR-1: Clickable Mermaid Diagrams with Modal

Create a MermaidDiagramModal component and update MermaidDiagram to support click-to-expand:

```tsx
// ui/src/components/MermaidDiagramModal.tsx

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

  useEffect(() => {
    closeButtonRef.current?.focus();
  }, []);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        onClose();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  // Prevent body scroll when modal is open
  useEffect(() => {
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = '';
    };
  }, []);

  return (
    <div
      ref={modalRef}
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/90 backdrop-blur-sm animate-fade-in"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label={ariaLabel ?? 'Diagram full view'}
    >
      <button
        ref={closeButtonRef}
        onClick={onClose}
        className="absolute top-4 right-4 text-white/60 hover:text-white transition-colors z-10"
        aria-label="Close diagram"
      >
        <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
          <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>

      <div
        className="relative max-w-[90vw] max-h-[90vh] overflow-auto bg-[#0B0F14] rounded-2xl p-8 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
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
```

Update MermaidDiagram to be clickable:

```tsx
// ui/src/components/MermaidDiagram.tsx - Add onClick support

'use client';

import { useEffect, useId, useState } from 'react';
import mermaid from 'mermaid';
import { MermaidDiagramModal } from './MermaidDiagramModal';

// ... existing mermaid initialization ...

interface MermaidDiagramProps {
  chart: string;
  className?: string;
  ariaLabel?: string;
  clickable?: boolean; // NEW: Enable click-to-expand
}

export function MermaidDiagram({ chart, className, ariaLabel, clickable = true }: MermaidDiagramProps) {
  const id = useId();
  const [svg, setSvg] = useState('');
  const [hasError, setHasError] = useState(false);
  const [showModal, setShowModal] = useState(false);

  // ... existing render logic ...

  if (hasError) {
    return (
      <div className="mermaid-error">
        <svg className="w-5 h-5 text-[#EF4444]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
        <span>Diagram failed to render. Please refresh the page.</span>
      </div>
    );
  }

  const handleClick = () => {
    if (clickable) {
      setShowModal(true);
    }
  };

  return (
    <>
      <div
        className={`mermaid-container ${clickable ? 'mermaid-clickable' : ''} ${className || ''}`}
        role="img"
        aria-label={ariaLabel ?? 'Mermaid diagram'}
        onClick={handleClick}
        onKeyDown={(e) => {
          if (clickable && (e.key === 'Enter' || e.key === ' ')) {
            e.preventDefault();
            setShowModal(true);
          }
        }}
        tabIndex={clickable ? 0 : undefined}
        dangerouslySetInnerHTML={{ __html: svg }}
      />
      {showModal && (
        <MermaidDiagramModal
          svg={svg}
          ariaLabel={ariaLabel}
          onClose={() => setShowModal(false)}
        />
      )}
    </>
  );
}
```

Add CSS for clickable diagrams:

```css
/* ui/src/app/globals.css */

.mermaid-clickable {
  cursor: zoom-in;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.mermaid-clickable:hover {
  transform: scale(1.01);
  box-shadow: 0 0 20px rgba(99, 210, 151, 0.15);
}

.mermaid-clickable:focus-visible {
  outline: 2px solid rgba(99, 210, 151, 0.5);
  outline-offset: 4px;
  border-radius: 8px;
}

/* Modal diagram styling - larger text for readability */
.mermaid-modal-content svg {
  min-width: 600px;
  max-width: 100%;
  height: auto;
}

.mermaid-modal-content .nodeLabel {
  font-size: 14px !important;
}

.mermaid-modal-content .messageText {
  font-size: 13px !important;
}
```

### FR-2: Fix Sequence Diagram Model Reference

Update ArchitectureOverview.tsx to use DeepSeek V3.2:

```tsx
// ui/src/app/competition/components/ArchitectureOverview.tsx

const serviceSequenceDiagram = `sequenceDiagram
    participant Impl as Your Implementation
    participant Proxy as Web Proxy
    participant Search as Search API
    participant Sandbox as Code Sandbox
    participant Inference as Chutes Inference

    Impl->>Search: Search for "quantum entanglement"
    Search-->>Impl: Top 10 results
    Impl->>Proxy: Fetch https://physics.org/quantum
    Proxy-->>Impl: Page content
    Impl->>Inference: Call DeepSeek-V3.2 for synthesis
    Inference-->>Impl: Synthesized explanation
    Impl->>Sandbox: Execute Python visualization
    Sandbox-->>Impl: Generated image`;
```

### FR-3: Update Rodeo Rankings Leaderboard

Update Leaderboard.tsx with new entries:

```tsx
// ui/src/app/competition/components/Leaderboard.tsx

const leaderboardData: CompetitorRow[] = [
  {
    rank: 1,
    competitor: 'your-janus-implementation',
    miner: '5Your...Key',
    score: 82.7,
    quality: 86.3,
    speed: 78.4,
    cost: 84.2,
    streaming: 80.1,
    modality: 78.5,
    submitted: '2025-01-20',
    daysAtTop: 4,
    details: {
      suite: 'public/dev',
      ttft: '0.78s',
      p95: '3.8s',
      tokens: '1.1k avg',
      notes: 'Could this be your implementation taking the crown? Submit and find out.',
    },
  },
  {
    rank: 2,
    competitor: 'quantum-rider',
    miner: '5G9a...C21',
    score: 79.4,
    quality: 82.8,
    speed: 74.2,
    cost: 81.5,
    streaming: 76.8,
    modality: 77.3,
    submitted: '2025-01-18',
    daysAtTop: null,
    details: {
      suite: 'public/dev',
      ttft: '0.88s',
      p95: '4.2s',
      tokens: '1.0k avg',
      notes: 'Strong multimodal handling with efficient tool orchestration.',
    },
  },
  {
    rank: 3,
    competitor: 'baseline-n8n',
    miner: '5H2d...E9F',
    score: 76.2,
    quality: 79.5,
    speed: 71.8,
    cost: 78.9,
    streaming: 73.6,
    modality: 74.2,
    submitted: '2025-01-15',
    daysAtTop: null,
    details: {
      suite: 'public/dev',
      ttft: '0.98s',
      p95: '4.6s',
      tokens: '1.2k avg',
      notes: 'Workflow-based baseline using n8n orchestration.',
    },
  },
  {
    rank: 4,
    competitor: 'baseline-cli-agent',
    miner: '5J7b...A10',
    score: 74.8,
    quality: 77.6,
    speed: 70.2,
    cost: 76.5,
    streaming: 72.1,
    modality: 71.8,
    submitted: '2025-01-12',
    daysAtTop: null,
    details: {
      suite: 'public/dev',
      ttft: '1.04s',
      p95: '4.9s',
      tokens: '1.3k avg',
      notes: 'Reference CLI agent baseline with Aider integration.',
    },
  },
  {
    rank: 5,
    competitor: 'trailblazer',
    miner: '5K3e...D44',
    score: 72.5,
    quality: 75.2,
    speed: 68.4,
    cost: 74.8,
    streaming: 70.3,
    modality: 69.6,
    submitted: '2025-01-10',
    daysAtTop: null,
    details: {
      suite: 'public/dev',
      ttft: '1.12s',
      p95: '5.1s',
      tokens: '1.4k avg',
      notes: 'Consistent performance across all benchmark categories.',
    },
  },
];
```

### FR-4: Collapsible Leaderboard Columns Section

Update Leaderboard.tsx to make column definitions collapsible:

```tsx
// ui/src/app/competition/components/Leaderboard.tsx

export function Leaderboard() {
  // ... existing state ...
  const [columnsExpanded, setColumnsExpanded] = useState(false);

  // ... existing code ...

  return (
    <section id="leaderboard" className="py-16 lg:py-24">
      {/* ... existing leaderboard table ... */}

      {/* Collapsible column definitions */}
      <div className="glass-card mt-6 overflow-hidden">
        <button
          type="button"
          onClick={() => setColumnsExpanded(!columnsExpanded)}
          className="w-full p-6 flex items-center justify-between text-left hover:bg-white/5 transition-colors"
          aria-expanded={columnsExpanded}
          aria-controls="leaderboard-columns"
        >
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-[#9CA3AF]">
              Leaderboard columns
            </p>
            <p className="text-sm text-[#6B7280] mt-1">
              {columnsExpanded ? 'Click to collapse' : 'Click to see column definitions'}
            </p>
          </div>
          <svg
            className={`w-5 h-5 text-[#9CA3AF] transition-transform ${columnsExpanded ? 'rotate-180' : ''}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>
        {columnsExpanded && (
          <div id="leaderboard-columns" className="px-6 pb-6">
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4 text-sm">
              {columnDefinitions.map((column) => (
                <div key={column.label} className="space-y-1">
                  <p className="text-[#F3F4F6] font-semibold">{column.label}</p>
                  <p className="text-[#9CA3AF]">{column.description}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
```

### FR-5: Update Prize Pool Amount

Update prizePoolData.ts:

```typescript
// ui/src/app/competition/components/prizePoolData.ts

const poolAmountUsd = 47250;

export const prizePoolSnapshot = {
  amountUsd: poolAmountUsd,
  amountDisplay: currencyFormatter.format(poolAmountUsd),
  amountShort: shortCurrencyFormatter.format(poolAmountUsd),
  accumulatingSince: 'Jan 15, 2026',
  daysAtTop: 8,
  champion: 'your-janus-implementation',
  miner: '5Your...Key',
};
```

### FR-6: Collapsible Example Scenario

Update PrizePool.tsx:

```tsx
// ui/src/app/competition/components/PrizePool.tsx

export function PrizePool() {
  // ... existing state ...
  const [scenarioExpanded, setScenarioExpanded] = useState(false);

  return (
    <section id="prize-pool" className="py-16 lg:py-24 bg-[#0B111A]">
      {/* ... existing prize pool content ... */}

      {/* Collapsible Example Scenario */}
      <div className="glass-card overflow-hidden">
        <button
          type="button"
          onClick={() => setScenarioExpanded(!scenarioExpanded)}
          className="w-full p-6 flex items-center justify-between text-left hover:bg-white/5 transition-colors"
          aria-expanded={scenarioExpanded}
          aria-controls="example-scenario"
        >
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-[#9CA3AF]">
              Example scenario
            </p>
            <p className="text-sm text-[#6B7280] mt-1">
              {scenarioExpanded ? 'Click to collapse' : 'See how the prize pool grows and resets'}
            </p>
          </div>
          <svg
            className={`w-5 h-5 text-[#9CA3AF] transition-transform ${scenarioExpanded ? 'rotate-180' : ''}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>
        {scenarioExpanded && (
          <div id="example-scenario" className="px-6 pb-6 overflow-x-auto">
            <table className="w-full text-left border-separate border-spacing-y-2">
              {/* ... existing table content ... */}
            </table>
          </div>
        )}
      </div>
    </section>
  );
}
```

### FR-7: Replace Bittensor Hotkey Section with Accessible "How Contributors Earn"

Replace the technical hotkey section with a more accessible explanation:

```tsx
// ui/src/app/competition/components/SubmissionGuide.tsx

{/* Replace "Bittensor Hotkey Requirement" with this */}
<div className="glass-card p-6 space-y-4">
  <h3 className="text-xl font-semibold text-[#F3F4F6]">
    How Contributors Earn
  </h3>
  <p className="text-sm text-[#9CA3AF]">
    Janus runs on Bittensor, a decentralized network where contributors
    (called "miners") compete to provide the best AI services. Think of it
    like an open marketplace for intelligence - anyone can participate, and
    the best implementations earn rewards.
  </p>

  <div className="space-y-4">
    <div>
      <p className="text-sm text-[#F3F4F6] font-semibold">
        The Competition Model
      </p>
      <ul className="mt-2 space-y-2 text-sm text-[#D1D5DB] list-disc list-inside">
        <li>Submit your AI implementation to the Janus competition</li>
        <li>Your code runs benchmarks against other submissions</li>
        <li>Top performers earn from the prize pool</li>
        <li>All submissions are open source, fostering community learning</li>
      </ul>
    </div>

    <div>
      <p className="text-sm text-[#F3F4F6] font-semibold">
        Why Decentralized?
      </p>
      <ul className="mt-2 space-y-2 text-sm text-[#D1D5DB] list-disc list-inside">
        <li>
          <span className="text-[#63D297]">Open access:</span> Anyone can
          compete - no gatekeepers or approval processes
        </li>
        <li>
          <span className="text-[#63D297]">Transparent scoring:</span> All
          benchmarks and results are public
        </li>
        <li>
          <span className="text-[#63D297]">Fair rewards:</span> Earnings
          distributed automatically based on performance
        </li>
        <li>
          <span className="text-[#63D297]">Community-driven:</span> The best
          ideas rise to the top through open competition
        </li>
      </ul>
    </div>

    <div>
      <p className="text-sm text-[#F3F4F6] font-semibold">
        Getting Started
      </p>
      <p className="mt-2 text-sm text-[#D1D5DB]">
        To participate, you'll need a Bittensor wallet address (similar to a
        crypto wallet). This is used for:
      </p>
      <ul className="mt-2 space-y-2 text-sm text-[#D1D5DB] list-disc list-inside">
        <li>Attribution on the leaderboard</li>
        <li>Receiving prize pool payouts</li>
        <li>Building your reputation across submissions</li>
      </ul>
      <p className="mt-3 text-sm text-[#9CA3AF]">
        Don't have a wallet yet?{' '}
        <a
          href="https://docs.bittensor.com/getting-started/installation"
          target="_blank"
          rel="noopener noreferrer"
          className="text-[#63D297] hover:underline"
        >
          Get started with Bittensor
        </a>{' '}
        - it takes just a few minutes.
      </p>
    </div>
  </div>
</div>
```

### FR-8: Collapsible FAQ Sections

Update FAQ.tsx to use accordion-style collapsible sections:

```tsx
// ui/src/app/competition/components/FAQ.tsx

'use client';

import { useState, type ReactNode } from 'react';

// ... existing faqSections data ...

interface FAQItemProps {
  question: string;
  answer: ReactNode;
  defaultOpen?: boolean;
}

function FAQItem({ question, answer, defaultOpen = false }: FAQItemProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div className="glass-card overflow-hidden">
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full p-6 flex items-start justify-between text-left hover:bg-white/5 transition-colors"
        aria-expanded={isOpen}
      >
        <h4 className="text-lg font-semibold text-[#F3F4F6] pr-4">
          {question}
        </h4>
        <svg
          className={`w-5 h-5 text-[#9CA3AF] flex-shrink-0 transition-transform mt-1 ${isOpen ? 'rotate-180' : ''}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      {isOpen && (
        <div className="px-6 pb-6">
          <div className="text-sm text-[#9CA3AF] leading-relaxed space-y-3">
            {answer}
          </div>
        </div>
      )}
    </div>
  );
}

interface FAQSectionProps {
  title: string;
  items: { question: string; answer: ReactNode }[];
}

function FAQSection({ title, items }: FAQSectionProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div className="space-y-4">
      <button
        type="button"
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between text-left group"
        aria-expanded={isExpanded}
      >
        <h3 className="text-2xl font-semibold text-[#F3F4F6] group-hover:text-[#63D297] transition-colors">
          {title}
        </h3>
        <div className="flex items-center gap-2 text-sm text-[#9CA3AF]">
          <span>{items.length} questions</span>
          <svg
            className={`w-5 h-5 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </button>
      {isExpanded && (
        <div className="space-y-3">
          {items.map((item) => (
            <FAQItem key={item.question} question={item.question} answer={item.answer} />
          ))}
        </div>
      )}
    </div>
  );
}

export function FAQ() {
  return (
    <section id="faq" className="py-16 lg:py-24 bg-[#0B111A]">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 space-y-12">
        <div className="text-center">
          <p className="text-sm uppercase tracking-[0.3em] text-[#9CA3AF]">FAQ</p>
          <h2 className="text-3xl sm:text-4xl font-semibold text-[#F3F4F6] mt-3">
            Frequently Asked Questions
          </h2>
          <p className="text-[#9CA3AF] mt-4">
            Need a quick answer before you ship? Click a category to explore.
          </p>
        </div>

        <div className="space-y-8">
          {faqSections.map((section) => (
            <FAQSection
              key={section.title}
              title={section.title}
              items={section.items}
            />
          ))}
        </div>

        {/* Helpful links card stays expanded */}
        <div className="glass-card p-6 space-y-4">
          <h3 className="text-2xl font-semibold text-[#F3F4F6]">Helpful Links</h3>
          <ul className="space-y-3 text-sm text-[#D1D5DB]">
            {helpfulLinks.map((link) => (
              <li key={link.label}>
                <a href={link.href} className="text-[#63D297] hover:underline">
                  {link.label}
                </a>{' '}
                - {link.description}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}
```

## Testing Checklist

- [ ] Mermaid diagrams clickable - open full-size modal
- [ ] Modal closes on Escape key
- [ ] Modal closes on backdrop click
- [ ] Sequence diagram shows "DeepSeek-V3.2" not "gpt-4o-mini"
- [ ] Leaderboard shows your-janus-implementation at #1
- [ ] Leaderboard shows baseline-n8n at #3
- [ ] Leaderboard shows baseline-cli-agent at #4
- [ ] Leaderboard columns section collapsed by default
- [ ] Prize pool shows $47,250
- [ ] Example scenario collapsed by default
- [ ] "How Contributors Earn" section replaces hotkey section
- [ ] FAQ sections are collapsible
- [ ] Page feels visually lighter (less overwhelming)
- [ ] All collapsible sections expand/collapse smoothly
- [ ] Keyboard navigation works for all interactive elements

## Acceptance Criteria

- [ ] All Mermaid diagrams support click-to-expand
- [ ] Model reference corrected to DeepSeek-V3.2
- [ ] Leaderboard reflects correct baseline names
- [ ] Collapsible sections reduce visual clutter
- [ ] Prize pool updated to $47,250
- [ ] Bittensor terminology made accessible
- [ ] FAQ uses accordion pattern
- [ ] No accessibility regressions

## Files to Modify

```
ui/
├── src/
│   ├── app/
│   │   ├── globals.css                             # Add mermaid-clickable styles
│   │   └── competition/
│   │       └── components/
│   │           ├── ArchitectureOverview.tsx        # Fix model reference
│   │           ├── Leaderboard.tsx                 # Update entries, collapsible
│   │           ├── PrizePool.tsx                   # Collapsible scenario
│   │           ├── prizePoolData.ts                # Update amount
│   │           ├── SubmissionGuide.tsx             # Replace hotkey section
│   │           └── FAQ.tsx                         # Collapsible sections
│   └── components/
│       ├── MermaidDiagram.tsx                      # Add clickable support
│       ├── MermaidDiagramModal.tsx                 # NEW: Modal component
│       └── index.ts                                # Export modal
```

## Related Specs

- `specs/19_competition_page.md` - Original competition page design
- `specs/62_mermaid_diagram_styling.md` - Mermaid styling guidelines
- `specs/22_ui_polish.md` - UI polish standards
