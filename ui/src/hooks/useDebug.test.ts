import { describe, expect, it } from 'vitest';
import { computeActiveNodes } from './useDebug';
import type { DebugEvent } from '@/types/debug';

const baseEvent = (step: string): DebugEvent => ({
  request_id: 'req-1',
  timestamp: new Date().toISOString(),
  type: 'request_received',
  step,
  message: 'ok',
});

describe('computeActiveNodes', () => {
  it('maps known steps to the full path', () => {
    expect(computeActiveNodes(baseEvent('REQ'), [])).toEqual(['REQ']);
    // New simplified flow: REQ -> ROUTING -> FAST_LLM
    expect(computeActiveNodes(baseEvent('FAST_LLM'), [])).toEqual([
      'REQ',
      'ROUTING',
      'FAST_LLM',
    ]);
  });

  it('maps agent path steps correctly', () => {
    expect(computeActiveNodes(baseEvent('SANDY'), [])).toEqual([
      'REQ',
      'ROUTING',
      'SANDY',
    ]);
    expect(computeActiveNodes(baseEvent('AGENT'), [])).toEqual([
      'REQ',
      'ROUTING',
      'SANDY',
      'AGENT',
    ]);
    expect(computeActiveNodes(baseEvent('TOOLS'), [])).toEqual([
      'REQ',
      'ROUTING',
      'SANDY',
      'AGENT',
      'TOOLS',
    ]);
  });

  it('keeps previous nodes for SSE step', () => {
    expect(computeActiveNodes(baseEvent('SSE'), ['REQ', 'ROUTING'])).toEqual([
      'REQ',
      'ROUTING',
      'SSE',
    ]);
  });

  it('falls back to step when unknown', () => {
    expect(computeActiveNodes(baseEvent('CUSTOM'), [])).toEqual(['REQ', 'CUSTOM']);
  });

  it('retains previous when step is empty', () => {
    expect(computeActiveNodes(baseEvent(''), ['REQ'])).toEqual(['REQ']);
  });

  it('handles legacy node names via PATH_MAP', () => {
    // Legacy nodes like DETECT should map to ROUTING
    expect(computeActiveNodes(baseEvent('DETECT'), [])).toEqual([
      'REQ',
      'ROUTING',
    ]);
    expect(computeActiveNodes(baseEvent('KEYWORDS'), [])).toEqual([
      'REQ',
      'ROUTING',
    ]);
  });
});
