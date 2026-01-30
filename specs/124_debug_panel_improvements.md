# Spec 124: Debug Panel Improvements

## Status: COMPLETE

**Priority:** Medium
**Complexity:** Medium
**Prerequisites:** None

---

## Problem Statement

The debug mode panel in the chat UI has several usability issues:

1. **Mermaid diagram too large** - Only a small portion fits in the panel, making it hard to see the full flow
2. **Panel not resizable** - Users can't adjust the panel width to see more detail
3. **Panel not detachable** - Can't pop out as a separate window for multi-monitor workflows
4. **Flow path not displayed** - The diagram doesn't highlight the actual path the query took
5. **Events not showing** - Debug events are not appearing in the log section

**Test Case:** Query "Explain why the sky is blue." (request id: chatcmpl-502a917bcf0642f48722d13c) showed none of these features working correctly.

---

## Implementation

### 1. Scale Mermaid Diagram to Fit Panel

**File: `ui/src/components/debug/DebugFlowDiagram.tsx`**

Add SVG scaling to fit container:

```tsx
// Add container ref for size calculation
const containerRef = useRef<HTMLDivElement>(null);
const [scale, setScale] = useState(1);

// Calculate scale to fit diagram in container
useEffect(() => {
  if (!containerRef.current || !svg) return;

  const container = containerRef.current;
  const svgElement = container.querySelector('svg');
  if (!svgElement) return;

  const containerWidth = container.clientWidth - 24; // padding
  const containerHeight = container.clientHeight - 24;
  const svgWidth = svgElement.viewBox.baseVal.width || svgElement.clientWidth;
  const svgHeight = svgElement.viewBox.baseVal.height || svgElement.clientHeight;

  const scaleX = containerWidth / svgWidth;
  const scaleY = containerHeight / svgHeight;
  const newScale = Math.min(scaleX, scaleY, 1); // Don't scale up, only down

  setScale(newScale);
}, [svg]);

// Apply scale via CSS transform
<div
  ref={containerRef}
  className="chat-debug-diagram"
  style={{
    overflow: 'auto',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center'
  }}
>
  <div style={{ transform: `scale(${scale})`, transformOrigin: 'top center' }}>
    {/* SVG content */}
  </div>
</div>
```

**File: `ui/src/app/globals.css`**

```css
.chat-debug-diagram {
  flex: 1;
  min-height: 200px;
  max-height: 50vh;
  overflow: auto;
}

.chat-debug-diagram svg {
  max-width: 100%;
  height: auto;
}
```

### 2. Make Panel Resizable

**File: `ui/src/components/debug/DebugPanel.tsx`**

Add resize handle:

```tsx
import { useState, useCallback } from 'react';

const [panelWidth, setPanelWidth] = useState(420);
const [isResizing, setIsResizing] = useState(false);

const handleMouseDown = useCallback((e: React.MouseEvent) => {
  e.preventDefault();
  setIsResizing(true);

  const startX = e.clientX;
  const startWidth = panelWidth;

  const handleMouseMove = (e: MouseEvent) => {
    const delta = startX - e.clientX;
    const newWidth = Math.min(Math.max(startWidth + delta, 320), 800);
    setPanelWidth(newWidth);
  };

  const handleMouseUp = () => {
    setIsResizing(false);
    document.removeEventListener('mousemove', handleMouseMove);
    document.removeEventListener('mouseup', handleMouseUp);
  };

  document.addEventListener('mousemove', handleMouseMove);
  document.addEventListener('mouseup', handleMouseUp);
}, [panelWidth]);

// Render resize handle
<div
  className="debug-panel-resize-handle"
  onMouseDown={handleMouseDown}
/>
```

**CSS for resize handle:**
```css
.debug-panel-resize-handle {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  cursor: ew-resize;
  background: transparent;
  transition: background 0.2s;
}

.debug-panel-resize-handle:hover,
.debug-panel-resize-handle:active {
  background: rgba(99, 210, 151, 0.5);
}
```

