# Spec 111: Fix API Docs Table of Contents Overlap

## Status: COMPLETE

**Priority:** Low
**Complexity:** Low
**Prerequisites:** None

---

## Problem Statement

On the API documentation page (`/api-docs`), the sticky "Contents" sidebar (Table of Contents) overlaps with the main content text when scrolling. The sidebar was missing a background color, causing content to show through it during scroll.

---

## Root Cause

The `<aside>` element with the Table of Contents had:
- `lg:sticky lg:top-24` - Makes it stick to the viewport on scroll
- `h-fit` - Fits to content height
- **No background** - Content scrolled underneath was visible through the sidebar

---

## Solution

Added background, backdrop blur, padding, and z-index to the sticky sidebar:

```jsx
// Before
<aside className="lg:sticky lg:top-24 h-fit">

// After
<aside className="lg:sticky lg:top-24 h-fit bg-[#0B0F14]/95 backdrop-blur-sm lg:py-4 lg:-my-4 lg:pr-4 z-10">
```

**Changes:**
- `bg-[#0B0F14]/95` - Semi-transparent dark background matching page
- `backdrop-blur-sm` - Subtle blur effect for depth
- `lg:py-4 lg:-my-4` - Padding with negative margin to extend background
- `lg:pr-4` - Right padding for visual spacing
- `z-10` - Ensures sidebar stays above scrolling content

---

## Files Modified

```
ui/src/app/api-docs/page.tsx  # Line 268
```

---

## Testing

1. Navigate to http://localhost:3000/api-docs
2. Scroll down the page
3. Verify the "Contents" sidebar:
   - Has a visible background
   - Stays fixed in position
   - Content scrolls cleanly behind it without overlap
   - Backdrop blur provides subtle depth

---

## Acceptance Criteria

- [x] Sticky sidebar has background color
- [x] Content does not show through sidebar when scrolling
- [x] Visual appearance consistent with dark theme
- [x] Works on desktop (lg: breakpoint and above)

NR_OF_TRIES: 1
