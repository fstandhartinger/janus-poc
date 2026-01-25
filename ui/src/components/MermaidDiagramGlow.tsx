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