### 3. Make Panel Detachable

Add pop-out button to header:

```tsx
const [isDetached, setIsDetached] = useState(false);
const detachedWindowRef = useRef<Window | null>(null);

const handleDetach = useCallback(() => {
  const width = 500;
  const height = 700;
  const left = window.screenX + window.innerWidth - width - 50;
  const top = window.screenY + 50;

  const popup = window.open(
    '',
    'JanusDebugPanel',
    `width=${width},height=${height},left=${left},top=${top},resizable=yes`
  );

  if (popup) {
    detachedWindowRef.current = popup;
    setIsDetached(true);

    // Render debug content into popup
    popup.document.write(`
      <!DOCTYPE html>
      <html>
        <head>
          <title>Janus Debug Panel</title>
          <style>/* Copy relevant styles */</style>
        </head>
        <body id="debug-root"></body>
      </html>
    `);

    // Use ReactDOM.createPortal or similar to render into popup
  }
}, []);

// Header button
<button
  onClick={handleDetach}
  className="debug-detach-btn"
  title="Open in new window"
>
  <ExternalLinkIcon />
</button>
```

### 4. Fix Flow Path Highlighting

**File: `ui/src/hooks/useDebug.ts`**

Ensure activeNodes is updated based on events:

```typescript
// Map event types to flow nodes
const EVENT_TO_NODE: Record<string, string[]> = {
  'request_received': ['request'],
  'complexity_check_start': ['complexity'],
  'complexity_check_keyword': ['keywords'],
  'complexity_check_llm': ['llm_verify'],
  'fast_path_start': ['fast_path'],
  'fast_path_llm_call': ['fast_path', 'direct_llm'],
  'agent_path_start': ['agent_path'],
  'sandbox_init': ['sandbox'],
  'sandy_agent_api_request': ['agent'],
  'tool_call_start': ['tools'],
  'response_chunk': ['response'],
};

// Update activeNodes when events arrive
const processEvent = (event: DebugEvent) => {
  const nodes = EVENT_TO_NODE[event.type] || [];
  if (nodes.length > 0) {
    setDebugState(prev => ({
      ...prev,
      activeNodes: [...new Set([...prev.activeNodes, ...nodes])],
      currentStep: event.step,
    }));
  }
};
```

### 5. Fix Events Not Showing

**File: `ui/src/hooks/useDebug.ts`**

Verify SSE connection and event parsing:

```typescript
useEffect(() => {
  if (!requestId || !isEnabled) return;

  const eventSource = new EventSource(
    `/api/debug/stream/${requestId}?baseline=${baseline}`
  );

  eventSource.onmessage = (e) => {
    try {
      const event = JSON.parse(e.data) as DebugEvent;
      console.log('[Debug] Event received:', event.type); // Debug logging

      setDebugState(prev => ({
        ...prev,
        events: [...prev.events, event],
      }));

      processEvent(event);
    } catch (err) {
      console.error('[Debug] Failed to parse event:', e.data, err);
    }
  };

  eventSource.onerror = (err) => {
    console.error('[Debug] SSE error:', err);
  };

  return () => eventSource.close();
}, [requestId, isEnabled, baseline]);
```

---

## Acceptance Criteria

- [x] Mermaid diagram scales to fit within panel bounds
- [x] Panel width is resizable via drag handle (320px - 800px)
- [x] Panel can be detached to a separate window
- [x] Flow path highlights nodes as request progresses
- [x] Debug events appear in the log section in real-time
- [x] All features work on desktop (1024px+)

---

## Testing

1. Enable debug mode, send "Explain why the sky is blue"
2. Verify diagram fits in panel without scrolling
3. Drag resize handle to change panel width
4. Click detach button, verify popup window works
5. Verify flow nodes highlight as request processes
6. Verify events appear in log with timestamps

---

<!-- NR_OF_TRIES: 1 -->
