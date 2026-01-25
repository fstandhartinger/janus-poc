# Spec 88: Chat UI Improvements

## Status: NOT STARTED

## Context / Why

The chat UI has several usability issues and missing convenience features that affect the user experience:

1. Visual glitches (sidebar expand button clipping)
2. Redundant navigation elements
3. Jumpy streaming text display
4. Aggressive auto-scroll during streaming
5. Confusing "thinking" indicator behavior
6. Missing convenience features (copy, regenerate, share)
7. Links not opening in new tabs
8. No citation/reference support for research claims

This spec addresses all these issues to create a polished, professional chat experience.

## Goals

- Fix visual bugs in sidebar and navigation
- Smooth streaming text experience
- Smart auto-scroll that doesn't interrupt reading
- Proper thinking indicator behavior
- Add message action buttons (copy, regenerate, share)
- Links open in new tabs
- Citation/reference support
- Clean, minimal navigation

## Non-Goals

- Major layout redesign
- New chat features (covered in other specs)
- Mobile-specific redesign (minor adjustments only)

## Functional Requirements

### FR-1: Fix Sidebar Expand Button Clipping

The expand/collapse button shows only half the circle when sidebar is collapsed.

**Problem:** Button is positioned at the edge and gets clipped by overflow.

**Solution:** Position button to always be fully visible.

```typescript
// ui/src/components/chat/Sidebar.tsx

// Before: Button clips when sidebar is collapsed
<button className="absolute -right-3 top-1/2 ...">

// After: Button positioned outside overflow boundary
export function Sidebar({ isCollapsed, onToggle }: SidebarProps) {
  return (
    <div className="relative">
      {/* Sidebar content */}
      <div
        className={cn(
          "h-full bg-gray-900 border-r border-white/10 transition-all duration-300",
          isCollapsed ? "w-0 overflow-hidden" : "w-64"
        )}
      >
        {/* Sidebar content here */}
      </div>

      {/* Toggle button - always visible, positioned outside sidebar */}
      <button
        onClick={onToggle}
        className={cn(
          "absolute top-1/2 -translate-y-1/2 z-50",
          "w-6 h-6 rounded-full",
          "bg-gray-800 border border-white/20",
          "flex items-center justify-center",
          "hover:bg-gray-700 transition-colors",
          isCollapsed ? "left-2" : "left-[248px]"  // 256px - 8px
        )}
      >
        {isCollapsed ? (
          <ChevronRight size={14} className="text-white/60" />
        ) : (
          <ChevronLeft size={14} className="text-white/60" />
        )}
      </button>
    </div>
  );
}
```

### FR-2: Remove Header Bar in Chat View

Replace the full navigation header with minimal branding.

```typescript
// ui/src/app/chat/layout.tsx or page.tsx

// Remove the shared Header component in chat view
// Add minimal brand element instead

export default function ChatLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="h-screen flex flex-col bg-background">
      {/* Minimal top bar - no full header */}
      <div className="flex-1 flex overflow-hidden">
        <Sidebar />
        <main className="flex-1 flex flex-col">
          {/* Chat header with brand */}
          <ChatHeader />
          {children}
        </main>
      </div>
    </div>
  );
}

// ui/src/components/chat/ChatHeader.tsx
function ChatHeader() {
  return (
    <div className="h-14 flex items-center justify-between px-4 border-b border-white/10">
      {/* Left: Brand link to home */}
      <Link
        href="/"
        className="text-xl font-bold tracking-tight hover:text-moss transition-colors"
      >
        JANUS
      </Link>

      {/* Center: Session info and model selector */}
      <div className="flex items-center gap-4">
        <span className="text-sm text-white/60">SESSION</span>
        <ModelSelector />
        <NewChatButton />
      </div>

      {/* Right: Settings/options if needed */}
      <div className="w-20" /> {/* Spacer for balance */}
    </div>
  );
}
```

### FR-3: Clean Up Sidebar

Remove redundant elements from sidebar.

