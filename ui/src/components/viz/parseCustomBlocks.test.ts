import { describe, expect, it } from 'vitest';
import { parseCustomBlocks } from './parseCustomBlocks';

describe('parseCustomBlocks', () => {
  it('splits markdown and custom blocks', () => {
    const content = 'Intro\n:::chart\n{"type":"bar"}\n:::\nOutro';
    const blocks = parseCustomBlocks(content);

    expect(blocks).toEqual([
      { type: 'markdown', content: 'Intro\n' },
      { type: 'chart', content: '{"type":"bar"}' },
      { type: 'markdown', content: '\nOutro' },
    ]);
  });

  it('handles multiple blocks with windows newlines', () => {
    const content =
      'Start\r\n:::diagram\r\nflowchart TD\r\n:::\r\nMiddle\n:::spreadsheet\n[]\n:::\nEnd';
    const blocks = parseCustomBlocks(content);

    expect(blocks).toEqual([
      { type: 'markdown', content: 'Start\r\n' },
      { type: 'diagram', content: 'flowchart TD' },
      { type: 'markdown', content: '\r\nMiddle\n' },
      { type: 'spreadsheet', content: '[]' },
      { type: 'markdown', content: '\nEnd' },
    ]);
  });

  it('returns empty array for empty input', () => {
    expect(parseCustomBlocks('')).toEqual([]);
  });
});
