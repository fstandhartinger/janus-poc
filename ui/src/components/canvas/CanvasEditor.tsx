'use client';

import { useEffect, useRef } from 'react';
import { EditorView, basicSetup } from 'codemirror';
import { EditorState, type Extension } from '@codemirror/state';
import { javascript } from '@codemirror/lang-javascript';
import { python } from '@codemirror/lang-python';
import { html } from '@codemirror/lang-html';
import { css } from '@codemirror/lang-css';
import { json } from '@codemirror/lang-json';
import { markdown } from '@codemirror/lang-markdown';
import { oneDark } from '@codemirror/theme-one-dark';

interface CanvasEditorProps {
  content: string;
  language: string;
  onChange: (content: string) => void;
  readonly?: boolean;
}

const languageExtensions: Record<string, () => Extension> = {
  javascript: () => javascript(),
  typescript: () => javascript({ typescript: true }),
  python: () => python(),
  html: () => html(),
  css: () => css(),
  json: () => json(),
  markdown: () => markdown(),
  text: () => markdown(),
};

export function CanvasEditor({ content, language, onChange, readonly = false }: CanvasEditorProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const viewRef = useRef<EditorView | null>(null);
  const contentRef = useRef(content);

  useEffect(() => {
    contentRef.current = content;
  }, [content]);

  useEffect(() => {
    if (!containerRef.current) return;

    const langExt = languageExtensions[language] || (() => markdown());

    const state = EditorState.create({
      doc: content,
      extensions: [
        basicSetup,
        oneDark,
        langExt(),
        EditorState.readOnly.of(readonly),
        EditorView.updateListener.of((update) => {
          if (update.docChanged) {
            const nextContent = update.state.doc.toString();
            if (nextContent !== contentRef.current) {
              contentRef.current = nextContent;
              onChange(nextContent);
            }
          }
        }),
        EditorView.theme({
          '&': {
            height: '100%',
            fontSize: '13px',
            fontFamily: 'var(--font-mono)',
          },
          '.cm-scroller': {
            overflow: 'auto',
          },
          '.cm-content': {
            fontFamily: 'var(--font-mono)',
            padding: '16px',
          },
        }),
      ],
    });

    const view = new EditorView({
      state,
      parent: containerRef.current,
    });

    viewRef.current = view;

    return () => {
      view.destroy();
    };
  }, [language, readonly]);

  useEffect(() => {
    const view = viewRef.current;
    if (!view) return;

    const currentContent = view.state.doc.toString();
    if (content !== currentContent && content !== contentRef.current) {
      view.dispatch({
        changes: {
          from: 0,
          to: currentContent.length,
          insert: content,
        },
      });
    }
  }, [content]);

  return <div ref={containerRef} className="canvas-editor" />;
}
