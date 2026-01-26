# Spec 109: Chat UI Mobile Responsive Improvements

## Status: TODO

**Priority:** High
**Complexity:** Medium
**Prerequisites:** None

---

## Problem Statement

The chat page topbar contains too many elements that don't fit well on mobile portrait mode (375px - 428px width). Currently the topbar includes:

**Left side:**
- Menu button (hamburger)
- New chat button (when sidebar collapsed)
- Home button
- "Session" label
- Session title

**Right side:**
- Sign in button (unauthenticated)
- Free chats counter "X/5 free chats remaining" (unauthenticated)
- User menu (authenticated)
- Debug toggle
- Memory toggle
- Model selector dropdown

On mobile screens (<640px), this causes:
- Horizontal overflow
- Elements getting squished
- Text truncation that's too aggressive
- Poor touch targets
- Cluttered, overwhelming UI

---

## Goals

1. Make the chat topbar fully usable on mobile portrait (375px width)
2. Prioritize essential controls, hide secondary ones on narrow screens
3. Maintain all functionality accessible (via menus/collapsed states)
4. Ensure touch targets are at least 44px for accessibility
5. No horizontal scrolling on the topbar

---

## Design Decisions

### Priority of Elements (What to Show on Mobile)

| Priority | Element | Mobile Behavior |
|----------|---------|-----------------|
| 1 | Menu button | Always visible |
| 2 | Model selector | Always visible (compact) |
| 3 | Sign in / User menu | Always visible (compact) |
| 4 | Home button | Hide on mobile, accessible via sidebar |
| 5 | Session title | Truncate aggressively or hide |
| 6 | "Session" label | Hide on mobile |
| 7 | Free chats counter | Hide on mobile (show in menu or below input) |
| 8 | Debug toggle | Move to overflow menu |
| 9 | Memory toggle | Move to overflow menu |
| 10 | New chat button | Keep in sidebar only |

---

## Implementation

### 1. Responsive CSS Updates

```css
/* ui/src/app/globals.css */

/* Mobile-first topbar improvements */
@media (max-width: 639px) {
  .chat-topbar {
    padding: 12px 16px;
    gap: 8px;
  }

  .chat-topbar-left {
    gap: 8px;
    flex: 1;
    min-width: 0;
  }

  .chat-topbar-right {
    gap: 8px;
    flex-shrink: 0;
  }

  /* Hide home button on mobile - accessible via sidebar */
  .chat-home-btn {
    display: none;
  }

  /* Hide "Session" label on mobile */
  .chat-context {
    display: none;
  }

  /* Aggressive truncation for session title */
  .chat-session-title {
    max-width: 100px;
    font-size: 13px;
  }

  /* Hide free chats counter on mobile - show elsewhere */
  .chat-free-count {
    display: none;
  }

  /* Smaller buttons on mobile */
  .chat-menu-btn,
  .chat-home-btn,
  .chat-new-chat-btn {
    width: 32px;
    height: 32px;
    border-radius: 10px;
  }

  /* Compact sign-in button */
  .chat-signin-btn {
    padding: 5px 10px;
    font-size: 11px;
  }

  /* Compact model selector */
  .chat-model-dropdown {
    max-width: 120px;
    font-size: 11px;
    padding: 5px 8px;
  }

  /* Hide debug and memory toggles - move to overflow menu */
  .chat-debug-toggle,
  .chat-memory-toggle {
    display: none;
  }

  /* Show overflow menu button */
  .chat-overflow-menu-btn {
    display: flex;
  }
}

/* Tablet and up - show everything */
@media (min-width: 640px) {
  .chat-overflow-menu-btn {
    display: none;
  }
}

/* Extra small screens (< 375px) */
@media (max-width: 374px) {
  .chat-topbar {
    padding: 10px 12px;
  }

  .chat-session-title {
    display: none;
  }

  .chat-model-dropdown {
    max-width: 90px;
  }
}
```

### 2. Add Overflow Menu Component

Create a new overflow menu that contains hidden controls on mobile:

