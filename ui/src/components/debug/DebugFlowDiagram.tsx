'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { MermaidDiagram } from '@/components/MermaidDiagram';

const ALL_NODES = [
  'REQ',
  'DETECT',
  'KEYWORDS',
  'LLM_VERIFY',
  'FAST_LLM',
  'SANDY',
  'AGENT',
  'TOOL_IMG',
  'TOOL_CODE',
  'TOOL_SEARCH',
  'TOOL_FILES',
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
      <div className="chat-debug-diagram-scale" style={{ transform: `scale(${scale})` }}>
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
  const activeList = activeNodes.length ? activeNodes : currentStep ? [currentStep] : [];
  const activeLines = activeList.map((node) => `class ${node} active`).join('\n');
  const inactiveLine = `class ${ALL_NODES.join(',')} inactive`;

  return `
    flowchart TB
      classDef active fill:#63D297,stroke:#63D297,color:#0B0F14
      classDef inactive fill:#111827,stroke:#334155,color:#E5E7EB
      classDef pending fill:#111827,stroke:#475569,stroke-dasharray: 5 5,color:#9CA3AF

      subgraph Request ["Incoming Request"]
          REQ["POST /v1/chat/completions"]
      end

      subgraph Routing ["Complexity Detection"]
          DETECT["Complexity Detector"]
          KEYWORDS["Keyword Check"]
          LLM_VERIFY["LLM Verification"]
      end

      subgraph FastPath ["Fast Path"]
          FAST_LLM["Direct LLM Call"]
      end

      subgraph AgentPath ["Agent Path"]
          SANDY["${sandboxLabel}"]
          AGENT["${agentLabel}"]
      end

      subgraph Tools ["Agent Tools"]
          TOOL_IMG["Image Gen"]
          TOOL_CODE["Code Exec"]
          TOOL_SEARCH["Web Search"]
          TOOL_FILES["File Ops"]
      end

      subgraph Response ["Response"]
          SSE["SSE Stream"]
      end

      REQ --> DETECT
      DETECT --> KEYWORDS
      KEYWORDS -->|"Complex"| SANDY
      KEYWORDS -->|"Simple"| LLM_VERIFY
      LLM_VERIFY --> FAST_LLM
      LLM_VERIFY --> SANDY
      SANDY --> AGENT
      AGENT --> TOOL_IMG & TOOL_CODE & TOOL_SEARCH & TOOL_FILES
      FAST_LLM --> SSE
      AGENT --> SSE

      ${inactiveLine}
      ${activeLines}
  `;
}
