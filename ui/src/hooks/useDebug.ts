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
  DETECT: ['REQ', 'DETECT'],
  KEYWORDS: ['REQ', 'DETECT', 'KEYWORDS'],
  LLM_VERIFY: ['REQ', 'DETECT', 'KEYWORDS', 'LLM_VERIFY'],
  FAST_LLM: ['REQ', 'DETECT', 'KEYWORDS', 'LLM_VERIFY', 'FAST_LLM'],
  SANDY: ['REQ', 'DETECT', 'KEYWORDS', 'SANDY'],
  AGENT: ['REQ', 'DETECT', 'KEYWORDS', 'SANDY', 'AGENT'],
  TOOL_IMG: ['REQ', 'DETECT', 'KEYWORDS', 'SANDY', 'AGENT', 'TOOL_IMG'],
  TOOL_CODE: ['REQ', 'DETECT', 'KEYWORDS', 'SANDY', 'AGENT', 'TOOL_CODE'],
  TOOL_SEARCH: ['REQ', 'DETECT', 'KEYWORDS', 'SANDY', 'AGENT', 'TOOL_SEARCH'],
  TOOL_FILES: ['REQ', 'DETECT', 'KEYWORDS', 'SANDY', 'AGENT', 'TOOL_FILES'],
  SSE: ['REQ', 'DETECT', 'KEYWORDS', 'SSE'],
};

const FILE_EVENT_TYPES = new Set(['file_created', 'file_modified', 'artifact_generated']);

const EVENT_TO_NODES: Record<string, string[]> = {
  request_received: ['REQ'],
  complexity_check_start: ['DETECT'],
  complexity_check_keyword: ['KEYWORDS'],
  complexity_check_llm: ['LLM_VERIFY'],
  complexity_check_complete: ['DETECT'],
  routing_decision: ['DETECT'],
  fast_path_start: ['FAST_LLM'],
  fast_path_llm_call: ['FAST_LLM'],
  fast_path_stream: ['SSE'],
  fast_path_complete: ['SSE'],
  agent_path_start: ['SANDY'],
  agent_selection: ['SANDY'],
  model_selection: ['SANDY'],
  sandbox_init: ['SANDY'],
  sandy_sandbox_create: ['SANDY'],
  sandy_sandbox_created: ['SANDY'],
  sandy_agent_api_request: ['AGENT'],
  sandy_agent_api_sse_event: ['AGENT'],
  sandy_agent_api_complete: ['AGENT'],
  tool_call_start: ['AGENT'],
  tool_call_result: ['AGENT'],
  tool_call_complete: ['AGENT'],
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