```tsx
// ui/src/components/ChatOverflowMenu.tsx

'use client';

import { useState, useRef, useEffect } from 'react';
import { MoreHorizontal, Bug, Brain, Home, Hash } from 'lucide-react';

interface ChatOverflowMenuProps {
  debugEnabled: boolean;
  onDebugChange: (enabled: boolean) => void;
  memoryEnabled: boolean;
  onMemoryToggle: () => void;
  freeChatsRemaining?: number;
  freeChatsLimit?: number;
  showFreeChats?: boolean;
}

export function ChatOverflowMenu({
  debugEnabled,
  onDebugChange,
  memoryEnabled,
  onMemoryToggle,
  freeChatsRemaining,
  freeChatsLimit,
  showFreeChats,
}: ChatOverflowMenuProps) {
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Close on click outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    if (open) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [open]);

  return (
    <div ref={menuRef} className="chat-overflow-menu-btn relative sm:hidden">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="w-8 h-8 rounded-lg border border-ink-700 flex items-center justify-center text-ink-400 hover:text-ink-200 hover:border-ink-500 transition-colors"
        aria-label="More options"
        aria-expanded={open}
      >
        <MoreHorizontal className="w-4 h-4" />
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-2 w-56 bg-ink-900/95 border border-ink-700 rounded-xl p-2 shadow-xl z-50">
          {/* Free chats info */}
          {showFreeChats && freeChatsRemaining !== undefined && (
            <div className="px-3 py-2 text-xs text-ink-400 border-b border-ink-700 mb-2">
              <Hash className="w-3 h-3 inline mr-1" />
              {freeChatsRemaining}/{freeChatsLimit} free chats remaining
            </div>
          )}

          {/* Debug toggle */}
          <button
            type="button"
            onClick={() => {
              onDebugChange(!debugEnabled);
              setOpen(false);
            }}
            className="w-full flex items-center gap-3 px-3 py-2 text-sm text-ink-300 hover:text-ink-100 hover:bg-ink-800 rounded-lg transition-colors"
          >
            <Bug className="w-4 h-4" />
            <span>Debug mode</span>
            <span className={`ml-auto text-xs ${debugEnabled ? 'text-moss' : 'text-ink-500'}`}>
              {debugEnabled ? 'ON' : 'OFF'}
            </span>
          </button>

          {/* Memory toggle */}
          <button
            type="button"
            onClick={() => {
              onMemoryToggle();
              setOpen(false);
            }}
            className="w-full flex items-center gap-3 px-3 py-2 text-sm text-ink-300 hover:text-ink-100 hover:bg-ink-800 rounded-lg transition-colors"
          >
            <Brain className="w-4 h-4" />
            <span>Memory</span>
            <span className={`ml-auto text-xs ${memoryEnabled ? 'text-moss' : 'text-ink-500'}`}>
              {memoryEnabled ? 'ON' : 'OFF'}
            </span>
          </button>

          {/* Home link - hidden on mobile topbar */}
          <a
            href="/"
            className="w-full flex items-center gap-3 px-3 py-2 text-sm text-ink-300 hover:text-ink-100 hover:bg-ink-800 rounded-lg transition-colors"
            onClick={() => setOpen(false)}
          >
            <Home className="w-4 h-4" />
            <span>Go to home</span>
          </a>
        </div>
      )}
    </div>
  );
}
```

### 3. Update ChatArea.tsx

Integrate the overflow menu and adjust responsive visibility:

```tsx
// In ChatArea.tsx, update the topbar-right section:

<div className="chat-topbar-right">
  <div className="chat-auth">
    {!authLoading && !isAuthenticated && (
      <>
        <button type="button" className="chat-signin-btn" onClick={() => signIn()}>
          Sign in
        </button>
        {/* Only show on desktop */}
        <div className="chat-free-count hidden sm:block">
          {freeChatsRemaining}/{FREE_CHAT_LIMIT} free
        </div>
      </>
    )}
    {isAuthenticated && user && (
      <UserMenu userId={user.userId} username={user.username} onSignOut={signOut} />
    )}
  </div>

  {/* Desktop: show individual toggles */}
  <div className="hidden sm:flex items-center gap-3">
    <DebugToggle enabled={debugEnabled} onToggle={onDebugChange} />
    <MemoryToggle
      enabled={memoryEnabled}
      onOpen={() => setMemorySheetOpen(true)}
      open={memorySheetOpen}
    />
  </div>

  {/* Mobile: overflow menu with toggles */}
  <ChatOverflowMenu
    debugEnabled={debugEnabled}
    onDebugChange={onDebugChange}
    memoryEnabled={memoryEnabled}
    onMemoryToggle={() => setMemorySheetOpen(true)}
    freeChatsRemaining={freeChatsRemaining}
    freeChatsLimit={FREE_CHAT_LIMIT}
    showFreeChats={!isAuthenticated}
  />

  {/* Model selector - always visible but compact on mobile */}
  <ModelSelector
    models={models.length ? models : [{ id: 'baseline-cli-agent', object: 'model', created: 0, owned_by: 'janus' }]}
    selectedModel={selectedModel}
    onSelect={setSelectedModel}
  />
</div>
```

