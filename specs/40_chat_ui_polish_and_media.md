# Spec 40: Chat UI Polish and Media Display

## Status: COMPLETE

## Context / Why

The chat UI has several issues that need polishing:

1. **Landing page text redundancy** - "the intelligence engine" appears below JANUS and is redundant with the subtitle that also mentions "intelligence engine"
2. **Unnecessary UI elements** - The "Thinking: On/Off" toggle and "Workspace / Janus Auto / J" branding add clutter without value
3. **Mobile layout issues** - On mobile portrait mode, the chat requires scrolling to reach the input bar even with no messages
4. **Limited media display** - Chat responses can only display images; needs support for videos, audio, and other media types

## Goals

- Remove redundant landing page text
- Simplify chat UI by removing unused controls
- Fix mobile portrait layout so input is always accessible
- Support rich media display in chat responses (images, videos, audio, files)

## Non-Goals

- Complete UI redesign
- Adding new features to the sidebar
- Changing the chat input functionality

## Functional Requirements

### FR-1: Remove Landing Page Tagline

Remove "the intelligence engine" text from the hero section:

```tsx
// ui/src/components/landing/HeroSection.tsx

// BEFORE:
<h1 className="hero-title">
  <span className="gradient-text">JANUS</span>
</h1>
<p className="hero-tagline">the intelligence engine</p>  // REMOVE THIS
<p className="hero-subtitle">
  Anything In. Anything Out. Build the intelligence engine...
</p>

// AFTER:
<h1 className="hero-title">
  <span className="gradient-text">JANUS</span>
</h1>
<p className="hero-subtitle">
  Anything In. Anything Out. Build the intelligence engine...
</p>
```

### FR-2: Remove Thinking Toggle

Remove the "Thinking: On/Off" toggle from the chat top bar:

```tsx
// ui/src/components/ChatArea.tsx

// REMOVE this section from chat-topbar-right:
<button onClick={toggleReasoning} className="chat-toggle">
  {showReasoning ? 'Thinking: On' : 'Thinking: Off'}
</button>

// Also remove from useChatStore destructuring:
// - toggleReasoning
// - showReasoning (keep internally for future use, just don't show toggle)
```

**Note**: Keep `showReasoning` state and pass it to MessageBubble, but default it to `true` and remove the UI toggle. Users who want to hide reasoning can use a future settings panel.

### FR-3: Remove Workspace Header from Sidebar

Remove the "Workspace / Janus Auto / J" section from the sidebar:

```tsx
// ui/src/components/Sidebar.tsx

// REMOVE this entire section (lines 42-51):
<div className="flex items-center justify-between">
  <div className="chat-sidebar-hide-collapsed">
    <div className="text-xs uppercase tracking-[0.3em] text-[#6B7280]">Workspace</div>
    <div className="text-sm text-[#F3F4F6] mt-2 font-medium">Janus Auto</div>
  </div>
  <div className="w-10 h-10 rounded-xl bg-[#111726] border border-[#1F2937] flex items-center justify-center text-[#63D297]">
    J
  </div>
</div>

// ALSO REMOVE these placeholder buttons (lines 92-99 area):
<div className="mt-4 search-input chat-sidebar-hide-collapsed">
  // Keep search input
</div>
<generic>
  <button "Library">  // REMOVE
  <button "Agents">   // REMOVE
  <button "Studio">   // REMOVE
</generic>
```

**Simplified sidebar structure:**
```tsx
<aside className={sidebarClasses}>
  {/* Header with Home link and New Chat */}
  <div className="px-5 pt-5 pb-4 border-b border-[#1F2937]">
    <Link href="/" className="chat-sidebar-item w-full flex items-center gap-2">
      {/* Home icon */}
      <span className="chat-sidebar-hide-collapsed">Home</span>
    </Link>

    <button onClick={createSession} className="mt-4 w-full ...">
      <span>+</span>
      <span className="chat-sidebar-hide-collapsed">New Chat</span>
    </button>

    <button onClick={onClose} className="mt-3 ... lg:hidden">
      Close
    </button>

    <div className="mt-4 search-input chat-sidebar-hide-collapsed">
      <input placeholder="Search chats" />
    </div>
  </div>

  {/* Chat list */}
  <div className="flex-1 overflow-y-auto px-4 py-4">
    {/* Chats section unchanged */}
  </div>

  {/* Footer */}
  <div className="px-5 py-4 border-t border-[#1F2937] text-xs text-[#6B7280]">
    Janus PoC
  </div>
</aside>
```

