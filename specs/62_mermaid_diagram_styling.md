# Spec 62: Mermaid Diagram Styling Enhancement

## Status: DRAFT

## Context / Why

The Mermaid diagrams throughout the app (especially in the competition section) have basic dark theme styling but don't fully align with the Chutes design system. The current implementation uses:

- Basic dark theme colors
- Minimal integration with glass morphism aesthetic
- No gradient effects or aurora styling
- Limited node/edge styling

The diagrams should feel native to the app's visual language, featuring:
- Glass morphism containers
- Aurora-inspired gradient accents
- Moss green (#63D297) highlights
- Consistent typography (Tomato Grotesk)
- Smooth, modern appearance

## Goals

- Align Mermaid diagram styling with Chutes design system
- Improve visual consistency across all diagram types (flowchart, sequence, etc.)
- Add aurora gradient accents and glass morphism effects
- Ensure diagrams are readable and professional
- Support both light text on dark backgrounds throughout

## Functional Requirements

### FR-1: Enhanced Mermaid Theme Configuration

Update the MermaidDiagram component with comprehensive theming:

```tsx
// ui/src/components/MermaidDiagram.tsx

'use client';

import { useEffect, useId, useState } from 'react';
import mermaid from 'mermaid';

let mermaidInitialized = false;

// Chutes Design System Colors
const CHUTES_COLORS = {
  // Base colors
  background: '#0B0F14',
  cardBackground: '#111726',
  surfaceBackground: '#142030',

  // Text colors
  primaryText: '#F3F4F6',
  secondaryText: '#9CA3AF',
  mutedText: '#6B7280',

  // Accent colors
  mossGreen: '#63D297',
  mossGreenDark: '#4BA87A',
  mossGreenLight: '#7FDAA8',

  // Aurora gradient stops
  auroraStart: '#63D297',
  auroraMid: '#4ECDC4',
  auroraEnd: '#45B7D1',

  // Semantic colors
  success: '#63D297',
  warning: '#F59E0B',
  error: '#EF4444',
  info: '#3B82F6',

  // Border colors
  border: 'rgba(55, 65, 81, 0.6)',
  borderLight: 'rgba(99, 210, 151, 0.3)',
};

interface MermaidDiagramProps {
  chart: string;
  className?: string;
  ariaLabel?: string;
}

export function MermaidDiagram({ chart, className, ariaLabel }: MermaidDiagramProps) {
  const id = useId();
  const [svg, setSvg] = useState('');
  const [hasError, setHasError] = useState(false);

  useEffect(() => {
    if (!mermaidInitialized) {
      mermaid.initialize({
        startOnLoad: false,
        theme: 'base',
        securityLevel: 'strict',

        // General settings
        fontFamily: 'Tomato Grotesk, Inter, system-ui, sans-serif',
        fontSize: 14,

        // Flowchart specific
        flowchart: {
          curve: 'basis',
          padding: 20,
          nodeSpacing: 50,
          rankSpacing: 60,
          htmlLabels: true,
          useMaxWidth: true,
        },

        // Sequence diagram specific
        sequence: {
          actorMargin: 50,
          boxMargin: 10,
          boxTextMargin: 5,
          noteMargin: 10,
          messageMargin: 35,
          mirrorActors: true,
          useMaxWidth: true,
        },

        // Theme variables aligned with Chutes design system
        themeVariables: {
          // Background colors
          background: CHUTES_COLORS.background,
          primaryColor: CHUTES_COLORS.cardBackground,
          secondaryColor: CHUTES_COLORS.surfaceBackground,
          tertiaryColor: CHUTES_COLORS.surfaceBackground,

          // Text colors
          primaryTextColor: CHUTES_COLORS.primaryText,
          secondaryTextColor: CHUTES_COLORS.secondaryText,
          tertiaryTextColor: CHUTES_COLORS.mutedText,

          // Line and border colors
          lineColor: CHUTES_COLORS.mossGreen,
          primaryBorderColor: CHUTES_COLORS.borderLight,
          secondaryBorderColor: CHUTES_COLORS.border,

          // Node styling
          nodeBkg: CHUTES_COLORS.cardBackground,
          nodeTextColor: CHUTES_COLORS.primaryText,
          nodeBorder: CHUTES_COLORS.mossGreen,

          // Main node (root/primary)
          mainBkg: CHUTES_COLORS.surfaceBackground,

          // Cluster/subgraph styling
          clusterBkg: 'rgba(17, 23, 38, 0.7)',
          clusterBorder: CHUTES_COLORS.borderLight,
          titleColor: CHUTES_COLORS.primaryText,

          // Edge labels
          edgeLabelBackground: CHUTES_COLORS.background,

          // Font settings
          fontFamily: 'Tomato Grotesk, Inter, system-ui, sans-serif',

          // Sequence diagram specific
          actorBkg: CHUTES_COLORS.cardBackground,
          actorBorder: CHUTES_COLORS.mossGreen,
          actorTextColor: CHUTES_COLORS.primaryText,
          actorLineColor: CHUTES_COLORS.mossGreen,
          signalColor: CHUTES_COLORS.mossGreen,
          signalTextColor: CHUTES_COLORS.primaryText,
          labelBoxBkgColor: CHUTES_COLORS.cardBackground,
          labelBoxBorderColor: CHUTES_COLORS.borderLight,
          labelTextColor: CHUTES_COLORS.primaryText,
          loopTextColor: CHUTES_COLORS.secondaryText,
          noteBkgColor: CHUTES_COLORS.surfaceBackground,
          noteBorderColor: CHUTES_COLORS.borderLight,
          noteTextColor: CHUTES_COLORS.primaryText,
          activationBkgColor: 'rgba(99, 210, 151, 0.15)',
          activationBorderColor: CHUTES_COLORS.mossGreen,

          // Pie chart
          pie1: CHUTES_COLORS.mossGreen,
          pie2: '#4ECDC4',
          pie3: '#45B7D1',
          pie4: '#5B8DEE',
          pie5: '#8B7DD8',
          pieStrokeColor: CHUTES_COLORS.border,
          pieStrokeWidth: '1px',
          pieTitleTextColor: CHUTES_COLORS.primaryText,
          pieSectionTextColor: CHUTES_COLORS.primaryText,
          pieLegendTextColor: CHUTES_COLORS.secondaryText,

          // Gantt chart
          sectionBkgColor: CHUTES_COLORS.cardBackground,
          altSectionBkgColor: CHUTES_COLORS.surfaceBackground,
          gridColor: CHUTES_COLORS.border,
          taskBkgColor: CHUTES_COLORS.mossGreen,
          taskTextColor: CHUTES_COLORS.background,
          taskTextOutsideColor: CHUTES_COLORS.primaryText,
          activeTaskBkgColor: CHUTES_COLORS.mossGreenLight,
          activeTaskBorderColor: CHUTES_COLORS.mossGreen,
          doneTaskBkgColor: CHUTES_COLORS.mossGreenDark,
          doneTaskBorderColor: CHUTES_COLORS.mossGreen,
          critBkgColor: CHUTES_COLORS.error,
          critBorderColor: '#DC2626',
          todayLineColor: CHUTES_COLORS.warning,

          // State diagram
          labelColor: CHUTES_COLORS.primaryText,
          altBackground: CHUTES_COLORS.surfaceBackground,

          // Class diagram
          classText: CHUTES_COLORS.primaryText,

          // Git graph
          git0: CHUTES_COLORS.mossGreen,
          git1: '#4ECDC4',
          git2: '#45B7D1',
          git3: '#5B8DEE',
          git4: '#8B7DD8',
          git5: '#C084FC',
          git6: '#F472B6',
          git7: '#FB7185',
          gitBranchLabel0: CHUTES_COLORS.primaryText,
          commitLabelColor: CHUTES_COLORS.primaryText,
          commitLabelBackground: CHUTES_COLORS.cardBackground,
        },
      });
      mermaidInitialized = true;
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    const render = async () => {
      try {
        const renderId = `mermaid-${id.replace(/:/g, '')}`;
        const { svg: svgMarkup } = await mermaid.render(renderId, chart);
        if (!cancelled) {
          setSvg(svgMarkup);
        }
      } catch {
        if (!cancelled) {
          setHasError(true);
        }
      }
    };

    render();

    return () => {
      cancelled = true;
    };
  }, [chart, id]);

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

  return (
    <div
      className={`mermaid-container ${className || ''}`}
      role="img"
      aria-label={ariaLabel ?? 'Mermaid diagram'}
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  );
}
```

### FR-2: CSS Styling for Mermaid Diagrams

Add comprehensive CSS for Mermaid diagram containers and SVG elements:

```css
/* ui/src/app/globals.css */

/* ─── Mermaid Diagram Styling ──────────────────────────────────────────────── */

.mermaid-container {
  width: 100%;
  overflow-x: auto;
  scrollbar-width: thin;
  scrollbar-color: rgba(99, 210, 151, 0.3) transparent;
}

.mermaid-container::-webkit-scrollbar {
  height: 6px;
}

.mermaid-container::-webkit-scrollbar-track {
  background: transparent;
}

.mermaid-container::-webkit-scrollbar-thumb {
  background: rgba(99, 210, 151, 0.3);
  border-radius: 3px;
}

.mermaid-container svg {
  max-width: 100%;
  height: auto;
  display: block;
  margin: 0 auto;
}

/* Flowchart node styling */
.mermaid-container .node rect,
.mermaid-container .node polygon,
.mermaid-container .node circle,
.mermaid-container .node ellipse {
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.3));
  transition: filter 0.2s ease;
}

.mermaid-container .node:hover rect,
.mermaid-container .node:hover polygon {
  filter: drop-shadow(0 4px 8px rgba(99, 210, 151, 0.2));
}

/* Subgraph/cluster styling - Glass morphism effect */
.mermaid-container .cluster rect {
  fill: rgba(17, 23, 38, 0.6) !important;
  stroke: rgba(99, 210, 151, 0.3) !important;
  stroke-width: 1px !important;
  rx: 12 !important;
  ry: 12 !important;
}

/* Cluster/subgraph labels */
.mermaid-container .cluster-label .nodeLabel {
  fill: #F3F4F6 !important;
  font-weight: 600;
  font-size: 13px;
}

/* Node labels */
.mermaid-container .nodeLabel {
  font-family: 'Tomato Grotesk', 'Inter', system-ui, sans-serif;
  font-size: 13px;
  fill: #F3F4F6 !important;
}

/* Edge/arrow styling */
.mermaid-container .edgePath .path {
  stroke: #63D297 !important;
  stroke-width: 1.5px !important;
}

.mermaid-container .edgePath marker path {
  fill: #63D297 !important;
  stroke: #63D297 !important;
}

/* Dashed edges (for blocked/inactive states) */
.mermaid-container .edgePath.dashed .path {
  stroke-dasharray: 5, 3 !important;
  stroke: #6B7280 !important;
}

/* Edge labels */
.mermaid-container .edgeLabel {
  background-color: #0B0F14 !important;
  padding: 2px 6px;
  border-radius: 4px;
}

.mermaid-container .edgeLabel .label {
  fill: #9CA3AF !important;
  font-size: 11px;
}

/* Sequence diagram styling */
.mermaid-container .actor {
  fill: #111726 !important;
  stroke: #63D297 !important;
  stroke-width: 1.5px !important;
  rx: 8 !important;
}

.mermaid-container .actor-line {
  stroke: rgba(99, 210, 151, 0.5) !important;
  stroke-dasharray: 4, 4 !important;
}

.mermaid-container text.actor > tspan {
  fill: #F3F4F6 !important;
  font-weight: 600;
}

/* Message lines */
.mermaid-container .messageLine0,
.mermaid-container .messageLine1 {
  stroke: #63D297 !important;
  stroke-width: 1.5px !important;
}

/* Message text */
.mermaid-container .messageText {
  fill: #D1D5DB !important;
  font-size: 12px;
}

/* Activation box */
.mermaid-container .activation0,
.mermaid-container .activation1,
.mermaid-container .activation2 {
  fill: rgba(99, 210, 151, 0.15) !important;
  stroke: #63D297 !important;
}

/* Notes in sequence diagrams */
.mermaid-container .note {
  fill: #142030 !important;
  stroke: rgba(99, 210, 151, 0.3) !important;
  rx: 6 !important;
}

.mermaid-container .noteText {
  fill: #D1D5DB !important;
  font-size: 11px;
}

/* Loop/Alt boxes */
.mermaid-container .loopLine {
  stroke: rgba(99, 210, 151, 0.4) !important;
  stroke-dasharray: 3, 3 !important;
}

.mermaid-container .loopText,
.mermaid-container .loopText > tspan {
  fill: #9CA3AF !important;
  font-size: 11px;
}

.mermaid-container .labelBox {
  fill: #111726 !important;
  stroke: rgba(99, 210, 151, 0.3) !important;
}

.mermaid-container .labelText {
  fill: #63D297 !important;
  font-weight: 600;
}

/* Mermaid error state */
.mermaid-error {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 8px;
  color: #FCA5A5;
  font-size: 13px;
}

/* ─── Mermaid in Glass Cards ───────────────────────────────────────────────── */

.glass-card .mermaid-container,
.glass .mermaid-container {
  padding: 8px;
}

/* ─── Mermaid Diagram Wrapper with Aurora Glow ─────────────────────────────── */

.mermaid-glow {
  position: relative;
  padding: 1px;
  border-radius: 16px;
  background: linear-gradient(
    135deg,
    rgba(99, 210, 151, 0.2) 0%,
    rgba(78, 205, 196, 0.15) 50%,
    rgba(69, 183, 209, 0.1) 100%
  );
}

.mermaid-glow::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: 16px;
  background: linear-gradient(
    135deg,
    rgba(99, 210, 151, 0.1) 0%,
    transparent 50%
  );
  filter: blur(20px);
  opacity: 0.5;
  z-index: -1;
}

.mermaid-glow > .mermaid-container {
  background: rgba(11, 15, 20, 0.9);
  border-radius: 15px;
  padding: 20px;
}

/* ─── Responsive Mermaid ───────────────────────────────────────────────────── */

@media (max-width: 768px) {
  .mermaid-container svg {
    min-width: 500px;
  }

  .mermaid-container .nodeLabel {
    font-size: 11px;
  }

  .mermaid-container .messageText {
    font-size: 10px;
  }
}

/* ─── Dark Mode Print Styles ───────────────────────────────────────────────── */

@media print {
  .mermaid-container {
    background: white;
  }

  .mermaid-container .nodeLabel,
  .mermaid-container text {
    fill: #1F2937 !important;
  }

  .mermaid-container .edgePath .path {
    stroke: #374151 !important;
  }

  .mermaid-container .cluster rect {
    fill: #F3F4F6 !important;
    stroke: #D1D5DB !important;
  }
}
```

### FR-3: MermaidDiagramGlow Wrapper Component

Create an optional wrapper for diagrams that need extra emphasis:

```tsx
// ui/src/components/MermaidDiagramGlow.tsx

'use client';

import { MermaidDiagram } from './MermaidDiagram';

interface MermaidDiagramGlowProps {
  chart: string;
  ariaLabel?: string;
  className?: string;
}

export function MermaidDiagramGlow({ chart, ariaLabel, className }: MermaidDiagramGlowProps) {
  return (
    <div className={`mermaid-glow ${className || ''}`}>
      <MermaidDiagram chart={chart} ariaLabel={ariaLabel} />
    </div>
  );
}
```

### FR-4: Update Usage in Competition Pages

Update ArchitectureOverview and other competition components to use enhanced styling:

```tsx
// Example update in ui/src/app/competition/components/ArchitectureOverview.tsx

// For important diagrams, use the glow wrapper:
<MermaidDiagramGlow
  chart={architectureDiagram}
  ariaLabel="Janus architecture diagram"
/>

// For inline diagrams in glass cards:
<div className="glass p-4 rounded-2xl overflow-x-auto">
  <MermaidDiagram
    chart={serviceSequenceDiagram}
    ariaLabel="Platform services sequence diagram"
  />
</div>
```

### FR-5: Consistent Diagram Node Shapes

Define consistent node shape conventions across all diagrams:

| Element Type | Shape | Color |
|--------------|-------|-------|
| User-facing components | Rounded rectangle | `#111726` with `#63D297` border |
| Internal services | Rectangle | `#142030` with subtle border |
| External services | Stadium shape | `#111726` with dashed border |
| Data stores | Cylinder | `#142030` |
| Blocked/inactive | Any shape | Grayed out (`#6B7280`) |

## Testing Checklist

- [ ] Mermaid diagrams render with dark theme
- [ ] Node colors match Chutes design system
- [ ] Edge/arrow colors are moss green (#63D297)
- [ ] Subgraph containers have glass morphism effect
- [ ] Text is readable (light on dark)
- [ ] Hover states have subtle glow effect
- [ ] Sequence diagrams have consistent actor styling
- [ ] Diagrams are horizontally scrollable on mobile
- [ ] MermaidDiagramGlow wrapper adds aurora gradient
- [ ] Error state displays gracefully
- [ ] Competition page diagrams look professional
- [ ] Chat UI diagram rendering (if any) is consistent
- [ ] Print styles work correctly (dark → light)

## Acceptance Criteria

- [ ] All Mermaid diagrams align with Chutes design system
- [ ] Glass morphism effect on subgraphs/clusters
- [ ] Aurora-inspired gradient accents available
- [ ] Consistent typography (Tomato Grotesk)
- [ ] Moss green (#63D297) used for connections/highlights
- [ ] Diagrams are responsive and scrollable
- [ ] Error states handled gracefully
- [ ] Visual consistency across flowchart, sequence, and other diagram types

## Files to Modify

```
ui/
├── src/
│   ├── app/
│   │   └── globals.css                    # Add mermaid CSS
│   └── components/
│       ├── MermaidDiagram.tsx             # Enhanced theme config
│       ├── MermaidDiagramGlow.tsx         # NEW: Glow wrapper
│       └── index.ts                       # Export new component
```

## Related Specs

- `specs/22_ui_polish.md` - UI styling guidelines
- `specs/18_landing_page.md` - Design system reference
- `specs/19_competition_page.md` - Competition page components