```typescript
// ui/src/components/chat/Sidebar.tsx

// REMOVE:
// - Home button/link (use JANUS brand instead)
// - New chat button when collapsed (available in header)
// - Reduced-width collapsed state showing buttons

// Sidebar should either:
// - Be fully expanded (showing conversation history)
// - Be fully collapsed (showing nothing, just the toggle button)

export function Sidebar({ isCollapsed, onToggle }: SidebarProps) {
  return (
    <div className="relative flex-shrink-0">
      {/* Main sidebar - hidden when collapsed */}
      <aside
        className={cn(
          "h-full bg-gray-900/80 backdrop-blur-sm border-r border-white/10",
          "transition-all duration-300 ease-in-out overflow-hidden",
          isCollapsed ? "w-0" : "w-64"
        )}
      >
        <div className="p-4 space-y-4">
          {/* New Chat button */}
          <button
            onClick={onNewChat}
            className="w-full flex items-center gap-2 px-3 py-2 rounded-lg
                       bg-moss/20 text-moss hover:bg-moss/30 transition-colors"
          >
            <Plus size={18} />
            <span>New Chat</span>
          </button>

          {/* Conversation history */}
          <div className="space-y-1">
            <h3 className="text-xs text-white/40 uppercase tracking-wider px-2">
              Recent
            </h3>
            <ConversationList />
          </div>
        </div>
      </aside>

      {/* Toggle button */}
      <ToggleButton isCollapsed={isCollapsed} onToggle={onToggle} />
    </div>
  );
}
```

### FR-4: Remove Non-Functional Hamburger Menu

Check and remove or fix the hamburger menu button.

```typescript
// ui/src/components/chat/ChatHeader.tsx

// If hamburger has no functionality, remove it entirely
// If it has functionality (e.g., mobile menu), only show on mobile

function ChatHeader() {
  return (
    <div className="h-14 flex items-center justify-between px-4 border-b border-white/10">
      {/* Mobile-only: Hamburger for sidebar toggle */}
      <button
        onClick={toggleSidebar}
        className="md:hidden p-2 hover:bg-white/10 rounded-lg"
        aria-label="Toggle sidebar"
      >
        <Menu size={20} />
      </button>

      {/* Desktop: Show brand */}
      <Link href="/" className="hidden md:block text-xl font-bold">
        JANUS
      </Link>

      {/* ... rest of header */}
    </div>
  );
}
```

### FR-5: Smooth Streaming Text

Make streaming text appear smoothly without visual jumpiness.

```typescript
// ui/src/components/MessageBubble.tsx

// Use CSS for smooth text appearance
const streamingStyles = `
  @keyframes fadeIn {
    from { opacity: 0.7; }
    to { opacity: 1; }
  }

  .streaming-text span:last-child {
    animation: fadeIn 0.15s ease-out;
  }
`;

// Or use a buffer approach to batch updates
function useStreamingBuffer(content: string, isStreaming: boolean) {
  const [displayContent, setDisplayContent] = useState('');
  const bufferRef = useRef('');
  const rafRef = useRef<number>();

  useEffect(() => {
    if (!isStreaming) {
      setDisplayContent(content);
      return;
    }

    bufferRef.current = content;

    // Batch updates with requestAnimationFrame for smooth rendering
    const updateDisplay = () => {
      if (bufferRef.current !== displayContent) {
        setDisplayContent(bufferRef.current);
      }
      rafRef.current = requestAnimationFrame(updateDisplay);
    };

    rafRef.current = requestAnimationFrame(updateDisplay);

    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, [content, isStreaming]);

  return displayContent;
}

// Apply smooth container transition
<div
  className={cn(
    "prose prose-invert max-w-none",
    isStreaming && "transition-all duration-100 ease-out"
  )}
  style={{
    // Prevent layout shifts during streaming
    minHeight: isStreaming ? 'auto' : undefined,
  }}
>
  <MarkdownContent content={displayContent} />
</div>
```

### FR-6: Smart Auto-Scroll

Only auto-scroll when user is already at the bottom.

