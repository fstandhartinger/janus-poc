export interface ParsedImage {
  url: string;
  alt?: string;
}

/**
 * Extract inline data-image markdown and return cleaned text + images.
 *
 * Handles extremely long data URLs and missing closing parentheses
 * by treating the rest of the string as the URL when needed.
 */
export function parseImageContent(content: string): { text: string; images: ParsedImage[] } {
  if (!content) {
    return { text: content, images: [] };
  }

  const images: ParsedImage[] = [];
  let output = '';
  let cursor = 0;

  while (cursor < content.length) {
    const start = content.indexOf('![', cursor);
    if (start === -1) {
      output += content.slice(cursor);
      break;
    }

    const labelEnd = content.indexOf('](', start);
    if (labelEnd === -1) {
      output += content.slice(cursor);
      break;
    }

    const urlStart = labelEnd + 2;
    if (!content.startsWith('data:image', urlStart)) {
      cursor = urlStart;
      continue;
    }

    const closeParen = content.indexOf(')', urlStart);
    const end = closeParen === -1 ? content.length : closeParen;
    const alt = content.slice(start + 2, labelEnd);
    const url = content.slice(urlStart, end);
    const compact = url.replace(/\s+/g, '');

    images.push({ url: compact, alt: alt || undefined });
    output += content.slice(cursor, start);
    cursor = closeParen === -1 ? content.length : closeParen + 1;
  }

  const text = output.replace(/\n{3,}/g, '\n\n').trim();
  return { text, images };
}
