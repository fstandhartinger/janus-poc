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
};

const FILE_EVENT_TYPES = new Set(['file_created', 'file_modified', 'artifact_generated']);

export function useDebug(enabled: boolean, requestId: string | null, baseline: string) {
  const [debugState, setDebugState] = useState<DebugState>(INITIAL_STATE);
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!enabled) {
      setDebugState(INITIAL_STATE);
    }
  }, [enabled]);

  useEffect(() => {
    if (!enabled || !requestId) return;

    setDebugState(INITIAL_STATE);

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
  if (!event.step) return previous;
  if (event.step === 'SSE') {
    return uniqueList([...previous, 'SSE']);
  }
  const mapped = PATH_MAP[event.step];
  if (mapped) return mapped;
  return [event.step];
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
