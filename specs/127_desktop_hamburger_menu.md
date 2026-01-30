# Spec 127: Desktop Hamburger Menu Toggle

## Status: TODO

**Priority:** Low
**Complexity:** Low
**Prerequisites:** None

---

## Problem Statement

The hamburger menu button (☰) in the chat UI header, left of the "JANUS" title, does nothing on desktop. Currently:

- **Mobile (< 1024px):** Button is visible and opens sidebar as modal overlay
- **Desktop (≥ 1024px):** Button is hidden with `lg:hidden` CSS class

Users expect the hamburger button to toggle the sidebar expand/collapse on desktop, similar to many modern applications.

---

## Current Implementation

**File:** `ui/src/components/ChatArea.tsx` (lines 767-776)

```tsx
<button
  type="button"
  onClick={onMenuClick}
  className="chat-menu-btn lg:hidden"  // Hidden on desktop!
  aria-label="Open sidebar"
>
  {/* hamburger icon */}
</button>
```

**File:** `ui/src/app/chat/page.tsx`

- `sidebarOpen` state controls mobile modal
- `sidebarCollapsed` state controls desktop collapse (but no trigger from hamburger)

---

## Implementation

### 1. Show Hamburger on Desktop

**File:** `ui/src/components/ChatArea.tsx`

Remove `lg:hidden` and handle both mobile and desktop:

```tsx
<button
  type="button"
  onClick={onMenuClick}
  className="chat-menu-btn"  // Visible on all screen sizes
  aria-label={isDesktop ? "Toggle sidebar" : "Open sidebar"}
>
  <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="1.6">
    <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
  </svg>
</button>
```

### 2. Update Click Handler for Desktop

**File:** `ui/src/app/chat/page.tsx`

Modify `openSidebar` to handle both cases:

```tsx
import { useMediaQuery } from '@/hooks/useMediaQuery';

const ChatPage = () => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('sidebar-collapsed') === 'true';
    }
    return false;
  });

  const isDesktop = useMediaQuery('(min-width: 1024px)');

  // Unified handler for hamburger menu
  const handleMenuClick = useCallback(() => {
    if (isDesktop) {
      // Desktop: toggle collapse state
      setSidebarCollapsed(prev => {
        const newValue = !prev;
        localStorage.setItem('sidebar-collapsed', String(newValue));
        return newValue;
      });
    } else {
      // Mobile: open as modal
      setSidebarOpen(true);
    }
  }, [isDesktop]);

  return (
    // ...
    <ChatArea
      onMenuClick={handleMenuClick}
      // ...
    />
  );
};
```

### 3. Add useMediaQuery Hook (if not exists)

**File:** `ui/src/hooks/useMediaQuery.ts`

```typescript
import { useState, useEffect } from 'react';

export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(false);

  useEffect(() => {
    const media = window.matchMedia(query);

    // Set initial value
    setMatches(media.matches);

    // Listen for changes
    const listener = (e: MediaQueryListEvent) => setMatches(e.matches);
    media.addEventListener('change', listener);

    return () => media.removeEventListener('change', listener);
  }, [query]);

  return matches;
}
```

### 4. Update Button Styling

**File:** `ui/src/app/globals.css`

```css
.chat-menu-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: transparent;
  border: none;
  color: #9CA3AF;
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}

.chat-menu-btn:hover {
  background: rgba(99, 210, 151, 0.1);
  color: #63D297;
}

/* Touch-friendly on mobile */
@media (max-width: 1023px) {
  .chat-menu-btn {
    min-width: 44px;
    min-height: 44px;
  }
}
```

### 5. Add Visual Feedback for Collapse State

Optionally animate the hamburger icon to indicate state:

```tsx
<button
  type="button"
  onClick={onMenuClick}
  className={`chat-menu-btn ${sidebarCollapsed ? 'sidebar-collapsed' : ''}`}
  aria-label={isDesktop ? "Toggle sidebar" : "Open sidebar"}
  aria-expanded={isDesktop ? !sidebarCollapsed : sidebarOpen}
>
  <svg
    viewBox="0 0 24 24"
    className="w-4 h-4 transition-transform"
    style={{ transform: sidebarCollapsed ? 'rotate(90deg)' : 'none' }}
    fill="none"
    stroke="currentColor"
    strokeWidth="1.6"
  >
    <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
  </svg>
</button>
```

---

## Acceptance Criteria

- [ ] Hamburger button visible on desktop (≥ 1024px)
- [ ] Clicking on desktop toggles sidebar collapse/expand
- [ ] Clicking on mobile opens sidebar as modal (existing behavior)
- [ ] Collapse state persists in localStorage
- [ ] Visual feedback indicates current state
- [ ] Accessible: proper aria-label and aria-expanded

---

## Testing

1. **Desktop (≥ 1024px):**
   - Hamburger button visible
   - Click toggles sidebar width (collapsed ↔ expanded)
   - State persists on page reload

2. **Mobile (< 1024px):**
   - Hamburger button visible (larger touch target)
   - Click opens sidebar as modal overlay
   - Click outside closes sidebar

3. **Responsive:**
   - Resize window across 1024px breakpoint
   - Behavior switches appropriately
