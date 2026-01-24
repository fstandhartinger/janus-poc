import { useCanvasStore } from '@/store/canvas';

export interface CanvasBlock {
  language: string;
  title: string;
  content: string;
  readonly: boolean;
}

const buildCanvasRegex = () => /:::canvas\[([^\]]*)\]\s*\r?\n([\s\S]*?)\r?\n:::/g;

export function parseCanvasBlocks(content: string): CanvasBlock[] {
  const blocks: CanvasBlock[] = [];
  if (!content) return blocks;

  const regex = buildCanvasRegex();
  let match: RegExpExecArray | null = null;

  while ((match = regex.exec(content)) !== null) {
    const attributes = parseAttributes(match[1]);
    blocks.push({
      language: attributes.language || 'text',
      title: attributes.title || 'Untitled',
      content: match[2].trim(),
      readonly: attributes.readonly === 'true',
    });
  }

  return blocks;
}

function parseAttributes(attrString: string): Record<string, string> {
  const attrs: Record<string, string> = {};
  if (!attrString) return attrs;

  const regex = /(\w+)=([^,\]]+)/g;
  let match: RegExpExecArray | null = null;

  while ((match = regex.exec(attrString)) !== null) {
    attrs[match[1]] = match[2].trim();
  }

  return attrs;
}

export function handleCanvasContent(content: string): void {
  const blocks = parseCanvasBlocks(content);

  if (blocks.length > 0) {
    const block = blocks[0];
    const store = useCanvasStore.getState();
    const existingDoc = Array.from(store.documents.values()).find(
      (doc) => doc.title === block.title && doc.language === block.language
    );

    if (existingDoc) {
      store.openCanvas({ ...existingDoc, readonly: block.readonly });
      if (block.content && block.content !== existingDoc.content) {
        store.updateContent(block.content, 'AI edit');
      }
      return;
    }

    store.createDocument(block.title, block.language, block.content, block.readonly);
  }
}

export function stripCanvasBlocks(content: string): string {
  if (!content) return content;

  const regex = buildCanvasRegex();
  return content
    .replace(regex, '')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}
