export interface ParsedImage {
  url: string;
  alt?: string;
}

const MARKDOWN_IMAGE_REGEX = /!\[([^\]]*)]\((data:image\/[^)]+)\)/g;

/**
 * Extract inline data-image markdown and return cleaned text + images.
 */
export function parseImageContent(content: string): { text: string; images: ParsedImage[] } {
  if (!content) {
    return { text: content, images: [] };
  }

  const images: ParsedImage[] = [];

  const cleaned = content.replace(MARKDOWN_IMAGE_REGEX, (_match, alt, url) => {
    const compact = String(url).replace(/\s+/g, '');
    images.push({ url: compact, alt: alt || undefined });
    return '';
  });

  const text = cleaned.replace(/\n{3,}/g, '\n\n').trim();
  return { text, images };
}
