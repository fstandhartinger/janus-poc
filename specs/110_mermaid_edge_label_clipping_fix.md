# Spec 110: Fix Mermaid Diagram Edge Label Clipping

## Status: TODO

**Priority:** Medium
**Complexity:** Low
**Prerequisites:** None

---

## Problem Statement

On the competition page's "How It Works" / Architecture Overview section, the Mermaid diagrams have edge labels (text on arrows) that are only partially rendered - they appear cut off or clipped. This affects:

1. **Sequence Diagram** (`serviceSequenceDiagram`) - Message labels like:
   - `Search for "quantum entanglement"`
   - `Fetch https://physics.org/quantum`
   - `Call DeepSeek-V3.2 for synthesis`
   - `Execute Python visualization`

2. **Flowchart Diagrams** - Edge labels with `|text|` syntax

The edge labels are crucial for understanding the flow and should be fully visible.

---

## Root Cause Analysis

Potential causes of edge label clipping:

1. **SVG overflow clipping**: The `.mermaid-container svg { max-width: 100% }` combined with container overflow may clip edge label backgrounds
2. **Edge label positioning**: Mermaid calculates label positions that may extend beyond node boundaries
3. **Font rendering**: The `edgeLabel` background padding may not account for actual rendered text width
4. **Container constraints**: Parent containers (`.glass-card`, `.glass`) may have overflow constraints

---

## Implementation

### 1. Update Mermaid CSS Styling

```css
/* ui/src/app/globals.css */

/* Fix edge label clipping - ensure labels have enough space */
.mermaid-container .edgeLabel {
  background-color: #0B0F14 !important;
  padding: 4px 8px !important;  /* Increased padding */
  border-radius: 4px;
  overflow: visible !important;  /* Prevent clipping */
  white-space: nowrap !important; /* Prevent text wrapping */
}

.mermaid-container .edgeLabel .label {
  fill: #9CA3AF !important;
  font-size: 11px;
  overflow: visible !important;
}

/* Ensure edge label foreignObjects don't clip */
.mermaid-container .edgeLabel foreignObject {
  overflow: visible !important;
}

/* Edge label text should not be truncated */
.mermaid-container .edgeLabel span {
  display: inline-block;
  white-space: nowrap;
  overflow: visible !important;
  text-overflow: clip !important;
}

/* Sequence diagram message text - fix clipping */
.mermaid-container .messageText {
  fill: #D1D5DB !important;
  font-size: 12px;
  overflow: visible !important;
}

/* Ensure SVG allows overflow for labels */
.mermaid-container svg {
  overflow: visible !important;
  max-width: none;  /* Remove max-width constraint */
  width: 100%;
  height: auto;
  display: block;
  margin: 0 auto;
}

/* Container should scroll horizontally rather than clip */
.mermaid-container {
  width: 100%;
  overflow-x: auto;
  overflow-y: visible;
  padding: 10px 0; /* Add vertical padding for overflow labels */
  scrollbar-width: thin;
  scrollbar-color: rgba(99, 210, 151, 0.3) transparent;
}
```

### 2. Update Mermaid Configuration

```tsx
// ui/src/components/MermaidDiagram.tsx

// In mermaid.initialize(), update flowchart config:
flowchart: {
  curve: 'basis',
  padding: 30,        // Increased from 20
  nodeSpacing: 60,    // Increased from 50
  rankSpacing: 70,    // Increased from 60
  htmlLabels: true,
  useMaxWidth: false, // Changed: allow diagram to size naturally
  wrappingWidth: 200, // Wrap long labels
},

// Update sequence diagram config:
sequence: {
  actorMargin: 60,      // Increased from 50
  boxMargin: 15,        // Increased from 10
  boxTextMargin: 8,     // Increased from 5
  noteMargin: 15,       // Increased from 10
  messageMargin: 45,    // Increased from 35
  mirrorActors: true,
  useMaxWidth: false,   // Changed: allow diagram to size naturally
  wrap: true,           // Enable text wrapping
  wrapPadding: 10,      // Padding for wrapped text
},
```

### 3. Add Wrapper Component for Better Sizing

```tsx
// ui/src/components/MermaidDiagram.tsx

// Wrap the diagram in a container that handles sizing better
return (
  <>
    <div
      className={`mermaid-wrapper ${className || ''}`}
      style={{ minWidth: 'fit-content' }}
    >
      <div
        className={`mermaid-container ${clickable ? 'mermaid-clickable' : ''}`}
        role="img"
        aria-label={ariaLabel ?? 'Mermaid diagram'}
        onClick={handleClick}
        onKeyDown={handleKeyDown}
        tabIndex={clickable ? 0 : undefined}
        dangerouslySetInnerHTML={{ __html: svg }}
      />
    </div>
    {showModal && (
      <MermaidDiagramModal
        svg={svg}
        ariaLabel={ariaLabel}
        onClose={() => setShowModal(false)}
      />
    )}
  </>
);
```

### 4. Additional CSS for Wrapper

```css
/* Mermaid wrapper for proper sizing */
.mermaid-wrapper {
  width: 100%;
  overflow-x: auto;
  overflow-y: visible;
}

/* Glass card mermaid adjustments */
.glass-card .mermaid-wrapper,
.glass .mermaid-wrapper {
  margin: -8px;  /* Compensate for container padding */
  padding: 8px;
}

/* Ensure sequence diagram messages don't clip */
.mermaid-container .messageLine0,
.mermaid-container .messageLine1 {
  stroke: #63D297 !important;
  stroke-width: 1.5px !important;
}

/* Message text container */
.mermaid-container text.messageText {
  dominant-baseline: central;
}

/* Flowchart edge labels */
.mermaid-container .flowchart-link {
  overflow: visible !important;
}
```