### FR-4: Fix Mobile Portrait Layout

The chat layout on mobile should ensure the input bar is always visible without scrolling:

```css
/* ui/src/app/globals.css */

/* Fix: Make chat area fill available height properly on mobile */
.chat-aurora-bg {
  /* Ensure full viewport height minus browser chrome */
  min-height: 100dvh; /* Use dynamic viewport height */
  height: 100dvh;
}

.chat-shell {
  display: flex;
  flex: 1;
  min-height: 0;
  height: calc(100dvh - 64px); /* Subtract header height */
  overflow: hidden;
}

/* Chat area should use flex to push input to bottom */
@media (max-width: 1023px) {
  .chat-shell {
    flex-direction: column;
    height: calc(100dvh - 64px);
  }
}
```

```tsx
// ui/src/components/ChatArea.tsx

// Ensure the main container uses proper flex layout:
<div className="flex-1 flex flex-col min-h-0">
  {/* Top bar - fixed height */}
  <div className="chat-topbar shrink-0">
    {/* ... */}
  </div>

  {/* Messages area - scrollable, takes remaining space */}
  <div className="flex-1 overflow-y-auto min-h-0 px-6 py-6">
    {/* ... */}
  </div>

  {/* Input area - fixed at bottom */}
  <div className="shrink-0 px-6 pb-6 pt-2">
    <ChatInput onSend={handleSend} disabled={isStreaming} />
  </div>
</div>
```

### FR-5: Rich Media Display in Messages

Support displaying various media types in chat responses:

```typescript
// ui/src/types/chat.ts

export interface VideoContent {
  type: 'video';
  video: {
    url: string;
    mime_type?: string;
    poster?: string; // Thumbnail
  };
}

export interface AudioContent {
  type: 'audio';
  audio: {
    url: string;
    mime_type?: string;
    duration?: number;
  };
}

export interface FileContent {
  type: 'file';
  file: {
    url: string;
    name: string;
    mime_type: string;
    size: number;
  };
}

export type MessageContent = string | (
  | TextContent
  | ImageUrlContent
  | VideoContent
  | AudioContent
  | FileContent
)[];
```

```tsx
// ui/src/components/MessageBubble.tsx

import { MediaRenderer } from './MediaRenderer';

export function MessageBubble({ message, showReasoning }: MessageBubbleProps) {
  // ... existing code ...

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      <div className={`chat-message max-w-[80%] ${isUser ? 'chat-message-user' : 'chat-message-assistant'}`}>

        {/* Render all media content */}
        <MediaRenderer content={message.content} />

        {/* Reasoning panel */}
        {showReasoning && message.reasoning_content && (
          <div className="mb-3 p-3 rounded-lg ...">
            {/* ... */}
          </div>
        )}

        {/* Text content */}
        <div className="prose prose-invert prose-sm max-w-none">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{textContent}</ReactMarkdown>
        </div>

        {/* Artifacts */}
        {/* ... */}
      </div>
    </div>
  );
}
```

### FR-6: Media Renderer Component

