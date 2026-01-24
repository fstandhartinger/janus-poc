export type RichBlock = { type: string; content: string };

const blockRegex = /:::(\w+)\r?\n([\s\S]*?)\r?\n:::/g;

export function parseCustomBlocks(content: string): RichBlock[] {
  const blocks: RichBlock[] = [];
  if (!content) {
    return blocks;
  }

  let lastIndex = 0;
  let match: RegExpExecArray | null = null;

  while ((match = blockRegex.exec(content)) !== null) {
    if (match.index > lastIndex) {
      blocks.push({
        type: 'markdown',
        content: content.slice(lastIndex, match.index),
      });
    }

    blocks.push({
      type: match[1].toLowerCase(),
      content: match[2].trim(),
    });

    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < content.length) {
    blocks.push({
      type: 'markdown',
      content: content.slice(lastIndex),
    });
  }

  return blocks;
}
