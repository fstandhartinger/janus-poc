# Spec 105: Fix Mermaid Diagram Modal in Chat

## Status: COMPLETE

## Context / Why

The click-to-enlarge modal for mermaid diagrams in the chat UI is broken. There are two mermaid components:

1. **MermaidDiagram** (`components/MermaidDiagram.tsx`) - Has modal functionality, used on static pages
2. **DiagramBlock** (`components/viz/DiagramBlock.tsx`) - Used in chat markdown rendering, NO modal functionality

When users receive mermaid diagrams in chat responses, they cannot click to see them in a larger modal view.

## Root Cause

`DiagramBlock` was created separately and only implements download functionality, not the click-to-expand modal that `MermaidDiagram` has.

## Solution

Unify the components by adding modal functionality to `DiagramBlock` (or replace it with `MermaidDiagram`).

## Functional Requirements

### FR-1: Add Modal to DiagramBlock

```typescript
// ui/src/components/viz/DiagramBlock.tsx

'use client';

import { useEffect, useRef, useState } from 'react';
import mermaid from 'mermaid';
import { MermaidDiagramModal } from '../MermaidDiagramModal';

// ... existing mermaid init code ...

export function DiagramBlock({ code }: DiagramBlockProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [svg, setSvg] = useState('');
  const [showModal, setShowModal] = useState(false);  // ADD

  // ... existing render logic ...

  if (error) {
    // ... existing error handling ...
  }

  return (
    <>
      <div
        className="diagram-block cursor-pointer"
        role="img"
        aria-label="Mermaid diagram (click to enlarge)"
        onClick={() => setShowModal(true)}  // ADD
        onKeyDown={(e) => {                  // ADD
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            setShowModal(true);
          }
        }}
        tabIndex={0}                         // ADD
      >
        <div className="diagram-toolbar">
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();  // Prevent modal open
              downloadSVG();
            }}
            title="Download SVG"
          >
            <DownloadIcon /> SVG
          </button>
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              setShowModal(true);
            }}
            title="View fullscreen"
          >
            <ExpandIcon /> Expand
          </button>
        </div>
        <div
          ref={containerRef}
          className="diagram-content"
          dangerouslySetInnerHTML={{ __html: svg }}
        />
      </div>

      {/* ADD: Modal for fullscreen view */}
      {showModal && (
        <MermaidDiagramModal
          svg={svg}
          ariaLabel="Mermaid diagram fullscreen"
          onClose={() => setShowModal(false)}
        />
      )}
    </>
  );
}

function ExpandIcon() {
  return (
    <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7" />
    </svg>
  );
}
```

### FR-2: Add Visual Hint for Clickability

```css
/* In globals.css or component styles */

.diagram-block {
  position: relative;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
}

.diagram-block:hover {
  transform: scale(1.01);
  box-shadow: 0 0 20px rgba(99, 210, 151, 0.2);
}

.diagram-block:focus {
  outline: 2px solid #63D297;
  outline-offset: 4px;
}

/* Hint overlay on hover */
.diagram-block::after {
  content: 'Click to enlarge';
  position: absolute;
  bottom: 8px;
  right: 8px;
  padding: 4px 8px;
  background: rgba(0, 0, 0, 0.7);
  color: #fff;
  font-size: 12px;
  border-radius: 4px;
  opacity: 0;
  transition: opacity 0.2s;
  pointer-events: none;
}

.diagram-block:hover::after {
  opacity: 1;
}
```

### FR-3: Ensure Modal Renders Above Chat UI

The modal uses `z-50` which should be sufficient, but verify it renders above:
- Chat messages
- Sidebar
- Any other overlays

```typescript
// MermaidDiagramModal.tsx - verify z-index
<div
  className="fixed inset-0 z-[100] flex items-center justify-center ..."  // Increase if needed
  ...
>
```

## Testing

```typescript
// Manual testing checklist
// 1. Send a message that generates a mermaid diagram
// 2. Verify diagram renders in chat
// 3. Click on diagram - modal should open
// 4. Modal shows diagram at larger size
// 5. Press Escape or click outside - modal closes
// 6. Download button still works (doesn't open modal)
// 7. Expand button in toolbar opens modal
// 8. Keyboard accessible (Tab to diagram, Enter to open)
```

## Acceptance Criteria

- [ ] Clicking a mermaid diagram in chat opens fullscreen modal
- [ ] Modal shows diagram at larger readable size
- [ ] Escape key closes modal
- [ ] Click outside modal closes it
- [ ] Download button still works without opening modal
- [ ] Visual hover hint shows "Click to enlarge"
- [ ] Keyboard accessible (Tab + Enter)
- [ ] Modal renders above all other UI elements

## Files to Modify

```
ui/src/components/viz/DiagramBlock.tsx  # Add modal functionality
ui/src/app/globals.css                  # Add hover styles (if needed)
```

## Related Specs

- Spec 63: Mermaid Diagram Styling

NR_OF_TRIES: 0
