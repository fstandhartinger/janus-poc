'use client';

import { useEffect, useId, useState } from 'react';
import mermaid from 'mermaid';

let mermaidInitialized = false;

interface MermaidDiagramProps {
  chart: string;
  className?: string;
}

export function MermaidDiagram({ chart, className }: MermaidDiagramProps) {
  const id = useId();
  const [svg, setSvg] = useState('');
  const [hasError, setHasError] = useState(false);

  useEffect(() => {
    if (!mermaidInitialized) {
      mermaid.initialize({
        startOnLoad: false,
        theme: 'dark',
        securityLevel: 'strict',
        flowchart: { curve: 'basis' },
        themeVariables: {
          fontFamily: 'Tomato Grotesk, Inter, system-ui, sans-serif',
          primaryColor: '#111726',
          primaryTextColor: '#F3F4F6',
          lineColor: '#63D297',
          edgeLabelBackground: '#0B0F14',
          tertiaryColor: '#142030',
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
      <div className="text-sm text-[#9CA3AF]">
        Architecture diagram failed to load. Please refresh the page.
      </div>
    );
  }

  return (
    <div
      className={className}
      role="img"
      aria-label="Competition architecture diagram"
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  );
}
