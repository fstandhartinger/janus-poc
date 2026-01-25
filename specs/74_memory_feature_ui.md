# Spec 74: Memory Feature UI Integration

## Status: COMPLETE
**Priority:** High
**Complexity:** Low
**Prerequisites:** Spec 72, Spec 73

---

## Overview

Integrate the memory feature into the Janus UI. This includes:
1. Generating and storing a unique user ID in localStorage
2. Sending `user_id` and `enable_memory=true` with chat requests
3. Optional: UI toggle to enable/disable memory feature

---

## Functional Requirements

### FR-1: User ID Generation and Storage

Generate a unique user ID on first visit and store in localStorage.

**Location:** `ui/src/lib/userId.ts`

```typescript
const USER_ID_STORAGE_KEY = 'janus_user_id';

export function getUserId(): string {
  if (typeof window === 'undefined') {
    return '';  // SSR fallback
  }

  let userId = localStorage.getItem(USER_ID_STORAGE_KEY);

  if (!userId) {
    // Generate UUID v4
    userId = crypto.randomUUID();
    localStorage.setItem(USER_ID_STORAGE_KEY, userId);
  }

  return userId;
}

export function clearUserId(): void {
  localStorage.removeItem(USER_ID_STORAGE_KEY);
}
```

### FR-2: Memory Toggle State

Store memory preference in localStorage.

**Location:** `ui/src/lib/memory.ts`

```typescript
const MEMORY_ENABLED_KEY = 'janus_memory_enabled';

export function isMemoryEnabled(): boolean {
  if (typeof window === 'undefined') {
    return false;
  }
  return localStorage.getItem(MEMORY_ENABLED_KEY) !== 'false';  // Default true
}

export function setMemoryEnabled(enabled: boolean): void {
  localStorage.setItem(MEMORY_ENABLED_KEY, enabled ? 'true' : 'false');
}
```

### FR-3: Send Memory Parameters with Chat Requests

Update the chat request to include `user_id` and `enable_memory`.

**Modify:** `ui/src/app/api/chat/route.ts` (gateway proxy) or the client-side fetch

**Request body modification:**
```typescript
const chatRequest = {
  model: selectedModel,
  messages: formattedMessages,
  stream: true,
  user_id: getUserId(),
  enable_memory: isMemoryEnabled(),
};
```

### FR-4: Memory Settings UI (Optional Toggle)

Add a toggle in the settings/header area to enable/disable memory.

**Option A: In Chat Header**
- Small brain icon with tooltip "Memory enabled/disabled"
- Click toggles the state
- Visual indicator (icon color) shows current state

**Option B: In Settings Modal**
- "Enable conversation memory" toggle
- Description: "Remember important things from past conversations"

**Recommended:** Option A for discoverability

```tsx
// components/MemoryToggle.tsx
import { Brain, BrainOff } from 'lucide-react';
import { isMemoryEnabled, setMemoryEnabled } from '@/lib/memory';
import { useState, useEffect } from 'react';

export function MemoryToggle() {
  const [enabled, setEnabled] = useState(true);

  useEffect(() => {
    setEnabled(isMemoryEnabled());
  }, []);

  const toggle = () => {
    const newState = !enabled;
    setEnabled(newState);
    setMemoryEnabled(newState);
  };

  return (
    <button
      onClick={toggle}
      className={cn(
        "p-2 rounded-lg transition-colors",
        enabled
          ? "text-moss-500 bg-moss-500/10 hover:bg-moss-500/20"
          : "text-gray-400 hover:text-gray-300"
      )}
      title={enabled ? "Memory enabled" : "Memory disabled"}
    >
      {enabled ? <Brain className="w-5 h-5" /> : <BrainOff className="w-5 h-5" />}
    </button>
  );
}
```

### FR-5: Memory Indicator in Chat

When memory is enabled and memories were used, show a subtle indicator.

**Option:** Small badge/icon on messages that had memory context injected.

This requires the backend to return metadata about memory usage, which can be added in a future enhancement.

---

## Technical Requirements

### TR-1: Files to Create

| File | Purpose |
|------|---------|
| `ui/src/lib/userId.ts` | User ID generation and storage |
| `ui/src/lib/memory.ts` | Memory preference storage |
| `ui/src/components/MemoryToggle.tsx` | Memory toggle button component |

### TR-2: Files to Modify

| File | Changes |
|------|---------|
| `ui/src/app/chat/page.tsx` | Pass memory params to chat |
| `ui/src/components/ChatArea.tsx` | Add MemoryToggle to header |
| `ui/src/app/api/chat/route.ts` | Forward memory params |
| `ui/src/hooks/useChat.ts` | Include memory params in requests |

### TR-3: Gateway Proxy Changes

If chat goes through the gateway, ensure it forwards `user_id` and `enable_memory`:

```python
# gateway/janus_gateway/routers/chat.py
@router.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    # Forward to baseline including user_id and enable_memory
    payload = request.model_dump()
    # These are already in the payload if sent by UI
```

---

## UI/UX Design

### Memory Toggle Button

**Location:** Chat header, next to model selector or settings

**States:**
1. **Enabled (default):** Moss green brain icon, subtle glow
2. **Disabled:** Gray brain icon with slash

**Tooltip:**
- Enabled: "Memory enabled - I'll remember important things"
- Disabled: "Memory disabled - conversations are not remembered"

### Memory Badge (Future Enhancement)

When a response used memory context:
- Small brain icon badge on the message
- Hover shows: "Used memories: X relevant memories referenced"

---

## Acceptance Criteria

- [ ] User ID is generated on first visit and persisted
- [ ] User ID is the same across browser sessions (until cleared)
- [ ] `user_id` and `enable_memory` sent with every chat request
- [ ] Memory toggle UI works correctly
- [ ] Toggle state persists across sessions
- [ ] Default memory state is `true` (enabled)
- [ ] No errors when localStorage unavailable (SSR, incognito)

---

## Testing Checklist

- [ ] First visit generates new user ID
- [ ] Subsequent visits use same user ID
- [ ] User ID is valid UUID format
- [ ] Memory toggle switches state correctly
- [ ] Toggle state persists after page refresh
- [ ] Chat requests include `user_id` (check Network tab)
- [ ] Chat requests include `enable_memory` (check Network tab)
- [ ] Toggle visual state matches actual state
- [ ] Works in incognito mode (generates new ID)

---

## Notes

- User ID is generated client-side to work without authentication
- Once Sign in with Chutes is implemented (Spec 75), the user ID will come from the authenticated user's `sub` claim
- Memory is enabled by default to encourage usage
- Users can disable memory for privacy-sensitive conversations
- In incognito mode, a new user ID is generated each session (expected behavior)

NR_OF_TRIES: 2
