'use client';

import { useEffect, useRef, useState } from 'react';
import mermaid from 'mermaid';

let mermaidInitialized = false;

interface DiagramBlockProps {
  code: string;
}

export function DiagramBlock({ code }: DiagramBlockProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [svg, setSvg] = useState('');

  useEffect(() => {
    if (!mermaidInitialized) {
      mermaid.initialize({
        startOnLoad: false,
        theme: 'dark',
        securityLevel: 'strict',
        themeVariables: {
          primaryColor: '#63D297',
          primaryTextColor: '#F3F4F6',
          primaryBorderColor: '#1F2937',
          lineColor: '#6B7280',
          secondaryColor: '#1F2937',
          tertiaryColor: '#111827',
          fontFamily: 'Tomato Grotesk, Inter, system-ui, sans-serif',
        },
        flowchart: {
          htmlLabels: true,
          curve: 'basis',
        },
      });
      mermaidInitialized = true;
    }
  }, []);

  useEffect(() => {
    const renderDiagram = async () => {
      try {
        setError(null);
        const id = `mermaid-${Math.random().toString(36).slice(2)}`;
        const { svg: renderedSvg } = await mermaid.render(id, code);
        setSvg(renderedSvg);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to render diagram');
      }
    };

    renderDiagram();
  }, [code]);

  const downloadSVG = () => {
    if (!svg) return;
    const blob = new Blob([svg], { type: 'image/svg+xml' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = 'diagram.svg';
    anchor.click();
    URL.revokeObjectURL(url);
  };

  if (error) {
    return (
      <div className="diagram-error">
        <span>Diagram Error: {error}</span>
        <pre className="diagram-source">{code}</pre>
      </div>
    );
  }

  return (
    <div className="diagram-block" role="img" aria-label="Mermaid diagram">
      <div className="diagram-toolbar">
        <button type="button" onClick={downloadSVG} title="Download SVG">
          <DownloadIcon /> SVG
        </button>
      </div>
      <div
        ref={containerRef}
        className="diagram-content"
        dangerouslySetInnerHTML={{ __html: svg }}
      />
    </div>
  );
}

function DownloadIcon() {
  return (
    <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="7 10 12 15 17 10" />
      <line x1="12" y1="15" x2="12" y2="3" />
    </svg>
  );
}
