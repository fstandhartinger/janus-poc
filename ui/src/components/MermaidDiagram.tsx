'use client';

import { useCallback, useEffect, useId, useState } from 'react';
import mermaid from 'mermaid';
import { MermaidDiagramModal } from './MermaidDiagramModal';

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
  clickable?: boolean;
}

export function MermaidDiagram({
  chart,
  className,
  ariaLabel,
  clickable = true,
}: MermaidDiagramProps) {
  const id = useId();
  const [svg, setSvg] = useState('');
  const [hasError, setHasError] = useState(false);
  const [showModal, setShowModal] = useState(false);

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
          padding: 30,
          nodeSpacing: 60,
          rankSpacing: 70,
          htmlLabels: true,
          useMaxWidth: false,
          wrappingWidth: 200,
        },

        // Sequence diagram specific
        sequence: {
          actorMargin: 60,
          boxMargin: 15,
          boxTextMargin: 8,
          noteMargin: 15,
          messageMargin: 45,
          mirrorActors: true,
          useMaxWidth: false,
          wrap: true,
          wrapPadding: 10,
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
      setHasError(false);
      if (!chart.trim()) {
        setSvg('');
        return;
      }
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

  // Stable callbacks to prevent infinite render loops
  const handleClick = useCallback(() => {
    if (clickable) {
      setShowModal(true);
    }
  }, [clickable]);

  const handleModalClose = useCallback(() => {
    setShowModal(false);
  }, []);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (clickable && (e.key === 'Enter' || e.key === ' ')) {
      e.preventDefault();
      setShowModal(true);
    }
  }, [clickable]);

  return (
    <>
      <div className={`mermaid-wrapper ${className || ''}`}>
        <div
          className={`mermaid-container ${clickable ? 'mermaid-clickable' : ''}`}
          role="img"
          aria-label={ariaLabel ?? 'Mermaid diagram'}
          onClick={handleClick}
          onKeyDown={handleKeyDown}
          tabIndex={clickable ? 0 : undefined}
          dangerouslySetInnerHTML={{ __html: svg }}
        />
      </div>
      {showModal && (
        <MermaidDiagramModal
          svg={svg}
          ariaLabel={ariaLabel}
          onClose={handleModalClose}
        />
      )}
    </>
  );
}