```tsx
// ui/src/components/MediaRenderer.tsx

import { useState } from 'react';
import { Play, Pause, Download, FileText, Film, Music } from 'lucide-react';
import type { MessageContent } from '@/types/chat';

interface MediaRendererProps {
  content: MessageContent;
}

export function MediaRenderer({ content }: MediaRendererProps) {
  if (typeof content === 'string') return null;

  const mediaItems = content.filter(
    (c) => c.type === 'image_url' || c.type === 'video' || c.type === 'audio' || c.type === 'file'
  );

  if (mediaItems.length === 0) return null;

  return (
    <div className="mb-3 flex flex-wrap gap-2">
      {mediaItems.map((item, index) => (
        <MediaItem key={index} item={item} />
      ))}
    </div>
  );
}

function MediaItem({ item }: { item: any }) {
  switch (item.type) {
    case 'image_url':
      return <ImageDisplay url={item.image_url.url} />;
    case 'video':
      return <VideoPlayer video={item.video} />;
    case 'audio':
      return <AudioPlayer audio={item.audio} />;
    case 'file':
      return <FileDownload file={item.file} />;
    default:
      return null;
  }
}

function ImageDisplay({ url }: { url: string }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <>
      <img
        src={url}
        alt="Attached"
        className="max-w-[300px] max-h-[300px] rounded-lg border border-ink-700 cursor-pointer hover:opacity-90 transition-opacity"
        onClick={() => setExpanded(true)}
      />
      {expanded && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4"
          onClick={() => setExpanded(false)}
        >
          <img
            src={url}
            alt="Expanded"
            className="max-w-full max-h-full object-contain rounded-lg"
          />
        </div>
      )}
    </>
  );
}

function VideoPlayer({ video }: { video: { url: string; poster?: string } }) {
  return (
    <div className="relative max-w-[400px] rounded-lg overflow-hidden border border-ink-700">
      <video
        src={video.url}
        poster={video.poster}
        controls
        className="w-full"
        preload="metadata"
      >
        <source src={video.url} />
        Your browser does not support video playback.
      </video>
    </div>
  );
}

function AudioPlayer({ audio }: { audio: { url: string; duration?: number } }) {
  return (
    <div className="flex items-center gap-3 p-3 rounded-lg bg-ink-800/50 border border-ink-700 min-w-[250px]">
      <div className="w-10 h-10 rounded-full bg-moss/20 flex items-center justify-center">
        <Music className="w-5 h-5 text-moss" />
      </div>
      <audio src={audio.url} controls className="flex-1 h-8" preload="metadata">
        Your browser does not support audio playback.
      </audio>
    </div>
  );
}

function FileDownload({ file }: { file: { url: string; name: string; mime_type: string; size: number } }) {
  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const getIcon = (mimeType: string) => {
    if (mimeType.startsWith('video/')) return Film;
    if (mimeType.startsWith('audio/')) return Music;
    return FileText;
  };

  const Icon = getIcon(file.mime_type);

  return (
    <a
      href={file.url}
      download={file.name}
      className="flex items-center gap-3 p-3 rounded-lg bg-ink-800/50 border border-ink-700 hover:bg-ink-700/50 transition-colors"
    >
      <div className="w-10 h-10 rounded-lg bg-ink-700 flex items-center justify-center">
        <Icon className="w-5 h-5 text-ink-400" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-ink-200 truncate">{file.name}</p>
        <p className="text-xs text-ink-500">{formatSize(file.size)}</p>
      </div>
      <Download className="w-4 h-4 text-ink-400" />
    </a>
  );
}
```

### FR-7: Update Chat Store Default

```typescript
// ui/src/store/chat.ts

// Change default showReasoning to true (always show reasoning by default)
export const useChatStore = create<ChatStore>()(
  persist(
    (set, get) => ({
      // ... existing state ...
      showReasoning: true, // Changed from false to true

      // Remove toggleReasoning or keep for future settings panel
      // toggleReasoning: () => set((state) => ({ showReasoning: !state.showReasoning })),
    }),
    // ...
  )
);
```

## Visual Reference

### Before (Current State)

```
┌─────────────────────────────────────────────────────────────────┐
│  JANUS                              Home  Chat  Competition     │
├───────────────────┬─────────────────────────────────────────────┤
│ WORKSPACE         │  SESSION  New Chat     MODEL ▼  THINKING:OFF│
│ Janus Auto    [J] │                                             │
│                   │                                             │
│ [+ New Chat]      │         Where should we begin?              │
│ [Search chats]    │                                             │
│ [Library]         │         Powered by Chutes...                │
│ [Agents]          │                                             │
│ [Studio]          │                                             │
│ ───────────────── │                                             │
│ CHATS             │                                             │
│ • New Chat        │                                             │
│                   ├─────────────────────────────────────────────┤
│ Janus PoC         │  [+] Ask anything...           [🎤] [→]     │
└───────────────────┴─────────────────────────────────────────────┘
```

