import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { MarkdownContent } from './markdown-renderer';

describe('MarkdownContent', () => {
  it('renders html-gen-ui blocks in a sandboxed iframe', () => {
    const content = [
      'Here is a widget:',
      '```html-gen-ui',
      '<!DOCTYPE html><html><body><h1>Hi</h1></body></html>',
      '```',
    ].join('\n');

    render(React.createElement(MarkdownContent, { content }));

    const iframe = screen.getByTitle('Generative UI');
    expect(iframe).toBeInTheDocument();
    expect(iframe).toHaveAttribute('sandbox', 'allow-scripts');
  });
});
