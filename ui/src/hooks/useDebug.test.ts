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
    expect(computeActiveNodes(baseEvent('FAST_LLM'), [])).toEqual([
      'REQ',
      'DETECT',
      'KEYWORDS',
      'LLM_VERIFY',
      'FAST_LLM',
    ]);
  });

  it('keeps previous nodes for SSE step', () => {
    expect(computeActiveNodes(baseEvent('SSE'), ['REQ', 'DETECT'])).toEqual([
      'REQ',
      'DETECT',
      'SSE',
    ]);
  });

  it('falls back to step when unknown', () => {
    expect(computeActiveNodes(baseEvent('CUSTOM'), [])).toEqual(['CUSTOM']);
  });

  it('retains previous when step is empty', () => {
    expect(computeActiveNodes(baseEvent(''), ['REQ'])).toEqual(['REQ']);
  });
});
