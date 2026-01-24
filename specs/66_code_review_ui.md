# Spec 66: Code Review - UI (Next.js Frontend)

## Status: DRAFT

## Context / Why

The UI is the user-facing Next.js application including the chat interface, landing page, competition page, and marketplace. A thorough code review is needed to identify and fix:

- Bugs and edge cases
- Performance bottlenecks
- Design/architecture issues
- Naming inconsistencies
- Overly complicated solutions
- Accessibility issues
- Error handling gaps
- State management problems

## Scope

Review all code in `ui/src/`:

```
ui/
├── src/
│   ├── app/
│   │   ├── layout.tsx             # Root layout
│   │   ├── page.tsx               # Landing page
│   │   ├── globals.css            # Global styles
│   │   ├── chat/
│   │   │   └── page.tsx           # Chat page
│   │   ├── competition/
│   │   │   └── page.tsx           # Competition page
│   │   └── marketplace/
│   │       └── page.tsx           # Marketplace page
│   ├── components/
│   │   ├── ChatArea.tsx           # Main chat component
│   │   ├── Sidebar.tsx            # Chat sidebar
│   │   ├── MessageBubble.tsx      # Message display
│   │   ├── MermaidDiagram.tsx     # Diagram renderer
│   │   ├── VoiceInput.tsx         # Voice recording
│   │   └── landing/               # Landing components
│   ├── lib/
│   │   ├── api.ts                 # API client
│   │   ├── transcription.ts       # Transcription helper
│   │   └── storage.ts             # Local storage
│   └── types/
│       └── chat.ts                # TypeScript types
```

## Review Checklist

### 1. App Router (app/)

- [ ] **Layout**: Root layout correct
- [ ] **Metadata**: SEO metadata set
- [ ] **Loading states**: Loading.tsx where needed
- [ ] **Error boundaries**: Error.tsx handlers
- [ ] **Not found**: 404 page exists
- [ ] **Fonts**: Fonts loaded efficiently

### 2. Chat Components

#### ChatArea.tsx
- [ ] **State management**: State organized well
- [ ] **Effects**: useEffect dependencies correct
- [ ] **Memoization**: useMemo/useCallback where needed
- [ ] **Event handlers**: No inline functions in JSX
- [ ] **Accessibility**: ARIA labels, keyboard nav
- [ ] **Error handling**: API errors displayed
- [ ] **Loading states**: Skeleton/spinners

#### Message Components
- [ ] **Markdown rendering**: Safe markdown parsing
- [ ] **Code highlighting**: Syntax highlighting works
- [ ] **XSS prevention**: HTML escaped
- [ ] **Image handling**: Images sized properly
- [ ] **Streaming**: Incremental updates work

#### Voice Input
- [ ] **Permissions**: Mic permission handled
- [ ] **Recording**: Audio captured correctly
- [ ] **Transcription**: API called properly
- [ ] **Error handling**: Errors displayed
- [ ] **Cleanup**: MediaRecorder cleaned up

### 3. API Client (lib/api.ts)

- [ ] **Base URL**: Configurable
- [ ] **Error handling**: Errors parsed
- [ ] **Streaming**: SSE parsed correctly
- [ ] **Timeouts**: Request timeouts
- [ ] **Retry logic**: Transient failures retried
- [ ] **Headers**: Correct headers sent

### 4. State Management

- [ ] **Local state**: useState used correctly
- [ ] **Side effects**: useEffect cleanup
- [ ] **Context**: Context not overused
- [ ] **Persistence**: localStorage used safely
- [ ] **Sync issues**: No stale state bugs

### 5. Styling (globals.css)

- [ ] **Organization**: CSS organized by component
- [ ] **Specificity**: No specificity wars
- [ ] **Responsive**: Mobile-first approach
- [ ] **Variables**: CSS variables used
- [ ] **Dark mode**: Consistent dark theme
- [ ] **Animation**: Smooth, performant

### 6. Accessibility

- [ ] **Semantic HTML**: Correct elements
- [ ] **ARIA**: Labels and roles
- [ ] **Focus management**: Tab order correct
- [ ] **Screen readers**: Content accessible
- [ ] **Color contrast**: WCAG compliant
- [ ] **Keyboard**: All actions keyboard accessible

### 7. Performance

- [ ] **Bundle size**: No unnecessary deps
- [ ] **Images**: Optimized, next/image used
- [ ] **Lazy loading**: Large components lazy loaded
- [ ] **Memoization**: Expensive renders avoided
- [ ] **Re-renders**: No unnecessary re-renders
- [ ] **Network**: Minimal requests

### 8. TypeScript

- [ ] **Types**: All props typed
- [ ] **Generics**: Used where appropriate
- [ ] **No any**: No any types
- [ ] **Null checks**: Null handled safely
- [ ] **Enums/unions**: Used for constants
- [ ] **Interfaces**: Consistent style

### 9. Testing

- [ ] **Unit tests**: Components tested
- [ ] **Integration**: Page tests exist
- [ ] **Mocking**: API properly mocked
- [ ] **Coverage**: Critical paths covered

## Common Issues to Look For

### React Specific
- Missing dependency arrays
- State updates on unmounted components
- Prop drilling too deep
- Context overuse
- Missing key props in lists

### Performance
- Large bundle imports
- Unoptimized images
- Unnecessary re-renders
- Blocking the main thread
- Memory leaks

### Accessibility
- Missing alt text
- Poor focus management
- Low contrast
- Missing ARIA labels
- Keyboard traps

### Styling
- CSS conflicts
- !important overuse
- Hardcoded values
- Inconsistent spacing
- Non-responsive elements

## Improvement Actions

For each issue found:

1. **Document**: File, line, issue
2. **Categorize**: Bug, Performance, Design, Accessibility, Styling
3. **Prioritize**: Critical, High, Medium, Low
4. **Fix**: Implement fix
5. **Test**: Add/update tests
6. **Visual test**: Screenshot verification

## Deliverables

- [ ] All issues fixed
- [ ] Accessibility improved
- [ ] Performance optimized
- [ ] Tests updated
- [ ] No visual regressions

## Acceptance Criteria

- [ ] Zero TypeScript errors
- [ ] Zero linting errors
- [ ] All tests pass
- [ ] Lighthouse score > 90
- [ ] Accessibility audit passes
- [ ] Visual consistency verified
- [ ] Responsive on all breakpoints
