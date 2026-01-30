# Spec 128: Fix Mermaid Modal Infinite Loop

## Status: TODO

**Priority:** Critical
**Complexity:** Low
**Prerequisites:** None

---

## Problem Statement

On the competition page, clicking a Mermaid diagram causes an infinite loop:
1. Modal opens
2. Modal closes immediately
3. Modal opens again
4. Repeat infinitely

This makes the page unusable and requires closing the browser tab.

---

## Root Cause Analysis

Based on code review of `ui/src/components/MermaidDiagram.tsx`:

**Problem:** The `onClose` callback is created inline, causing React to recreate it on every render:

```tsx
// Line 268 - PROBLEMATIC
{showModal && (
  <MermaidDiagramModal
    svg={svg}
    ariaLabel={ariaLabel}
    onClose={() => setShowModal(false)}  // ← New function every render!
  />
)}
```

This causes the `useEffect` in `MermaidDiagramModal.tsx` (which depends on `onClose`) to re-run on every render, potentially triggering state updates that cause more renders.

**Additional potential issues:**
1. Click event bubbling from modal content to backdrop
2. Focus management triggering re-renders
3. Event listener cleanup/re-setup thrashing

---

## Implementation

### 1. Stabilize onClose Callback

**File:** `ui/src/components/MermaidDiagram.tsx`

Use `useCallback` to memoize the close handler:

```tsx
import { useState, useCallback } from 'react';

const MermaidDiagram = ({ chart, clickable = true, ariaLabel }: Props) => {
  const [showModal, setShowModal] = useState(false);

  // Stable callback reference
  const handleModalClose = useCallback(() => {
    setShowModal(false);
  }, []);

  const handleClick = useCallback(() => {
    if (clickable) {
      setShowModal(true);
    }
  }, [clickable]);

  // ...

  return (
    <>
      {/* diagram content */}
      {showModal && (
        <MermaidDiagramModal
          svg={svg}
          ariaLabel={ariaLabel}
          onClose={handleModalClose}  // ← Stable reference
        />
      )}
    </>
  );
};
```

### 2. Fix Event Propagation

**File:** `ui/src/components/MermaidDiagramModal.tsx`

Ensure clicks don't propagate incorrectly:

```tsx
const MermaidDiagramModal = ({ svg, ariaLabel, onClose }: Props) => {
  const closeButtonRef = useRef<HTMLButtonElement>(null);

  // Handle backdrop click - only close if clicking the backdrop itself
  const handleBackdropClick = useCallback((e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      e.stopPropagation();
      onClose();
    }
  }, [onClose]);

  // Handle content click - prevent propagation
  const handleContentClick = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
  }, []);

  return (
    <div
      className="mermaid-modal-backdrop"
      onClick={handleBackdropClick}
      role="dialog"
      aria-modal="true"
    >
      <div
        className="mermaid-modal-content"
        onClick={handleContentClick}
      >
        <button
          ref={closeButtonRef}
          onClick={(e) => {
            e.stopPropagation();
            onClose();
          }}
          className="mermaid-modal-close"
        >
          ✕
        </button>
        <div dangerouslySetInnerHTML={{ __html: svg }} />
      </div>
    </div>
  );
};
```

### 3. Stabilize useEffect Dependencies

**File:** `ui/src/components/MermaidDiagramModal.tsx`

Remove `onClose` from effect dependencies or use a ref:

```tsx
const MermaidDiagramModal = ({ svg, ariaLabel, onClose }: Props) => {
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const onCloseRef = useRef(onClose);

  // Keep ref updated
  useEffect(() => {
    onCloseRef.current = onClose;
  }, [onClose]);

  // Focus management - no dependencies that change
  useEffect(() => {
    closeButtonRef.current?.focus();
  }, []);

  // Escape key handler - use ref instead of dependency
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        onCloseRef.current();  // ← Use ref
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, []);  // ← Empty dependency array

  // Body overflow
  useEffect(() => {
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = '';
    };
  }, []);

  // ...
};
```

### 4. Add Render Loop Protection

As a safety measure, prevent rapid open/close cycles:

```tsx
const MermaidDiagram = ({ chart, clickable = true, ariaLabel }: Props) => {
  const [showModal, setShowModal] = useState(false);
  const lastToggleRef = useRef(0);

  const handleModalClose = useCallback(() => {
    const now = Date.now();
    // Debounce: ignore if toggled within 100ms
    if (now - lastToggleRef.current < 100) {
      console.warn('[MermaidDiagram] Rapid toggle detected, ignoring');
      return;
    }
    lastToggleRef.current = now;
    setShowModal(false);
  }, []);

  const handleClick = useCallback(() => {
    if (!clickable) return;

    const now = Date.now();
    if (now - lastToggleRef.current < 100) {
      console.warn('[MermaidDiagram] Rapid toggle detected, ignoring');
      return;
    }
    lastToggleRef.current = now;
    setShowModal(true);
  }, [clickable]);

  // ...
};
```

---

## Testing

1. Go to competition page
2. Click on any Mermaid diagram
3. Verify modal opens and stays open
4. Click backdrop or close button - modal should close once
5. Click diagram again - should open normally
6. Press Escape - modal should close once
7. No infinite loops, no console errors

---

## Acceptance Criteria

- [ ] Clicking diagram opens modal once
- [ ] Modal stays open until explicitly closed
- [ ] Clicking backdrop closes modal once
- [ ] Clicking close button closes modal once
- [ ] Pressing Escape closes modal once
- [ ] No infinite render loops
- [ ] No "Maximum update depth exceeded" errors
- [ ] Page remains responsive after modal interaction
