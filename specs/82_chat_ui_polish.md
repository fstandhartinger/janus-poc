# Spec 82: Chat UI Polish & Improvements

**Status:** NOT STARTED
**Priority:** High
**Complexity:** Medium
**Prerequisites:** None

---

## Overview

Polish the chat UI with several improvements:
1. Fix TTS voice selector icon (microphone → speaker/person)
2. Hide useless "Thinking" section showing only "Processing request..."
3. Improve streaming response visual feedback
4. Fix chat input textarea vertical positioning issues
5. General response display improvements

---

## Functional Requirements

### FR-1: Fix TTS Voice Selector Icon

**Problem:** The voice selector uses a microphone icon which suggests voice INPUT (recording), not OUTPUT (speaking).

**Solution:** Replace with a speaker icon or person-speaking icon.

```tsx
// components/TTSPlayer.tsx

// Option A: Speaker with sound waves
function VoiceIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      className="w-4 h-4"
    >
      <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
      <path d="M15.54 8.46a5 5 0 0 1 0 7.07" />
      <path d="M19.07 4.93a10 10 0 0 1 0 14.14" />
    </svg>
  );
}

// Option B: Person speaking (recommended)
function VoiceIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="w-4 h-4"
    >
      {/* Head */}
      <circle cx="9" cy="7" r="4" />
      {/* Body */}
      <path d="M3 21v-2a4 4 0 0 1 4-4h4a4 4 0 0 1 4 4v2" />
      {/* Speech waves */}
      <path d="M17 8l2 2-2 2" />
      <path d="M20 6l2 2-2 2" />
    </svg>
  );
}
```

**Alternative:** Move voice selection to a settings panel instead of showing in every message. Add a global TTS settings button in header/settings.

### FR-2: Hide Useless Thinking Section

**Problem:** The "Thinking" panel shows only "Processing request..." which adds no value.

**Solution:** Only show reasoning_content if it contains meaningful content beyond generic status messages.

```tsx
// components/MessageBubble.tsx

// Filter out generic/useless reasoning content
const USELESS_REASONING_PATTERNS = [
  /^processing\s*(request|\.{2,})?$/i,
  /^thinking\.{2,}$/i,
  /^working\.{2,}$/i,
  /^loading\.{2,}$/i,
];

function isUsefulReasoning(content: string | undefined): boolean {
  if (!content) return false;
  const trimmed = content.trim();
  if (trimmed.length < 20) return false;  // Too short to be useful
  return !USELESS_REASONING_PATTERNS.some(pattern => pattern.test(trimmed));
}

// In MessageBubble component:
const hasUsefulReasoning = showReasoning && isUsefulReasoning(message.reasoning_content);

{hasUsefulReasoning && (
  <div className="mb-3 p-3 rounded-lg text-sm border border-[#1F2937] bg-[#111726]/70">
    <div className="text-[11px] uppercase tracking-[0.2em] text-[#F59E0B] font-semibold mb-2">
      Thinking
    </div>
    <div className="text-[#D1D5DB] whitespace-pre-wrap">
      {message.reasoning_content}
    </div>
  </div>
)}
```

### FR-3: Improve Streaming Response Visual Feedback

**Problem:** During streaming, it's not visually clear that more content is coming.

**Solution:** Add visual indicators to the message bubble itself.

```tsx
// components/MessageBubble.tsx

interface MessageBubbleProps {
  message: Message;
  showReasoning: boolean;
  isStreaming?: boolean;  // NEW: indicates this message is still streaming
}

export function MessageBubble({ message, showReasoning, isStreaming }: MessageBubbleProps) {
  // ... existing code ...

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      <div
        className={cn(
          "chat-message max-w-[80%]",
          isUser ? 'chat-message-user' : 'chat-message-assistant',
          isStreaming && 'chat-message-streaming'
        )}
      >
        {/* ... message content ... */}

        {/* Streaming indicator at bottom of message */}
        {isStreaming && !isUser && (
          <div className="streaming-indicator mt-3 flex items-center gap-2 text-xs text-gray-400">
            <span className="streaming-dots">
              <span className="dot" />
              <span className="dot" />
              <span className="dot" />
            </span>
            <span>Generating...</span>
          </div>
        )}
      </div>
    </div>
  );
}
```