```typescript
// ui/src/hooks/useSmartScroll.ts

export function useSmartScroll(containerRef: RefObject<HTMLElement>, deps: any[]) {
  const isNearBottom = useRef(true);
  const userScrolledUp = useRef(false);

  // Track if user is near bottom
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const handleScroll = () => {
      const { scrollTop, scrollHeight, clientHeight } = container;
      const distanceFromBottom = scrollHeight - scrollTop - clientHeight;

      // Consider "near bottom" if within 100px
      isNearBottom.current = distanceFromBottom < 100;

      // Detect if user scrolled up manually
      if (distanceFromBottom > 200) {
        userScrolledUp.current = true;
      }
    };

    container.addEventListener('scroll', handleScroll, { passive: true });
    return () => container.removeEventListener('scroll', handleScroll);
  }, [containerRef]);

  // Auto-scroll only if near bottom and user hasn't scrolled up
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    if (isNearBottom.current && !userScrolledUp.current) {
      // Smooth scroll to bottom
      container.scrollTo({
        top: container.scrollHeight,
        behavior: 'smooth',
      });
    }
  }, deps);

  // Reset user scroll state when new message starts
  const resetUserScroll = useCallback(() => {
    userScrolledUp.current = false;
  }, []);

  return { resetUserScroll };
}

// Usage in chat component
function ChatMessages({ messages, isStreaming }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const lastMessageContent = messages[messages.length - 1]?.content;

  const { resetUserScroll } = useSmartScroll(containerRef, [lastMessageContent]);

  // Reset when new message starts
  useEffect(() => {
    if (isStreaming) resetUserScroll();
  }, [messages.length]);

  return (
    <div ref={containerRef} className="flex-1 overflow-y-auto">
      {messages.map((m) => <MessageBubble key={m.id} message={m} />)}
    </div>
  );
}
```

### FR-7: Fix Thinking Indicator

Show thinking only while waiting for content, hide when done.

```typescript
// ui/src/components/ThinkingIndicator.tsx

interface ThinkingIndicatorProps {
  isVisible: boolean;
  message?: string;
}

export function ThinkingIndicator({ isVisible, message }: ThinkingIndicatorProps) {
  if (!isVisible) return null;

  return (
    <div className="flex items-center gap-2 text-white/50 text-sm py-2 animate-pulse">
      <div className="flex gap-1">
        <span className="w-1.5 h-1.5 bg-moss rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
        <span className="w-1.5 h-1.5 bg-moss rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
        <span className="w-1.5 h-1.5 bg-moss rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
      </div>
      <span>{message || 'Thinking...'}</span>
    </div>
  );
}

// Usage in MessageBubble
function MessageBubble({ message, isStreaming }: Props) {
  const hasContent = message.content && message.content.length > 0;
  const showThinking = isStreaming && !hasContent;

  return (
    <div className="message-bubble">
      {showThinking ? (
        <ThinkingIndicator isVisible={true} />
      ) : (
        <MarkdownContent content={message.content} />
      )}
    </div>
  );
}
```

### FR-8: Message Action Buttons

Add subtle action buttons to message bubbles.

```typescript
// ui/src/components/MessageActions.tsx

interface MessageActionsProps {
  message: Message;
  onCopy: () => void;
  onRegenerate?: () => void;
  onShare?: () => void;
}

export function MessageActions({ message, onCopy, onRegenerate, onShare }: MessageActionsProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
      {/* Copy button */}
      <button
        onClick={handleCopy}
        className="p-1.5 rounded hover:bg-white/10 text-white/40 hover:text-white/80"
        title="Copy to clipboard"
      >
        {copied ? <Check size={14} className="text-moss" /> : <Copy size={14} />}
      </button>

      {/* Regenerate button - only for assistant messages */}
      {message.role === 'assistant' && onRegenerate && (
        <button
          onClick={onRegenerate}
          className="p-1.5 rounded hover:bg-white/10 text-white/40 hover:text-white/80"
          title="Regenerate response"
        >
          <RefreshCw size={14} />
        </button>
      )}

      {/* Share button */}
      {onShare && (
        <button
          onClick={onShare}
          className="p-1.5 rounded hover:bg-white/10 text-white/40 hover:text-white/80"
          title="Share conversation"
        >
          <Share2 size={14} />
        </button>
      )}
    </div>
  );
}

// Usage in MessageBubble
function MessageBubble({ message, onRegenerate, onShare }: Props) {
  return (
    <div className="group relative">
      <div className="message-content">
        <MarkdownContent content={message.content} />
      </div>

      {/* Actions appear on hover, positioned at bottom-right */}
      <div className="absolute -bottom-2 right-0 translate-y-full">
        <MessageActions
          message={message}
          onCopy={() => {}}
          onRegenerate={message.role === 'assistant' ? onRegenerate : undefined}
          onShare={onShare}
        />
      </div>
    </div>
  );
}
```

