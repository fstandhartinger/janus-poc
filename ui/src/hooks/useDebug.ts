'use client';

import { useEffect, useRef, useState } from 'react';
import type { DebugEvent, DebugState } from '@/types/debug';

const INITIAL_STATE: DebugState = {
  currentStep: '',
  activeNodes: [],
  events: [],
  files: [],
};

const PATH_MAP: Record<string, string[]> = {
  REQ: ['REQ'],
  ROUTING: ['REQ', 'ROUTING'],
  FAST_LLM: ['REQ', 'ROUTING', 'FAST_LLM'],
  SANDY: ['REQ', 'ROUTING', 'SANDY'],
  AGENT: ['REQ', 'ROUTING', 'SANDY', 'AGENT'],
  TOOLS: ['REQ', 'ROUTING', 'SANDY', 'AGENT', 'TOOLS'],
  SSE: ['REQ', 'SSE'],
  // Legacy mappings for backward compatibility
  DETECT: ['REQ', 'ROUTING'],
  KEYWORDS: ['REQ', 'ROUTING'],
  LLM_VERIFY: ['REQ', 'ROUTING'],
  TOOL_IMG: ['REQ', 'ROUTING', 'SANDY', 'AGENT', 'TOOLS'],
  TOOL_CODE: ['REQ', 'ROUTING', 'SANDY', 'AGENT', 'TOOLS'],
  TOOL_SEARCH: ['REQ', 'ROUTING', 'SANDY', 'AGENT', 'TOOLS'],
  TOOL_FILES: ['REQ', 'ROUTING', 'SANDY', 'AGENT', 'TOOLS'],
};

const FILE_EVENT_TYPES = new Set(['file_created', 'file_modified', 'artifact_generated']);

const EVENT_TO_NODES: Record<string, string[]> = {
  // Request phase
  request_received: ['REQ'],

  // Routing phase
  complexity_check_start: ['ROUTING'],
  complexity_check_keyword: ['ROUTING'],
  complexity_check_llm: ['ROUTING'],
  complexity_check_complete: ['ROUTING'],
  routing_decision: ['ROUTING'],

  // Fast path
  fast_path_start: ['FAST_LLM'],
  fast_path_llm_call: ['FAST_LLM'],
  fast_path_stream: ['FAST_LLM', 'SSE'],
  fast_path_complete: ['SSE'],

  // Agent path
  agent_path_start: ['SANDY'],
  agent_selection: ['SANDY'],
  model_selection: ['SANDY'],
  sandbox_init: ['SANDY'],
  sandy_sandbox_create: ['SANDY'],
  sandy_sandbox_created: ['SANDY'],
  sandy_agent_api_request: ['AGENT'],
  sandy_agent_api_sse_event: ['AGENT'],
  sandy_agent_api_complete: ['AGENT'],

  // Tool calls
  tool_call_start: ['TOOLS'],
  tool_call_result: ['TOOLS'],
  tool_call_complete: ['TOOLS'],

  // Response
  response_chunk: ['SSE'],
  response_complete: ['SSE'],
  error: ['SSE'],
};

export function useDebug(enabled: boolean, requestId: string | null, baseline: string) {
  const [debugState, setDebugState] = useState<DebugState>(INITIAL_STATE);
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!enabled) {
      // Schedule state update outside effect render cycle
      queueMicrotask(() => {
        setDebugState(INITIAL_STATE);
      });
    }
  }, [enabled]);

  useEffect(() => {
    if (!enabled || !requestId) return;

    // Schedule state update outside effect render cycle
    queueMicrotask(() => {
      setDebugState(INITIAL_STATE);
    });

    const params = new URLSearchParams();
    if (baseline) {
      params.set('baseline', baseline);
    }
    const url = `/api/debug/stream/${requestId}${params.toString() ? `?${params.toString()}` : ''}`;
    const eventSource = new EventSource(url);
    eventSourceRef.current = eventSource;

    const handleEvent = (event: MessageEvent) => {
      const debugEvent = parseDebugEvent(event.data);
      if (!debugEvent) return;

      setDebugState((prev) => {
        const nextFiles = updateFiles(prev.files, debugEvent);
        const activeNodes = computeActiveNodes(debugEvent, prev.activeNodes);
        return {
          currentStep: debugEvent.step,
          activeNodes,
          events: [...prev.events, debugEvent],
          files: nextFiles,
          correlationId: prev.correlationId || debugEvent.correlation_id,
        };
      });
    };

    eventSource.onmessage = handleEvent;
    eventSource.addEventListener('debug', handleEvent as EventListener);
    eventSource.onerror = () => {
      eventSource.close();
    };

    return () => {
      eventSource.close();
      eventSourceRef.current = null;
    };
  }, [enabled, requestId, baseline]);

  return debugState;
}

export function computeActiveNodes(event: DebugEvent, previous: string[]): string[] {
  const eventNodes = EVENT_TO_NODES[event.type] ?? [];
  let nextNodes = eventNodes.length ? uniqueList([...previous, ...eventNodes]) : previous;
  if (!event.step) return nextNodes;
  if (event.step === 'SSE') {
    return uniqueList([...nextNodes, 'SSE']);
  }
  const mapped = PATH_MAP[event.step];
  if (mapped) return uniqueList([...nextNodes, ...mapped]);
  return uniqueList([...nextNodes, event.step]);
}

function updateFiles(files: string[], event: DebugEvent): string[] {
  if (!FILE_EVENT_TYPES.has(event.type)) return files;
  const filename =
    typeof event.data?.filename === 'string'
      ? event.data.filename
      : typeof event.data?.file === 'string'
      ? event.data.file
      : '';
  if (!filename) return files;
  return uniqueList([...files, filename]);
}

function uniqueList(items: string[]): string[] {
  return Array.from(new Set(items));
}

function parseDebugEvent(raw: string): DebugEvent | null {
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as DebugEvent;
    if (!parsed || typeof parsed !== 'object') return null;
    if (!parsed.timestamp || !parsed.type) return null;
    return parsed;
  } catch {
    return null;
  }
}
