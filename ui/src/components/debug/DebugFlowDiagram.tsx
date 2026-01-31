'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { MermaidDiagram } from '@/components/MermaidDiagram';

const ALL_NODES = [
  'REQ',
  'ROUTING',
  'FAST_LLM',
  'SANDY',
  'AGENT',
  'TOOLS',
  'SSE',
];

interface DebugFlowDiagramProps {
  baseline: string;
  currentStep: string;
  highlightedNodes: string[];
}

export function DebugFlowDiagram({ baseline, currentStep, highlightedNodes }: DebugFlowDiagramProps) {
  const diagramDefinition = useMemo(() => {
    return generateDiagram(baseline, currentStep, highlightedNodes);
  }, [baseline, currentStep, highlightedNodes]);
  const containerRef = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(1);

  const updateScale = useCallback(() => {
    const container = containerRef.current;
    if (!container) return;
    const svgElement = container.querySelector('svg');
    if (!svgElement) return;

    const styles = window.getComputedStyle(container);
    const paddingX = parseFloat(styles.paddingLeft) + parseFloat(styles.paddingRight);
    const paddingY = parseFloat(styles.paddingTop) + parseFloat(styles.paddingBottom);

    const containerWidth = container.clientWidth - paddingX;
    const containerHeight = container.clientHeight - paddingY;
    if (containerWidth <= 0 || containerHeight <= 0) return;

    const viewBox = svgElement.viewBox?.baseVal;
    const svgWidth = viewBox?.width || svgElement.getBoundingClientRect().width;
    const svgHeight = viewBox?.height || svgElement.getBoundingClientRect().height;
    if (!svgWidth || !svgHeight) return;

    const scaleX = containerWidth / svgWidth;
    const scaleY = containerHeight / svgHeight;
    const nextScale = Math.min(scaleX, scaleY, 1);
    setScale((prev) => (Math.abs(prev - nextScale) > 0.01 ? nextScale : prev));
  }, []);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const raf = requestAnimationFrame(updateScale);
    const mutationObserver = new MutationObserver(() => {
      requestAnimationFrame(updateScale);
    });
    mutationObserver.observe(container, { childList: true, subtree: true });

    let resizeObserver: ResizeObserver | null = null;
    if (typeof ResizeObserver !== 'undefined') {
      resizeObserver = new ResizeObserver(() => {
        requestAnimationFrame(updateScale);
      });
      resizeObserver.observe(container);
    }

    return () => {
      cancelAnimationFrame(raf);
      mutationObserver.disconnect();
      resizeObserver?.disconnect();
    };
  }, [diagramDefinition, updateScale]);

  return (
    <div className="chat-debug-diagram" ref={containerRef}>
      <div
        className="chat-debug-diagram-scale"
        style={{ transform: `scale(${scale})`, transformOrigin: 'center center' }}
      >
        <MermaidDiagram
          chart={diagramDefinition}
          ariaLabel={`Debug flow diagram for ${baseline}`}
          clickable={false}
          className="chat-debug-mermaid"
        />
      </div>
    </div>
  );
}

function generateDiagram(
  baseline: string,
  currentStep: string,
  activeNodes: string[],
): string {
  const agentLabel = baseline.includes('langchain') ? 'LangChain Agent' : 'CLI Agent';
  const sandboxLabel = baseline.includes('langchain') ? 'Agent Runtime' : 'Sandy Sandbox';

  // Map old node names to new simplified names for backward compatibility
  const nodeMap: Record<string, string> = {
    'DETECT': 'ROUTING',
    'KEYWORDS': 'ROUTING',
    'LLM_VERIFY': 'ROUTING',
    'TOOL_IMG': 'TOOLS',
    'TOOL_CODE': 'TOOLS',
    'TOOL_SEARCH': 'TOOLS',
    'TOOL_FILES': 'TOOLS',
  };

  const mappedNodes = activeNodes.map(node => nodeMap[node] || node);
  const activeList = mappedNodes.length ? mappedNodes : currentStep ? [nodeMap[currentStep] || currentStep] : [];
  const uniqueActiveNodes = [...new Set(activeList)];
  const activeLines = uniqueActiveNodes.map((node) => `class ${node} active`).join('\n');
  const inactiveLine = `class ${ALL_NODES.join(',')} inactive`;

  return `
flowchart TB
  classDef active fill:#63D297,stroke:#63D297,color:#0B0F14,stroke-width:2px
  classDef inactive fill:#111827,stroke:#334155,color:#E5E7EB

  REQ["📥 Request"]
  ROUTING["🔀 Complexity Router"]
  FAST_LLM["⚡ Direct LLM"]
  SANDY["📦 ${sandboxLabel}"]
  AGENT["🤖 ${agentLabel}"]
  TOOLS["🔧 Tools"]
  SSE["📤 SSE Response"]

  REQ --> ROUTING
  ROUTING -->|Simple| FAST_LLM
  ROUTING -->|Complex| SANDY
  SANDY --> AGENT
  AGENT --> TOOLS
  TOOLS --> AGENT
  FAST_LLM --> SSE
  AGENT --> SSE

  ${inactiveLine}
  ${activeLines}
  `;
}
