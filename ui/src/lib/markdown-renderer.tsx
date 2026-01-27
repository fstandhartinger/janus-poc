'use client';

import type { ReactNode } from 'react';
import ReactMarkdown, { defaultUrlTransform } from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import remarkBreaks from 'remark-breaks';
import rehypeKatex from 'rehype-katex';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { ExternalLink } from 'lucide-react';

import { GenerativeUI } from '../components/GenerativeUI';
import { ChartBlock } from '../components/viz/ChartBlock';
import { DiagramBlock } from '../components/viz/DiagramBlock';
import { SpreadsheetBlock } from '../components/viz/SpreadsheetBlock';
import { parseCustomBlocks } from '../components/viz/parseCustomBlocks';
import { Citation } from '../components/Citation';

interface MarkdownContentProps {
  content: string;
}

interface CitationEntry {
  index: number;
  url: string;
  title?: string;
}

function copyText(text: string) {
  if (navigator.clipboard?.writeText) {
    void navigator.clipboard.writeText(text);
    return;
  }

  const textarea = document.createElement('textarea');
  textarea.value = text;
  textarea.setAttribute('readonly', 'true');
  textarea.style.position = 'absolute';
  textarea.style.left = '-9999px';
  document.body.appendChild(textarea);
  textarea.select();
  document.execCommand('copy');
  document.body.removeChild(textarea);
}

function parseCitations(content: string): { text: string; citations: CitationEntry[] } {
  const citations: CitationEntry[] = [];
  const footnotes: Record<string, { url: string; title?: string }> = {};

  const footnoteRegex = /^\[\^(\d+)\]:\s*(\S+)(?:\s+"([^"]+)")?\s*$/gm;
  let text = content.replace(footnoteRegex, (_match, num, url, title) => {
    footnotes[num] = { url, title };
    return '';
  });

  text = text.replace(/\[\^(\d+)\]/g, (_match, num) => {
    const footnote = footnotes[num];
    if (!footnote) return '';
    const index = citations.length + 1;
    citations.push({ index, url: footnote.url, title: footnote.title });
    return `{{CITATION:${index}}}`;
  });

  text = text.replace(/\[\[([^\]|]+)\|([^\]]+)\]\]/g, (_match, title, url) => {
    const index = citations.length + 1;
    citations.push({ index, url, title });
    return `{{CITATION:${index}}}`;
  });

  return { text, citations };
}

function renderTextWithCitations(value: string, citations: CitationEntry[]) {
  if (!value.includes('{{CITATION:')) {
    return value;
  }

  const parts: ReactNode[] = [];
  const pattern = /\{\{CITATION:(\d+)\}\}/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = pattern.exec(value)) !== null) {
    if (match.index > lastIndex) {
      parts.push(value.slice(lastIndex, match.index));
    }
    const index = Number(match[1]);
    const citation = citations.find((entry) => entry.index === index);
    if (citation) {
      parts.push(
        <Citation key={`citation-${index}`} index={citation.index} url={citation.url} title={citation.title} />
      );
    } else {
      parts.push(match[0]);
    }
    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < value.length) {
    parts.push(value.slice(lastIndex));
  }

  return parts;
}

export function MarkdownContent({ content }: MarkdownContentProps) {
  if (!content) {
    return null;
  }

  const blocks = parseCustomBlocks(content);
  const urlTransform = (url: string) => {
    if (!url) {
      return url;
    }
    if (url.startsWith('data:image/') || url.startsWith('data:video/') || url.startsWith('data:audio/')) {
      return url;
    }
    if (url.startsWith('blob:')) {
      return url;
    }
    return defaultUrlTransform(url);
  };

  return (
    <div className="rich-content">
      {blocks.map((block, index) => {
        switch (block.type) {
          case 'chart':
            try {
              const config = JSON.parse(block.content);
              return <ChartBlock key={index} config={config} />;
            } catch {
              return (
                <div key={index} className="parse-error">
                  Invalid chart data
                </div>
              );
            }

          case 'spreadsheet':
            try {
              const data = JSON.parse(block.content);
              return <SpreadsheetBlock key={index} data={data} />;
            } catch {
              return (
                <div key={index} className="parse-error">
                  Invalid spreadsheet data
                </div>
              );
            }

          case 'diagram':
            return <DiagramBlock key={index} code={block.content} />;

          case 'markdown':
          default: {
            const { text, citations } = parseCitations(block.content);
            return (
              <div
                key={index}
                className="prose prose-invert prose-sm max-w-none
                  prose-headings:font-semibold prose-headings:text-white
                  prose-p:text-white/90 prose-p:leading-relaxed
                  prose-strong:text-white prose-strong:font-semibold
                  prose-ul:text-white/90 prose-ol:text-white/90
                  prose-li:marker:text-moss
                  prose-blockquote:border-l-moss prose-blockquote:text-white/70
                  prose-hr:border-white/10"
              >
                <ReactMarkdown
                  remarkPlugins={[remarkGfm, remarkMath, remarkBreaks]}
                  rehypePlugins={[rehypeKatex]}
                  urlTransform={urlTransform}
                  components={{
                    text({ children }) {
                      const value = Array.isArray(children) ? children.join('') : String(children ?? '');
                      if (!value || citations.length === 0) return value;
                      return <>{renderTextWithCitations(value, citations)}</>;
                    },
                    code(props) {
                      const { inline, className, children } = props as {
                        inline?: boolean;
                        className?: string;
                        children?: React.ReactNode;
                      };
                      const match = /language-([\w-]+)/.exec(className || '');
                      const language = match?.[1];
                      const codeString = String(children ?? '').replace(/\n$/, '');

                      if (!inline && language === 'html-gen-ui') {
                        return <GenerativeUI html={codeString} className="my-4" />;
                      }

                      if (!inline && language) {
                        return (
                          <div className="code-block">
                            <div className="code-header">
                              <span className="code-language">{language}</span>
                              <button
                                type="button"
                                onClick={() => copyText(codeString)}
                                className="code-copy"
                              >
                                Copy
                              </button>
                            </div>
                            <SyntaxHighlighter
                              style={vscDarkPlus}
                              language={language}
                              PreTag="div"
                            >
                              {codeString}
                            </SyntaxHighlighter>
                          </div>
                        );
                      }

                      return (
                        <code className={className}>
                          {children}
                        </code>
                      );
                    },
                    table({ children }) {
                      return (
                        <div className="markdown-table">
                          <table>{children}</table>
                        </div>
                      );
                    },
                    th({ children }) {
                      return <th className="markdown-th">{children}</th>;
                    },
                    td({ children }) {
                      return <td className="markdown-td">{children}</td>;
                    },
                    img({ src, alt }) {
                      if (!src) return null;
                      return (
                        <img
                          src={src}
                          alt={alt}
                          className="markdown-image"
                          loading="lazy"
                        />
                      );
                    },
                    a({ href, children, ...props }) {
                      const isExternal = href?.startsWith('http') || href?.startsWith('//');
                      return (
                        <a
                          href={href}
                          target={isExternal ? '_blank' : undefined}
                          rel={isExternal ? 'noopener noreferrer' : undefined}
                          className="markdown-link"
                          {...props}
                        >
                          {children}
                          {isExternal && <ExternalLink size={12} className="markdown-link-icon" />}
                        </a>
                      );
                    },
                  }}
                >
                  {text}
                </ReactMarkdown>
              </div>
            );
          }
        }
      })}
    </div>
  );
}