### FR-9: Links Open in New Tab

Configure markdown renderer to open external links in new tabs.

```typescript
// ui/src/lib/markdown-renderer.tsx

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

export function MarkdownContent({ content }: { content: string }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        // Links open in new tab
        a({ href, children, ...props }) {
          const isExternal = href?.startsWith('http') || href?.startsWith('//');

          return (
            <a
              href={href}
              target={isExternal ? '_blank' : undefined}
              rel={isExternal ? 'noopener noreferrer' : undefined}
              className="text-moss hover:underline"
              {...props}
            >
              {children}
              {isExternal && (
                <ExternalLink size={12} className="inline ml-1 opacity-60" />
              )}
            </a>
          );
        },

        // ... other components
      }}
    >
      {content}
    </ReactMarkdown>
  );
}
```

### FR-10: Citation/Reference Support

Support inline citations that link to sources.

```markdown
## Citation Format

The model can include citations using a special format:

"The population of Tokyo is 14 million[^1] making it the largest city[^2]."

[^1]: https://example.com/tokyo-stats "Tokyo Statistics 2024"
[^2]: https://example.com/world-cities "World's Largest Cities"

Or inline references:

"According to [[Wikipedia: Tokyo|https://en.wikipedia.org/wiki/Tokyo]], the city has..."
```

```typescript
// ui/src/components/Citation.tsx

interface CitationProps {
  index: number;
  url: string;
  title?: string;
}

export function Citation({ index, url, title }: CitationProps) {
  const [showPreview, setShowPreview] = useState(false);

  return (
    <span className="relative inline-block">
      <button
        onClick={() => window.open(url, '_blank')}
        onMouseEnter={() => setShowPreview(true)}
        onMouseLeave={() => setShowPreview(false)}
        className="inline-flex items-center justify-center w-4 h-4 text-[10px]
                   bg-moss/20 text-moss rounded-full hover:bg-moss/30
                   align-super cursor-pointer"
      >
        {index}
      </button>

      {/* Preview tooltip */}
      {showPreview && (
        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 z-50
                        bg-gray-800 rounded-lg p-2 shadow-lg min-w-48 max-w-72">
          <p className="text-xs text-white/80 line-clamp-2">{title || url}</p>
          <p className="text-[10px] text-white/40 truncate mt-1">{url}</p>
        </div>
      )}
    </span>
  );
}

// ui/src/lib/markdown-renderer.tsx - add citation parsing

function parseCitations(content: string): { text: string; citations: Citation[] } {
  const citations: Citation[] = [];
  let citationIndex = 1;

  // Parse footnote-style citations: [^1]: url "title"
  const footnoteRegex = /\[\^(\d+)\]:\s*(\S+)(?:\s+"([^"]+)")?/g;
  const footnotes: Record<string, { url: string; title?: string }> = {};

  let text = content.replace(footnoteRegex, (_, num, url, title) => {
    footnotes[num] = { url, title };
    return ''; // Remove footnote definitions from text
  });

  // Replace footnote references: [^1]
  text = text.replace(/\[\^(\d+)\]/g, (_, num) => {
    const footnote = footnotes[num];
    if (footnote) {
      citations.push({
        index: citationIndex++,
        url: footnote.url,
        title: footnote.title,
      });
      return `{{CITATION:${citations.length}}}`;
    }
    return '';
  });

  return { text, citations };
}
```

### FR-11: Share Conversation Modal

Allow users to share the conversation.