**CSS for streaming indicator:**
```css
/* globals.css */

.chat-message-streaming {
  border-color: rgba(99, 210, 151, 0.3);
  animation: pulse-border 2s ease-in-out infinite;
}

@keyframes pulse-border {
  0%, 100% { border-color: rgba(99, 210, 151, 0.2); }
  50% { border-color: rgba(99, 210, 151, 0.5); }
}

.streaming-indicator {
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  padding-top: 0.75rem;
}

.streaming-dots {
  display: flex;
  gap: 4px;
}

.streaming-dots .dot {
  width: 6px;
  height: 6px;
  background: #63D297;
  border-radius: 50%;
  animation: bounce 1.4s ease-in-out infinite;
}

.streaming-dots .dot:nth-child(1) { animation-delay: 0s; }
.streaming-dots .dot:nth-child(2) { animation-delay: 0.2s; }
.streaming-dots .dot:nth-child(3) { animation-delay: 0.4s; }

@keyframes bounce {
  0%, 80%, 100% { transform: translateY(0); opacity: 0.4; }
  40% { transform: translateY(-4px); opacity: 1; }
}
```

### FR-4: Fix Chat Input Textarea Positioning

**Problem:** The chat input textarea sometimes floats in the middle of the viewport instead of being anchored to the bottom. This happens when:
- Content doesn't fill the viewport
- Flex layout doesn't properly stretch

**Solution:** Ensure proper flex layout with sticky positioning.

```tsx
// components/ChatArea.tsx

export function ChatArea({ onMenuClick }: ChatAreaProps) {
  // ... existing code ...

  return (
    <div className="chat-area flex flex-col h-full">
      {/* Canvas panel */}
      <CanvasPanel onAIEdit={handleAIEdit} disabled={isStreaming} />

      {/* Top bar - fixed height */}
      <div className="chat-topbar shrink-0">
        {/* ... topbar content ... */}
      </div>

      {/* Messages area - takes remaining space, scrollable */}
      <div className="flex-1 overflow-y-auto min-h-0">
        <div className="max-w-4xl mx-auto px-6 py-6 min-h-full flex flex-col">
          {/* Research/Screenshot components */}
          <DeepResearchProgress stages={researchStages} isActive={researchActive} />
          <ScreenshotStream screenshots={screenshots} isLive={screenshotsLive} />

          {/* Messages or empty state */}
          {messages.length === 0 ? (
            <div className="flex-1 flex items-center justify-center">
              <div className="chat-empty text-center">
                <p className="chat-empty-title">Where should we begin?</p>
                <p className="chat-empty-subtitle">
                  Powered by Chutes. The world's open-source decentralized AI compute platform.
                </p>
              </div>
            </div>
          ) : (
            <div className="flex-1">
              {messages.map((message, index) => (
                <MessageBubble
                  key={message.id}
                  message={message}
                  showReasoning={showReasoning}
                  isStreaming={isStreaming && index === messages.length - 1 && message.role === 'assistant'}
                />
              ))}
              <div ref={messagesEndRef} />
            </div>
          )}

          {/* Streaming status bar */}
          {isStreaming && (
            <div className="chat-streaming shrink-0 mt-4">
              <span className="chat-streaming-dot" />
              <span>{researchActive ? 'Running deep research' : 'Generating response'}</span>
              <button onClick={handleCancel} className="chat-cancel">
                Stop
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Input area - always at bottom */}
      <div className="shrink-0 border-t border-white/5 bg-[#0a0a0f]/80 backdrop-blur-sm">
        <div className="max-w-4xl mx-auto px-6 py-4">
          <ChatInput onSend={handleSend} disabled={isStreaming} />
        </div>
      </div>
    </div>
  );
}
```

**CSS fix:**
```css
/* globals.css */

.chat-area {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;  /* Important for flex children */
}

/* Ensure the page container has proper height */
.chat-page {
  height: 100vh;
  height: 100dvh;  /* Dynamic viewport height for mobile */
  display: flex;
  flex-direction: column;
}

/* Input container should always be visible */
.chat-input-container {
  position: sticky;
  bottom: 0;
  background: linear-gradient(to top, #0a0a0f 80%, transparent);
  padding-top: 1rem;
}
```

