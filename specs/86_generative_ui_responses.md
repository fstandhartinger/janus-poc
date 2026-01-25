# Spec 86: Generative UI Responses

## Status: NOT STARTED

## Context / Why

The Janus model can respond with markdown containing code blocks. By adding a special code fence type `html-gen-ui`, the model can include interactive HTML/JavaScript UI blocks that render directly in the chat. This enables richer responses like:

- Interactive calculators, converters, visualizations
- Data exploration widgets
- Mini games or puzzles
- Form-based interactions
- Dynamic charts and graphs

This concept is proven in the [generative-chat-ui](https://github.com/fstandhartinger/generative-chat-ui) proof of concept, which demonstrates LLM-generated interactive UI blocks.

## Goals

- Add `html-gen-ui` code fence block support to chat responses
- Render generative UI securely in sandboxed iframes
- Provide fullscreen expansion capability
- Update agent prompts to understand and use generative UI
- Maintain security through proper isolation

## Non-Goals

- Full application embedding (keep blocks self-contained)
- Backend API access from UI blocks (blocks are client-side only)
- Persistent state across messages
- Complex multi-page applications

## Functional Requirements

### FR-1: Code Fence Syntax

The model can include generative UI blocks using a special code fence:

````markdown
Here's an interactive calculator for you:

```html-gen-ui
<!DOCTYPE html>
<html>
<head>
  <style>
    body {
      background: #1a1a2e;
      color: #eee;
      font-family: system-ui, sans-serif;
      padding: 1rem;
      margin: 0;
    }
    button {
      background: #63D297;
      color: #1a1a2e;
      border: none;
      padding: 0.5rem 1rem;
      border-radius: 4px;
      cursor: pointer;
    }
  </style>
</head>
<body>
  <h3>Simple Calculator</h3>
  <input type="number" id="a" placeholder="Number 1">
  <input type="number" id="b" placeholder="Number 2">
  <button onclick="calculate()">Add</button>
  <p id="result"></p>
  <script>
    function calculate() {
      const a = parseFloat(document.getElementById('a').value) || 0;
      const b = parseFloat(document.getElementById('b').value) || 0;
      document.getElementById('result').textContent = 'Result: ' + (a + b);
    }
  </script>
</body>
</html>
```

The calculator above lets you add two numbers.
````

### FR-2: Generative UI Component

Create a React component that renders the HTML in a sandboxed iframe.

```typescript
// ui/src/components/GenerativeUI.tsx

import { useState, useRef, useEffect } from 'react';
import { Maximize2, Minimize2, RefreshCw } from 'lucide-react';

interface GenerativeUIProps {
  html: string;
  className?: string;
}

export function GenerativeUI({ html, className }: GenerativeUIProps) {
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [key, setKey] = useState(0);
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Escape key to exit fullscreen
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isFullscreen) {
        setIsFullscreen(false);
      }
    };
    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [isFullscreen]);

  // Auto-resize iframe to content height
  useEffect(() => {
    const iframe = iframeRef.current;
    if (!iframe) return;

    const resizeObserver = new ResizeObserver(() => {
      try {
        const doc = iframe.contentDocument;
        if (doc?.body) {
          const height = Math.min(
            doc.body.scrollHeight + 20,
            isFullscreen ? window.innerHeight - 60 : 500
          );
          iframe.style.height = `${height}px`;
        }
      } catch {
        // Cross-origin error, use default height
      }
    });

    iframe.onload = () => {
      try {
        const doc = iframe.contentDocument;
        if (doc?.body) {
          resizeObserver.observe(doc.body);
        }
      } catch {
        // Cross-origin error, ignore
      }
    };

    return () => resizeObserver.disconnect();
  }, [key, isFullscreen]);

  const handleRefresh = () => setKey(k => k + 1);
  const toggleFullscreen = () => setIsFullscreen(!isFullscreen);

  const containerClasses = isFullscreen
    ? 'fixed inset-0 z-50 bg-gray-900 flex flex-col'
    : `relative rounded-lg border border-white/10 overflow-hidden ${className || ''}`;

  return (
    <div ref={containerRef} className={containerClasses}>
      {/* Toolbar */}
      <div className="flex items-center justify-between px-3 py-2 bg-white/5 border-b border-white/10">
        <span className="text-xs text-white/60 font-mono">Interactive UI</span>
        <div className="flex items-center gap-2">
          <button
            onClick={handleRefresh}
            className="p-1 hover:bg-white/10 rounded"
            title="Refresh"
          >
            <RefreshCw size={14} className="text-white/60" />
          </button>
          <button
            onClick={toggleFullscreen}
            className="p-1 hover:bg-white/10 rounded"
            title={isFullscreen ? 'Exit fullscreen' : 'Fullscreen'}
          >
            {isFullscreen ? (
              <Minimize2 size={14} className="text-white/60" />
            ) : (
              <Maximize2 size={14} className="text-white/60" />
            )}
          </button>
        </div>
      </div>

      {/* Sandboxed iframe */}
      <iframe
        key={key}
        ref={iframeRef}
        srcDoc={html}
        sandbox="allow-scripts"
        className="w-full bg-transparent"
        style={{
          minHeight: '200px',
          height: isFullscreen ? 'calc(100vh - 45px)' : '300px',
          border: 'none'
        }}
        title="Generative UI"
      />
    </div>
  );
}
```

### FR-3: Markdown Renderer Integration

Update the markdown renderer to detect and render `html-gen-ui` blocks.

```typescript
// ui/src/lib/markdown-renderer.tsx (update existing or create)

import ReactMarkdown from 'react-markdown';
import { GenerativeUI } from '@/components/GenerativeUI';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';

interface MarkdownContentProps {
  content: string;
}

export function MarkdownContent({ content }: MarkdownContentProps) {
  return (
    <ReactMarkdown
      components={{
        code({ node, inline, className, children, ...props }) {
          const match = /language-(\w+)/.exec(className || '');
          const language = match?.[1];
          const codeContent = String(children).replace(/\n$/, '');

          // Handle generative UI blocks
          if (language === 'html-gen-ui') {
            return <GenerativeUI html={codeContent} className="my-4" />;
          }

          // Inline code
          if (inline) {
            return (
              <code className="bg-white/10 px-1.5 py-0.5 rounded text-sm" {...props}>
                {children}
              </code>
            );
          }

          // Regular code blocks with syntax highlighting
          return (
            <SyntaxHighlighter
              style={vscDarkPlus}
              language={language || 'text'}
              PreTag="div"
              className="rounded-lg my-4"
              {...props}
            >
              {codeContent}
            </SyntaxHighlighter>
          );
        }
      }}
    >
      {content}
    </ReactMarkdown>
  );
}
```

### FR-4: MessageBubble Integration

Update MessageBubble to use the markdown renderer for assistant messages.

```typescript
// ui/src/components/MessageBubble.tsx (relevant update)

import { MarkdownContent } from '@/lib/markdown-renderer';

// In the assistant message rendering section:
{message.role === 'assistant' && (
  <div className="prose prose-invert max-w-none">
    <MarkdownContent content={message.content} />
  </div>
)}
```

### FR-5: Agent Prompt Updates

Update the baseline agent system prompts to understand generative UI capability.

```markdown
<!-- Add to baseline-agent-cli/agent-pack/prompts/system.md -->

## Generative UI Responses

You can include interactive UI widgets in your responses using the `html-gen-ui` code fence. This renders as an interactive iframe in the chat.

### When to Use Generative UI

Use `html-gen-ui` blocks when the response benefits from interactivity:
- Calculators, converters, unit transformations
- Data visualization (charts, graphs)
- Interactive forms or quizzes
- Simple games or puzzles
- Visual demonstrations
- Timeline or process visualizations

### Generative UI Requirements

1. **Self-contained**: Include all HTML, CSS, and JavaScript in one block
2. **Dark theme**: Use dark backgrounds (#1a1a2e or similar) and light text
3. **Mobile-friendly**: Design for 320px minimum width
4. **No external APIs**: Do not call external services from the UI
5. **Error handling**: Wrap JavaScript in try/catch for robustness

### Example: Interactive Widget

\`\`\`html-gen-ui
<!DOCTYPE html>
<html>
<head>
  <style>
    body {
      background: #1a1a2e;
      color: #e0e0e0;
      font-family: system-ui, -apple-system, sans-serif;
      padding: 1rem;
      margin: 0;
    }
    .card {
      background: rgba(255,255,255,0.05);
      border: 1px solid rgba(255,255,255,0.1);
      border-radius: 8px;
      padding: 1rem;
    }
    button {
      background: #63D297;
      color: #1a1a2e;
      border: none;
      padding: 0.5rem 1rem;
      border-radius: 6px;
      cursor: pointer;
      font-weight: 500;
    }
    button:hover { opacity: 0.9; }
    input, select {
      background: rgba(255,255,255,0.1);
      border: 1px solid rgba(255,255,255,0.2);
      color: #e0e0e0;
      padding: 0.5rem;
      border-radius: 4px;
      width: 100%;
      box-sizing: border-box;
    }
  </style>
</head>
<body>
  <div class="card">
    <h3 style="margin-top:0">Widget Title</h3>
    <!-- Interactive content here -->
  </div>
  <script>
    try {
      // JavaScript logic here
    } catch (error) {
      console.error('Widget error:', error);
    }
  </script>
</body>
</html>
\`\`\`

### When NOT to Use Generative UI

- Simple text answers or explanations
- Code examples the user wants to copy
- Long-form content (essays, documentation)
- Responses requiring backend/API access
- Complex multi-page applications
```

### FR-6: Security Sandboxing

The iframe uses `sandbox="allow-scripts"` which:
- Allows JavaScript execution
- Blocks form submission to external URLs
- Blocks top-level navigation
- Blocks popups and modals
- Blocks access to parent document
- Blocks access to localStorage/sessionStorage of parent

Additional considerations:
- CSP headers on the main page can further restrict iframe behavior
- Consider `allow-same-origin` only if communication with parent is needed
- Never pass sensitive data (API keys, tokens) to the iframe

### FR-7: CDN Library Support

For common use cases, the UI can load libraries from trusted CDNs:

```html
<!-- Charts: Chart.js -->
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

<!-- Maps: Leaflet -->
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>

<!-- 3D: Three.js -->
<script src="https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.min.js"></script>

<!-- Data visualization: D3.js -->
<script src="https://cdn.jsdelivr.net/npm/d3@7"></script>
```

Document recommended CDNs in the agent prompt for complex visualizations.

## Technical Design

### Component Hierarchy

```
MessageBubble
└── MarkdownContent
    ├── Regular text/formatting
    ├── SyntaxHighlighter (code blocks)
    └── GenerativeUI (html-gen-ui blocks)
        └── iframe[sandbox="allow-scripts"]
```

### State Management

- Each GenerativeUI instance is independent
- Fullscreen state is local to each instance
- Refresh resets the iframe by changing its key
- No shared state between UI blocks

### Responsive Behavior

- Default height: 300px with auto-grow up to 500px
- Fullscreen: Full viewport with 45px toolbar
- Mobile: Stack content vertically, minimum width 320px
- Toolbar collapses to icons on small screens

## Acceptance Criteria

- [ ] `html-gen-ui` code fence renders as interactive iframe
- [ ] Iframe is sandboxed (no parent DOM access)
- [ ] Fullscreen button expands to viewport
- [ ] Escape key exits fullscreen
- [ ] Refresh button reloads the content
- [ ] Auto-resize based on content height
- [ ] Dark theme styling matches Janus UI
- [ ] Agent prompts include generative UI examples
- [ ] Mobile-responsive layout
- [ ] CDN libraries load correctly in sandbox

## Files to Create/Modify

```
ui/src/
├── components/
│   ├── GenerativeUI.tsx          # NEW: Sandboxed iframe component
│   └── MessageBubble.tsx         # UPDATE: Integrate markdown renderer
├── lib/
│   └── markdown-renderer.tsx     # NEW: Custom markdown with gen-ui support

baseline-agent-cli/agent-pack/prompts/
└── system.md                     # UPDATE: Add generative UI section

baseline-langchain/
└── prompts/system.md             # UPDATE: Add generative UI section (if exists)
```

## Example Generative UI Blocks

### Temperature Converter

```html-gen-ui
<!DOCTYPE html>
<html>
<head>
  <style>
    body { background: #1a1a2e; color: #e0e0e0; font-family: system-ui; padding: 1rem; margin: 0; }
    .row { display: flex; gap: 1rem; align-items: center; margin: 0.5rem 0; }
    input { background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); color: #e0e0e0; padding: 0.5rem; border-radius: 4px; width: 100px; }
    label { width: 80px; }
  </style>
</head>
<body>
  <h3 style="margin-top:0">Temperature Converter</h3>
  <div class="row"><label>Celsius:</label><input type="number" id="c" oninput="fromC()"></div>
  <div class="row"><label>Fahrenheit:</label><input type="number" id="f" oninput="fromF()"></div>
  <div class="row"><label>Kelvin:</label><input type="number" id="k" oninput="fromK()"></div>
  <script>
    function fromC() { const c = parseFloat(document.getElementById('c').value); document.getElementById('f').value = ((c * 9/5) + 32).toFixed(2); document.getElementById('k').value = (c + 273.15).toFixed(2); }
    function fromF() { const f = parseFloat(document.getElementById('f').value); const c = (f - 32) * 5/9; document.getElementById('c').value = c.toFixed(2); document.getElementById('k').value = (c + 273.15).toFixed(2); }
    function fromK() { const k = parseFloat(document.getElementById('k').value); const c = k - 273.15; document.getElementById('c').value = c.toFixed(2); document.getElementById('f').value = ((c * 9/5) + 32).toFixed(2); }
  </script>
</body>
</html>
```

### Simple Bar Chart

```html-gen-ui
<!DOCTYPE html>
<html>
<head>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    body { background: #1a1a2e; padding: 1rem; margin: 0; }
    canvas { max-width: 100%; }
  </style>
</head>
<body>
  <canvas id="chart"></canvas>
  <script>
    new Chart(document.getElementById('chart'), {
      type: 'bar',
      data: {
        labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May'],
        datasets: [{
          label: 'Sales',
          data: [12, 19, 3, 5, 8],
          backgroundColor: '#63D297'
        }]
      },
      options: {
        plugins: { legend: { labels: { color: '#e0e0e0' } } },
        scales: {
          x: { ticks: { color: '#e0e0e0' }, grid: { color: 'rgba(255,255,255,0.1)' } },
          y: { ticks: { color: '#e0e0e0' }, grid: { color: 'rgba(255,255,255,0.1)' } }
        }
      }
    });
  </script>
</body>
</html>
```

## Related Specs

- `specs/85_pwa_mobile_install.md` - PWA installation
- `specs/47_text_to_speech_response_playback.md` - Audio responses

## References

- [Generative Chat UI PoC](https://github.com/fstandhartinger/generative-chat-ui)
- [MDN: iframe sandbox](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/iframe#sandbox)
- [Vercel AI SDK UI Streaming](https://sdk.vercel.ai/docs/concepts/ai-rsc)

NR_OF_TRIES: 0