```typescript
// ui/src/components/ShareModal.tsx

interface ShareModalProps {
  isOpen: boolean;
  onClose: () => void;
  conversationId: string;
  messages: Message[];
}

export function ShareModal({ isOpen, onClose, conversationId, messages }: ShareModalProps) {
  const [shareUrl, setShareUrl] = useState('');
  const [copied, setCopied] = useState(false);

  const generateShareLink = async () => {
    // Generate a shareable link (could be stored in backend or encoded)
    const shareId = await createShareableConversation(conversationId, messages);
    const url = `${window.location.origin}/share/${shareId}`;
    setShareUrl(url);
  };

  const copyToClipboard = async () => {
    await navigator.clipboard.writeText(shareUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (!isOpen) return null;

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Share Conversation</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          {!shareUrl ? (
            <button
              onClick={generateShareLink}
              className="w-full py-2 bg-moss text-background rounded-lg"
            >
              Generate Share Link
            </button>
          ) : (
            <div className="flex gap-2">
              <input
                value={shareUrl}
                readOnly
                className="flex-1 bg-white/10 rounded px-3 py-2 text-sm"
              />
              <button
                onClick={copyToClipboard}
                className="px-4 py-2 bg-moss/20 text-moss rounded"
              >
                {copied ? 'Copied!' : 'Copy'}
              </button>
            </div>
          )}

          {/* Alternative: Copy as text */}
          <button
            onClick={() => copyConversationAsText(messages)}
            className="w-full py-2 border border-white/20 rounded-lg text-white/60"
          >
            Copy as Plain Text
          </button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

function copyConversationAsText(messages: Message[]) {
  const text = messages
    .map((m) => `${m.role.toUpperCase()}:\n${m.content}`)
    .join('\n\n---\n\n');
  navigator.clipboard.writeText(text);
}
```

### FR-12: Improved Markdown Rendering

Enhance markdown rendering with better styling and features.

```typescript
// ui/src/lib/markdown-renderer.tsx

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';

export function MarkdownContent({ content }: { content: string }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm, remarkMath]}
      rehypePlugins={[rehypeKatex]}
      className="prose prose-invert prose-sm max-w-none
                 prose-headings:font-semibold prose-headings:text-white
                 prose-p:text-white/90 prose-p:leading-relaxed
                 prose-strong:text-white prose-strong:font-semibold
                 prose-ul:text-white/90 prose-ol:text-white/90
                 prose-li:marker:text-moss
                 prose-blockquote:border-l-moss prose-blockquote:text-white/70
                 prose-hr:border-white/10"
      components={{
        // Code blocks with copy button
        code({ node, inline, className, children, ...props }) {
          const match = /language-(\w+)/.exec(className || '');
          const language = match?.[1];
          const codeContent = String(children).replace(/\n$/, '');

          if (language === 'html-gen-ui') {
            return <GenerativeUI html={codeContent} className="my-4" />;
          }

          if (inline) {
            return (
              <code
                className="bg-white/10 px-1.5 py-0.5 rounded text-sm font-mono"
                {...props}
              >
                {children}
              </code>
            );
          }

          return (
            <div className="relative group my-4">
              <CopyButton
                content={codeContent}
                className="absolute right-2 top-2 opacity-0 group-hover:opacity-100"
              />
              <SyntaxHighlighter
                style={vscDarkPlus}
                language={language || 'text'}
                PreTag="div"
                className="rounded-lg !bg-gray-900/50 text-sm"
                showLineNumbers={codeContent.split('\n').length > 3}
              >
                {codeContent}
              </SyntaxHighlighter>
            </div>
          );
        },

        // Tables with better styling
        table({ children }) {
          return (
            <div className="overflow-x-auto my-4">
              <table className="min-w-full border-collapse">
                {children}
              </table>
            </div>
          );
        },

        th({ children }) {
          return (
            <th className="border border-white/10 bg-white/5 px-4 py-2 text-left font-medium">
              {children}
            </th>
          );
        },

        td({ children }) {
          return (
            <td className="border border-white/10 px-4 py-2">
              {children}
            </td>
          );
        },

        // Images with loading state
        img({ src, alt }) {
          return (
            <img
              src={src}
              alt={alt}
              className="rounded-lg max-w-full h-auto my-4"
              loading="lazy"
            />
          );
        },

        // Links open in new tab
        a({ href, children }) {
          const isExternal = href?.startsWith('http');
          return (
            <a
              href={href}
              target={isExternal ? '_blank' : undefined}
              rel={isExternal ? 'noopener noreferrer' : undefined}
              className="text-moss hover:underline inline-flex items-center gap-1"
            >
              {children}
              {isExternal && <ExternalLink size={12} className="opacity-60" />}
            </a>
          );
        },
      }}
    >
      {content}
    </ReactMarkdown>
  );
}
```

