'use client';

import { useMemo } from 'react';
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

  return (
    <div className="chat-debug-diagram">
      <MermaidDiagram
        chart={diagramDefinition}
        ariaLabel={`Debug flow diagram for ${baseline}`}
        clickable={false}
        className="chat-debug-mermaid"
      />
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
