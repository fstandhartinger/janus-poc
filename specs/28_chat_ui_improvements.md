# Spec 28: Janus Chat UI Improvements

## Status: DRAFT

## Context / Why

The current Janus Chat UI has several UX issues that affect usability:

1. **Unused sections**: Library, Agents, and Studio buttons in the sidebar do nothing
2. **No navigation back to home**: Users are trapped in the chat interface
3. **Sidebar not collapsible on desktop**: Always visible, takes up screen real estate
4. **Hamburger menu issues**: May not be working correctly on mobile

These improvements will make the chat interface cleaner and more user-friendly.

## Goals

- Remove placeholder UI elements (Library, Agents, Studio)
- Add navigation back to landing page
- Make sidebar collapsible on all screen sizes
- Ensure mobile hamburger menu works correctly
- Improve overall UX polish

## Non-Goals

- Implementing actual Library/Agents/Studio features (future specs)
- Major redesign of the chat interface
- Adding new chat features

## Functional Requirements

### FR-1: Remove Unused Sidebar Sections

Remove the Library, Agents, and Studio buttons from `Sidebar.tsx`:

**Before (lines 70-80):**
```tsx
<div className="mt-4 space-y-1">
  <button type="button" className="chat-sidebar-item w-full">
    Library
  </button>
  <button type="button" className="chat-sidebar-item w-full">
    Agents
  </button>
  <button type="button" className="chat-sidebar-item w-full">
    Studio
  </button>
</div>
```

**After:**
Remove this entire block.

### FR-2: Add Home Navigation Link

Add a link back to the landing page in the sidebar header:

```tsx
// In Sidebar.tsx, after the workspace header
<Link href="/" className="chat-sidebar-item w-full flex items-center gap-2 mt-3">
  <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="1.5">
    <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 12l8.954-8.955c.44-.439 1.152-.439 1.591 0L21.75 12M4.5 9.75v10.125c0 .621.504 1.125 1.125 1.125H9.75v-4.875c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21h4.125c.621 0 1.125-.504 1.125-1.125V9.75M8.25 21h8.25" />
  </svg>
  <span>Home</span>
</Link>
```

Also add a home icon in the top bar for quick access:

```tsx
// In ChatArea.tsx, in the topbar-left section
<Link href="/" className="chat-home-btn" title="Go to home">
  <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="1.5">
    <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 12l8.954-8.955c.44-.439 1.152-.439 1.591 0L21.75 12M4.5 9.75v10.125c0 .621.504 1.125 1.125 1.125H9.75v-4.875c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21h4.125c.621 0 1.125-.504 1.125-1.125V9.75M8.25 21h8.25" />
  </svg>
</Link>
```

### FR-3: Collapsible Sidebar on Desktop

Make the sidebar collapsible on desktop with a toggle button:

**State management** - Add to page.tsx:
```tsx
const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
```

**CSS classes** - Add to globals.css:
```css
.chat-sidebar-collapsed {
  width: 72px;
  overflow: hidden;
}

.chat-sidebar-collapsed .chat-sidebar-hide-collapsed {
  display: none;
}

.chat-sidebar-collapsed .chat-session-list {
  display: none;
}

.chat-sidebar-toggle {
  @apply absolute right-0 top-1/2 -translate-y-1/2 translate-x-1/2 z-10
         w-6 h-6 rounded-full bg-[#1F2937] border border-[#374151]
         flex items-center justify-center text-[#9CA3AF]
         hover:bg-[#374151] hover:text-[#F3F4F6] transition-colors;
}
```

**Toggle button** - Add to Sidebar.tsx:
```tsx
<button
  onClick={() => onToggleCollapse?.()}
  className="chat-sidebar-toggle hidden lg:flex"
  aria-label={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
>
  <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="2">
    {isCollapsed ? (
      <path strokeLinecap="round" strokeLinejoin="round" d="M13 5l7 7-7 7" />
    ) : (
      <path strokeLinecap="round" strokeLinejoin="round" d="M11 19l-7-7 7-7" />
    )}
  </svg>
</button>
```

### FR-4: Fix Mobile Hamburger Menu

Verify the hamburger menu works correctly. Current implementation looks correct but may have CSS issues.

**Debug checklist:**
1. Check that `chat-sidebar-open` class is being applied when `isOpen` is true
2. Check that the sidebar has proper z-index to appear above content
3. Check that the overlay click handler works