### 4. Show Free Chats Above Input (Mobile Alternative)

For unauthenticated users on mobile, show the free chat count above the input instead:

```tsx
// In ChatInput.tsx or ChatArea.tsx, above the input on mobile:

{!isAuthenticated && (
  <div className="sm:hidden text-center text-xs text-ink-500 mb-2">
    {freeChatsRemaining}/{FREE_CHAT_LIMIT} free chats remaining today
  </div>
)}
```

### 5. Update Model Selector for Mobile

Make the model selector more compact on mobile:

```css
/* ModelSelector responsive styles */
.chat-model-dropdown {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 999px;
  border: 1px solid rgba(31, 41, 55, 0.8);
  background: rgba(17, 23, 38, 0.7);
  color: #D1D5DB;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
}

@media (max-width: 639px) {
  .chat-model-dropdown {
    padding: 5px 8px;
    font-size: 11px;
    gap: 4px;
  }

  .chat-model-dropdown .model-name {
    max-width: 80px;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .chat-model-dropdown .model-chevron {
    width: 14px;
    height: 14px;
  }
}
```

### 6. Touch Target Sizing

Ensure all interactive elements meet minimum 44px touch target:

```css
/* Minimum touch targets on mobile */
@media (max-width: 639px) {
  .chat-menu-btn,
  .chat-home-btn,
  .chat-new-chat-btn,
  .chat-overflow-menu-btn button {
    min-width: 44px;
    min-height: 44px;
  }

  .chat-signin-btn {
    min-height: 36px;
    padding: 8px 12px;
  }

  .chat-model-dropdown {
    min-height: 36px;
  }
}
```

---

## Acceptance Criteria

### Must Have
- [ ] No horizontal overflow on 375px width screens
- [ ] All essential controls (menu, model, sign-in) accessible on mobile
- [ ] Touch targets are at least 44px on mobile
- [ ] Free chats counter hidden on mobile (shown elsewhere)
- [ ] "Session" label hidden on mobile
- [ ] Home button hidden on mobile (accessible via sidebar)

### Should Have
- [ ] Overflow menu contains debug/memory toggles on mobile
- [ ] Free chats shown above input area on mobile
- [ ] Model selector shows truncated model name on mobile
- [ ] Smooth transitions when resizing

### Nice to Have
- [ ] Animated overflow menu open/close
- [ ] Haptic feedback on mobile interactions
- [ ] Swipe gestures to access sidebar

---

## Visual Testing Checklist

Test on these viewports:
- [ ] iPhone SE (375x667)
- [ ] iPhone 14 (390x844)
- [ ] iPhone 14 Pro Max (428x926)
- [ ] iPad Mini (768x1024) portrait
- [ ] Desktop (1920x1080)

For each viewport verify:
- [ ] No horizontal scroll
- [ ] All buttons are tappable
- [ ] Text is readable (not too small)
- [ ] No overlapping elements
- [ ] Consistent with dark theme

---

## Files to Modify

```
ui/
├── src/
│   ├── app/
│   │   └── globals.css                    # MODIFY - Add responsive styles
│   └── components/
│       ├── ChatArea.tsx                   # MODIFY - Integrate overflow menu
│       ├── ChatOverflowMenu.tsx           # NEW - Mobile overflow menu
│       ├── ChatInput.tsx                  # MODIFY - Show free chats on mobile
│       └── ModelSelector.tsx              # MODIFY - Compact mobile variant
```

---

## Testing Commands

```bash
# Run visual tests on mobile viewports
cd ui && npx playwright test e2e/visual/responsive.visual.spec.ts --project="Mobile"

# Manual testing - run dev server and use browser DevTools
npm run dev
# Then: Chrome DevTools > Toggle Device Toolbar > iPhone 14
```

---

## Related Specs

- `specs/88_chat_ui_improvements.md` - Previous chat UI work
- `specs/82_chat_ui_polish.md` - Chat polish items
- `specs/107_e2e_browser_automation_testing.md` - E2E tests
- `specs/108_visual_regression_testing.md` - Visual tests

NR_OF_TRIES: 0