### 5. Competition Page Specific Fixes

The diagrams on the competition page are in containers with specific styling. Ensure these don't constrain the diagrams:

```css
/* Competition page diagram containers */
.glass-card .mermaid-container,
.glass .mermaid-container {
  padding: 12px;
  min-height: 200px;  /* Ensure minimum height */
}

/* Allow overflow in architecture diagram section */
.glass-card > .overflow-x-auto {
  overflow: visible;
}
```

---

## Testing

### Visual Testing with Playwright

Create a test that captures screenshots of the competition page diagrams:

```typescript
// ui/e2e/visual/mermaid.visual.spec.ts

import { test, expect } from '@playwright/test';

test.describe('Mermaid Diagram Edge Labels', () => {
  test('sequence diagram labels are fully visible', async ({ page }) => {
    await page.goto('/competition');
    await page.waitForLoadState('networkidle');

    // Wait for Mermaid to render
    await page.waitForSelector('.mermaid-container svg', { timeout: 10000 });
    await page.waitForTimeout(2000); // Allow rendering to complete

    // Find the sequence diagram (Platform Service Calls section)
    const sequenceDiagram = page.locator('.mermaid-container').nth(1);

    // Take screenshot
    await expect(sequenceDiagram).toHaveScreenshot('sequence-diagram-labels.png', {
      maxDiffPixels: 100,
    });

    // Verify specific labels are visible
    const svg = sequenceDiagram.locator('svg');

    // Check that message text elements exist and have content
    const messageTexts = svg.locator('.messageText');
    const count = await messageTexts.count();
    expect(count).toBeGreaterThan(0);

    // Verify text content is not truncated (check bounding boxes)
    for (let i = 0; i < count; i++) {
      const text = messageTexts.nth(i);
      const box = await text.boundingBox();
      if (box) {
        // Text should have reasonable width (not collapsed)
        expect(box.width).toBeGreaterThan(50);
      }
    }
  });

  test('flowchart edge labels are fully visible', async ({ page }) => {
    await page.goto('/competition');
    await page.waitForLoadState('networkidle');
    await page.waitForSelector('.mermaid-container svg', { timeout: 10000 });
    await page.waitForTimeout(2000);

    // Find the architecture flowchart (first diagram)
    const flowchart = page.locator('.mermaid-container').first();

    await expect(flowchart).toHaveScreenshot('flowchart-labels.png', {
      maxDiffPixels: 100,
    });

    // Verify edge labels exist
    const edgeLabels = flowchart.locator('.edgeLabel');
    const count = await edgeLabels.count();
    // The architecture diagram may not have edge labels,
    // but the egress diagram has "Blocked" labels
  });

  test('egress diagram blocked labels are visible', async ({ page }) => {
    await page.goto('/competition');
    await page.waitForLoadState('networkidle');
    await page.waitForSelector('.mermaid-container svg', { timeout: 10000 });
    await page.waitForTimeout(2000);

    // Scroll to security section
    await page.locator('text=Security Model').scrollIntoViewIfNeeded();
    await page.waitForTimeout(500);

    // Find the egress diagram (last one in security section)
    const egressDiagram = page.locator('.mermaid-container').last();

    await expect(egressDiagram).toHaveScreenshot('egress-diagram-labels.png', {
      maxDiffPixels: 100,
    });

    // Verify "Blocked" labels are visible
    const svg = egressDiagram.locator('svg');
    const blockedText = await svg.textContent();
    expect(blockedText).toContain('Blocked');
  });
});
```

### Manual Testing Steps

1. Open http://localhost:3000/competition
2. Scroll to "Architecture Overview" section
3. Check the sequence diagram under "Platform Service Calls"
4. Verify these labels are fully visible:
   - `Search for "quantum entanglement"`
   - `Top 10 results`
   - `Fetch https://physics.org/quantum`
   - `Page content`
   - `Call DeepSeek-V3.2 for synthesis`
   - `Synthesized explanation`
   - `Execute Python visualization`
   - `Generated image`
5. Scroll to "Security Model" section
6. Check the egress control diagram
7. Verify "Blocked" labels on dashed lines are visible
8. Test on mobile viewport (375px width) - diagrams should scroll horizontally

---

## Acceptance Criteria

- [ ] All sequence diagram message labels are fully visible (not clipped)
- [ ] Flowchart edge labels (e.g., "Blocked") are fully visible
- [ ] Diagrams render correctly on desktop (1920x1080)
- [ ] Diagrams are horizontally scrollable on mobile without label clipping
- [ ] Modal view shows full diagrams with all labels
- [ ] No horizontal overflow on the page (diagrams scroll within their container)
- [ ] Visual regression tests pass with captured screenshots

---

## Files to Modify

```
ui/
├── src/
│   ├── app/
│   │   └── globals.css                    # MODIFY - Fix edge label CSS
│   └── components/
│       └── MermaidDiagram.tsx             # MODIFY - Update Mermaid config
└── e2e/
    └── visual/
        └── mermaid.visual.spec.ts         # NEW - Visual tests for diagrams
```

---

## Browser Testing Commands

```bash
# Run dev server
cd ui && npm run dev

# In another terminal, take screenshot with Playwright
npx playwright test e2e/visual/mermaid.visual.spec.ts --headed

# Or use Playwright MCP for interactive testing
# Navigate to /competition and visually verify diagrams
```

---

## Related Specs

- `specs/71_competition_page_improvements.md` - Competition page
- `specs/108_visual_regression_testing.md` - Visual testing setup

NR_OF_TRIES: 0