**CSS fixes** (if needed):
```css
@media (max-width: 1023px) {
  .chat-sidebar {
    @apply fixed inset-y-0 left-0 z-40 transform -translate-x-full transition-transform;
  }

  .chat-sidebar-open {
    @apply translate-x-0;
  }
}
```

### FR-5: Sidebar Props Update

Update Sidebar component props:

```tsx
interface SidebarProps {
  isOpen?: boolean;           // Mobile: show/hide
  isCollapsed?: boolean;      // Desktop: collapsed state
  onClose?: () => void;       // Mobile: close handler
  onToggleCollapse?: () => void; // Desktop: toggle collapse
}
```

### FR-6: Update Page Layout

Update page.tsx to handle both mobile and desktop states:

```tsx
export default function ChatPage() {
  const [isMounted, setIsMounted] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  useEffect(() => {
    setIsMounted(true);
    // Restore collapsed state from localStorage
    const saved = localStorage.getItem('sidebar-collapsed');
    if (saved) setSidebarCollapsed(JSON.parse(saved));
  }, []);

  const toggleCollapse = () => {
    const newState = !sidebarCollapsed;
    setSidebarCollapsed(newState);
    localStorage.setItem('sidebar-collapsed', JSON.stringify(newState));
  };

  if (!isMounted) {
    return <div className="min-h-screen chat-aurora-bg" aria-busy="true" />;
  }

  return (
    <div className="min-h-screen chat-aurora-bg">
      <div className={`chat-shell ${sidebarCollapsed ? 'sidebar-collapsed' : ''}`}>
        {/* Mobile overlay */}
        {sidebarOpen && (
          <div
            className="fixed inset-0 bg-black/50 z-30 lg:hidden"
            onClick={() => setSidebarOpen(false)}
            aria-hidden="true"
          />
        )}
        <Sidebar
          isOpen={sidebarOpen}
          isCollapsed={sidebarCollapsed}
          onClose={() => setSidebarOpen(false)}
          onToggleCollapse={toggleCollapse}
        />
        <ChatArea onMenuClick={() => setSidebarOpen(true)} />
      </div>
    </div>
  );
}
```

## Non-Functional Requirements

### NFR-1: Accessibility

- All interactive elements must be keyboard accessible
- Proper ARIA labels on toggle buttons
- Focus management when sidebar state changes

### NFR-2: Performance

- Sidebar collapse state persisted in localStorage
- No layout shift when toggling collapse

### NFR-3: Responsive Design

- Mobile (<1024px): Full overlay sidebar, hamburger menu
- Desktop (>=1024px): Collapsible sidebar with toggle button

## Acceptance Criteria

- [ ] Library, Agents, Studio buttons removed from sidebar
- [ ] Home link added to sidebar header
- [ ] Home icon added to top bar for quick access
- [ ] Clicking home navigates to landing page
- [ ] Desktop: Sidebar has collapse toggle button
- [ ] Desktop: Collapsed sidebar shows only icons
- [ ] Desktop: Collapse state persists on page refresh
- [ ] Mobile: Hamburger menu opens sidebar
- [ ] Mobile: Clicking overlay closes sidebar
- [ ] All transitions are smooth (no jarring jumps)
- [ ] No console errors

## Files to Modify

- `ui/src/components/Sidebar.tsx` - Remove sections, add home link, add collapse
- `ui/src/components/ChatArea.tsx` - Add home icon to topbar
- `ui/src/app/chat/page.tsx` - Add collapse state management
- `ui/src/app/globals.css` - Add collapse-related styles

## Visual Reference

### Collapsed Sidebar (Desktop)
```
+--------+------------------------+
| [J]    |  Session: New chat    |
| [+]    |                       |
| [Home] |   Chat content...     |
|        |                       |
| [>]    |                       |
+--------+------------------------+
```

### Expanded Sidebar (Desktop)
```
+------------------+------------------------+
| Workspace        |  Session: New chat    |
| Janus Auto  [J]  |                       |
|                  |   Chat content...     |
| [+ New Chat]     |                       |
| [Home]           |                       |
|                  |                       |
| Chats            |                       |
| - Chat 1         |                       |
| - Chat 2         |                       |
|            [<]   |                       |
+------------------+------------------------+
```

## Related Specs

- Spec 11: Chat UI (original implementation)
- Spec 22: UI Polish