### FR-5: General Response Display Improvements

**5a. Better empty message handling:**
```tsx
// Don't show empty assistant bubbles
{messages.map((message, index) => {
  // Skip rendering empty assistant messages during streaming setup
  if (
    message.role === 'assistant' &&
    !message.content &&
    !message.reasoning_content &&
    isStreaming &&
    index === messages.length - 1
  ) {
    return null;
  }
  return <MessageBubble key={message.id} message={message} />;
})}
```

**5b. Better loading state before content arrives:**
```tsx
// components/MessageBubble.tsx
{!isUser && !hasText && !hasAudio && isStreaming && (
  <div className="flex items-center gap-2 text-gray-400 text-sm py-2">
    <div className="typing-indicator">
      <span /><span /><span />
    </div>
    <span>Thinking...</span>
  </div>
)}
```

**5c. Smooth content appearance:**
```css
.chat-message-assistant {
  animation: message-appear 0.3s ease-out;
}

@keyframes message-appear {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
```

**5d. Better code block styling during streaming:**
```css
/* Prevent layout shift during code block streaming */
.prose pre {
  min-height: 2.5rem;
  transition: min-height 0.2s ease-out;
}
```

---

## Files to Modify

| File | Changes |
|------|---------|
| `ui/src/components/TTSPlayer.tsx` | Replace VoiceIcon with speaker/person icon |
| `ui/src/components/MessageBubble.tsx` | Filter useless reasoning, add streaming indicator |
| `ui/src/components/ChatArea.tsx` | Fix layout, pass isStreaming to messages |
| `ui/src/app/globals.css` | Streaming animations, layout fixes |
| `ui/src/app/chat/page.tsx` | Ensure proper height container |

---

## Acceptance Criteria

- [ ] Voice selector icon shows speaker/person, not microphone
- [ ] "Thinking" section hidden when content is just "Processing request..."
- [ ] Streaming messages have visual indicator (pulsing border, dots)
- [ ] Chat input is always anchored to bottom of viewport
- [ ] Chat input is always visible (never below fold)
- [ ] Empty assistant messages don't show during initial streaming
- [ ] Messages appear with smooth animation
- [ ] No layout shift during streaming

---

## Testing Checklist

- [ ] TTS voice selector has appropriate icon
- [ ] Reasoning panel hidden for generic "Processing..." messages
- [ ] Reasoning panel shown for actual reasoning content
- [ ] During streaming, message bubble has pulsing border
- [ ] During streaming, "Generating..." indicator shows
- [ ] After streaming ends, indicator disappears
- [ ] Chat input stays at bottom with few messages
- [ ] Chat input stays at bottom with many messages
- [ ] Chat input visible on mobile viewports
- [ ] Empty state centers vertically
- [ ] Long responses don't push input off screen

---

## Visual Reference

### Current Issue (from screenshot)
```
┌────────────────────────────────────┐
│  Header                            │
├────────────────────────────────────┤
│                                    │
│  [Response bubble in middle]       │
│                                    │
│  [Input floating in middle] ← BAD  │
│                                    │
│                                    │
│                                    │
└────────────────────────────────────┘
```

### Fixed Layout
```
┌────────────────────────────────────┐
│  Header                            │
├────────────────────────────────────┤
│                                    │
│  [Response bubble]                 │
│                                    │
│  (scrollable area)                 │
│                                    │
├────────────────────────────────────┤
│  [Input always at bottom] ← GOOD   │
└────────────────────────────────────┘
```

### Streaming Message
```
┌────────────────────────────────────┐
│  Here's what I found about...      │
│                                    │
│  The answer involves several       │
│  key points:                       │
│  1. First...                       │
│  2. Second...█                     │
│                                    │
│  ─────────────────────────────     │
│  ● ● ● Generating...               │
└────────────────────────────────────┘
  ↑ Pulsing green border
```

---

## Notes

- Voice selector icon change is cosmetic but important for UX clarity
- Filtering "Processing request..." improves perceived responsiveness
- Streaming indicators help users understand the system is working
- Layout fix is critical - input must ALWAYS be accessible
- Consider adding settings panel for TTS preferences in future
