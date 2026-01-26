'use client';

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';

import { GenerativeUI } from '../components/GenerativeUI';
import { ChartBlock } from '../components/viz/ChartBlock';
import { DiagramBlock } from '../components/viz/DiagramBlock';
import { SpreadsheetBlock } from '../components/viz/SpreadsheetBlock';
import { parseCustomBlocks } from '../components/viz/parseCustomBlocks';

interface MarkdownContentProps {
  content: string;
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

export function MarkdownContent({ content }: MarkdownContentProps) {
  if (!content) {
    return null;
  }

  const blocks = parseCustomBlocks(content);

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
          default:
            return (
              <div key={index} className="prose prose-invert prose-sm max-w-none">
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  components={{
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
                              style={oneDark}
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
                  }}
                >
                  {block.content}
                </ReactMarkdown>
              </div>
            );
        }
      })}
    </div>
  );
}