## Technical Design

### Component Updates

```
ui/src/
├── app/
│   └── chat/
│       ├── layout.tsx          # UPDATE: Remove header, minimal layout
│       └── page.tsx            # UPDATE: Use new components
├── components/
│   ├── chat/
│   │   ├── Sidebar.tsx         # UPDATE: Fix button, remove home link
│   │   ├── ChatHeader.tsx      # UPDATE: Minimal with JANUS brand
│   │   ├── MessageBubble.tsx   # UPDATE: Add actions, fix thinking
│   │   └── MessageActions.tsx  # NEW: Copy, regenerate, share buttons
│   ├── ThinkingIndicator.tsx   # UPDATE: Show only when needed
│   ├── Citation.tsx            # NEW: Clickable references
│   ├── ShareModal.tsx          # NEW: Share conversation dialog
│   └── GenerativeUI.tsx        # From spec 86
├── hooks/
│   └── useSmartScroll.ts       # NEW: Smart auto-scroll
└── lib/
    └── markdown-renderer.tsx   # UPDATE: Better rendering, new tab links
```

### CSS Additions

```css
/* Smooth streaming animation */
@keyframes streamFadeIn {
  from {
    opacity: 0.7;
    transform: translateY(2px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.streaming-content {
  animation: streamFadeIn 0.1s ease-out;
}

/* Message actions fade in */
.message-bubble:hover .message-actions {
  opacity: 1;
  transform: translateY(0);
}

.message-actions {
  opacity: 0;
  transform: translateY(4px);
  transition: all 0.2s ease-out;
}

/* Citation tooltip */
.citation-tooltip {
  animation: fadeIn 0.15s ease-out;
}
```

## Acceptance Criteria

### Visual Fixes
- [ ] Sidebar expand button shows full circle in both states
- [ ] No header bar with navigation in chat view
- [ ] JANUS brand top-left links to home
- [ ] No home link in sidebar
- [ ] Collapsed sidebar shows nothing (just toggle button)
- [ ] Hamburger menu removed or only shown when functional

### Streaming & Scrolling
- [ ] Text streaming appears smooth without jumps
- [ ] Auto-scroll only when user is at bottom
- [ ] User can scroll up to read while streaming continues
- [ ] New user message resets scroll behavior

### Thinking Indicator
- [ ] Only shows when waiting for first content
- [ ] Disappears when content starts streaming
- [ ] Never shows after response is complete

### Message Actions
- [ ] Copy button on all messages
- [ ] Regenerate button on assistant messages
- [ ] Share button opens share modal
- [ ] Actions appear on hover, disappear when not hovering

### Links & References
- [ ] External links open in new tab
- [ ] External link icon indicator
- [ ] Citations render as clickable superscript numbers
- [ ] Citation hover shows preview tooltip

### Markdown
- [ ] Code blocks have copy buttons
- [ ] Syntax highlighting works
- [ ] Tables render properly
- [ ] Math equations render (if KaTeX installed)
- [ ] Generative UI blocks render in iframes

## Files to Create/Modify

```
ui/src/
├── app/chat/layout.tsx         # UPDATE
├── components/
│   ├── chat/
│   │   ├── Sidebar.tsx         # UPDATE
│   │   ├── ChatHeader.tsx      # UPDATE/NEW
│   │   ├── MessageBubble.tsx   # UPDATE
│   │   └── MessageActions.tsx  # NEW
│   ├── ThinkingIndicator.tsx   # UPDATE
│   ├── Citation.tsx            # NEW
│   └── ShareModal.tsx          # NEW
├── hooks/
│   └── useSmartScroll.ts       # NEW
├── lib/
│   └── markdown-renderer.tsx   # UPDATE
└── styles/
    └── chat.css                # UPDATE (animations)
```

## Related Specs

- `specs/86_generative_ui_responses.md` - Generative UI in chat
- `specs/85_pwa_mobile_install.md` - PWA/mobile considerations
- `specs/87_api_documentation_page.md` - API docs page

NR_OF_TRIES: 0