### After (Target State)

```
┌─────────────────────────────────────────────────────────────────┐
│  JANUS                              Home  Chat  Competition     │
├───────────────────┬─────────────────────────────────────────────┤
│ [🏠 Home]         │  SESSION  New Chat              MODEL ▼     │
│                   │                                             │
│ [+ New Chat]      │                                             │
│ [Search chats]    │         Where should we begin?              │
│ ───────────────── │                                             │
│ CHATS             │         Powered by Chutes...                │
│ • New Chat        │                                             │
│                   │                                             │
│                   │                                             │
│                   │                                             │
│ Janus PoC         ├─────────────────────────────────────────────┤
└───────────────────│  [+] Ask anything...           [🎤] [→]     │
                    └─────────────────────────────────────────────┘
```

### Mobile Portrait (375x812)

```
┌─────────────────────┐
│ JANUS           ≡   │
├─────────────────────┤
│ ≡ SESSION New Chat  │
│                     │
│                     │
│  Where should we    │
│     begin?          │
│                     │
│  Powered by Chutes  │
│                     │
│                     │
│                     │
│                     │
│                     │
├─────────────────────┤
│ [+] Ask anything... │
│           [🎤] [→]  │
└─────────────────────┘
```

Input bar should always be visible without scrolling on empty chat.

## Non-Functional Requirements

### NFR-1: Mobile Responsiveness

- Input bar always visible in viewport (no scrolling needed on empty chat)
- Use `dvh` (dynamic viewport height) for iOS Safari compatibility
- Touch-friendly tap targets (minimum 44x44px)

### NFR-2: Media Performance

- Lazy load videos and audio
- Use `preload="metadata"` for media
- Compress images before display if > 1MB
- Show loading skeleton while media loads

### NFR-3: Accessibility

- Video/audio controls accessible via keyboard
- Alt text for images
- File download links properly labeled
- ARIA labels for expanded image modal

## Acceptance Criteria

- [ ] "the intelligence engine" text removed from landing page
- [ ] "Thinking: On/Off" toggle removed from chat
- [ ] "Workspace / Janus Auto / J" section removed from sidebar
- [ ] "Library / Agents / Studio" buttons removed from sidebar
- [ ] Mobile portrait: input bar visible without scrolling
- [ ] Videos display with native controls
- [ ] Audio displays with player controls
- [ ] Files display with download link
- [ ] Images can be clicked to expand
- [ ] Works on iOS Safari (dvh units)
- [ ] Tests updated/passing

## Files to Modify

```
ui/src/
├── components/
│   ├── landing/
│   │   └── HeroSection.tsx       # MODIFY - Remove tagline
│   ├── ChatArea.tsx              # MODIFY - Remove thinking toggle, fix layout
│   ├── Sidebar.tsx               # MODIFY - Remove workspace header, placeholder buttons
│   ├── MessageBubble.tsx         # MODIFY - Use MediaRenderer
│   └── MediaRenderer.tsx         # NEW - Rich media display component
├── types/
│   └── chat.ts                   # MODIFY - Add video/audio/file content types
├── store/
│   └── chat.ts                   # MODIFY - Default showReasoning to true
└── app/
    └── globals.css               # MODIFY - Fix mobile viewport height
```

## Open Questions

1. **Reasoning default**: Should reasoning be shown by default, or hidden?
2. **Media size limits**: What's the max video/audio file size to display inline?
3. **Image lightbox**: Should expanded images have zoom/pan controls?
4. **Video autoplay**: Should videos autoplay (muted) or require click?

## Related Specs

- `specs/11_chat_ui.md` - Original chat UI spec
- `specs/37_extended_file_attachments.md` - File attachment handling
- `specs/39_speech_to_text_voice_input.md` - Voice input

NR_OF_TRIES: 1
