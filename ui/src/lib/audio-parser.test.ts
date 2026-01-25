import { describe, expect, it } from 'vitest';

import { parseAudioContent } from './audio-parser';

describe('parseAudioContent', () => {
  it('parses audio blocks with metadata', () => {
    const audioUrl = 'data:audio/wav;base64,AAA';
    const content = `:::audio[type=music,title=My Song,hasVocals=true,duration=90]\n${audioUrl}\n:::`;

    const result = parseAudioContent(content);

    expect(result).toHaveLength(1);
    expect(result[0]).toMatchObject({
      url: audioUrl,
      type: 'music',
      title: 'My Song',
    });
    expect(result[0].metadata?.hasVocals).toBe(true);
    expect(result[0].metadata?.duration).toBe(90);
  });

  it('detects inline audio type from context', () => {
    const audioUrl = 'data:audio/mp3;base64,BBB';
    const content = `Spoken response:${audioUrl}`;

    const result = parseAudioContent(content);

    expect(result).toHaveLength(1);
    expect(result[0].type).toBe('speech');
  });

  it('skips inline matches inside audio blocks', () => {
    const audioUrl = 'data:audio/ogg;base64,CCC';
    const content = `:::audio[type=speech]\n${audioUrl}\n:::`;

    const result = parseAudioContent(content);

    expect(result).toHaveLength(1);
    expect(result[0].url).toBe(audioUrl);
  });
});
