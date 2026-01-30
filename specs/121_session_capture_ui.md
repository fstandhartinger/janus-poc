# Spec 121: Browser Session Capture UI

## Status: COMPLETE

## Priority: MEDIUM

## Context / Why

Based on research in spec 118, users need a way to capture browser sessions for use by agents. This requires a VNC-based UI where users can manually log in to websites, then save the session to their account.

**Reference:** `docs/browser-user-session-pre-research.md` and `docs/browser-session-research-results.md`

## Goals

1. Create a session capture UI in Janus chat or agent-as-a-service-web
2. Integrate VNC viewer for manual browser interaction
3. Allow users to name and save captured sessions
4. Connect to session store service (spec 119)

## Non-Goals

- Automated login flows
- OAuth integration for session capture
- Browser extension approach

## Functional Requirements

### FR-1: Session Capture Flow

1. User clicks "Manage Sessions" in Janus chat
2. User clicks "Capture New Session"
3. Sandy sandbox created with VNC + browser
4. VNC viewer appears in modal
5. User navigates to website and logs in manually
6. User clicks "Save Session"
7. User enters session name and selects domains
8. Session state captured and stored

### FR-2: VNC Viewer Component

Integrate noVNC for browser interaction:

```tsx
<VncViewer
  sandboxId={sandboxId}
  websocketUrl={`wss://sandy.../vnc/${sandboxId}/websockify`}
  onReady={() => setVncReady(true)}
  onDisconnect={() => handleDisconnect()}
/>
```

### FR-3: Session Save Dialog

```tsx
<SessionSaveDialog
  onSave={(name, description, domains) => saveSession()}
>
  <Input label="Session Name" placeholder="e.g., MyTwitter" />
  <Input label="Description" placeholder="Optional description" />
  <DomainSelector
    detected={detectedDomains}
    onChange={setSelectedDomains}
  />
</SessionSaveDialog>
```

### FR-4: Session Management UI

List and manage saved sessions:

```tsx
<SessionManager>
  <SessionList>
    {sessions.map(s => (
      <SessionCard
        key={s.id}
        name={s.name}
        domains={s.domains}
        createdAt={s.created_at}
        onDelete={() => deleteSession(s.id)}
        onUpdate={() => openCaptureForUpdate(s)}
      />
    ))}
  </SessionList>
  <Button onClick={startCapture}>Capture New Session</Button>
</SessionManager>
```

### FR-5: Domain Detection

Auto-detect domains from browser history during capture:

```javascript
// In sandbox browser via agent-browser eval
const history = await page.evaluate(() => {
  return performance.getEntriesByType('navigation')
    .concat(performance.getEntriesByType('resource'))
    .map(e => new URL(e.name).hostname)
    .filter((v, i, a) => a.indexOf(v) === i);
});
```

### FR-6: Session Capture API Call

```typescript
async function captureSession(sandboxId: string) {
  // Use agent-browser to export storage state
  const result = await fetch(`/api/sandbox/${sandboxId}/exec`, {
    method: 'POST',
    body: JSON.stringify({
      command: 'agent-browser eval "JSON.stringify({ cookies: document.cookie, localStorage: {...localStorage} })"'
    })
  });

  // Better: use Playwright storageState via Sandy exec
  const storageState = await fetch(`/api/sandbox/${sandboxId}/exec`, {
    method: 'POST',
    body: JSON.stringify({
      command: 'python3 -c "import asyncio; from playwright.async_api import async_playwright; ..."'
    })
  });

  return storageState;
}
```

## Technical Approach

### UI Location

**Option A:** Janus Chat Settings
- Add "Browser Sessions" tab in settings modal
- Accessible from chat header

**Option B:** Dedicated Route
- `/sessions` page in Janus UI
- Linked from chat header

**Recommendation:** Option A for MVP, Option B for polish

### Component Structure

```
ui/src/components/
├── sessions/
│   ├── SessionManager.tsx      # Main container
│   ├── SessionList.tsx         # List of sessions
│   ├── SessionCard.tsx         # Individual session display
│   ├── SessionCaptureModal.tsx # VNC + save workflow
│   ├── VncViewer.tsx           # noVNC wrapper
│   └── SessionSaveDialog.tsx   # Name/domain picker
```

### Dependencies

- noVNC (npm: `@nicely_done/novnc-client` or similar)
- Integration with session store API (spec 119)
- Sandy API for sandbox management

## Acceptance Criteria

- [ ] VNC viewer component works with Sandy sandboxes
- [ ] Users can manually log in via VNC
- [ ] Session capture exports cookies + localStorage
- [ ] Session save dialog with name and domains
- [ ] Sessions stored via session store API
- [ ] Session list with delete functionality
- [ ] Responsive UI (desktop and tablet)
- [ ] Unit tests for components
- [ ] E2E test for capture flow

## UI Mockup

```
┌─────────────────────────────────────────────────────┐
│  Browser Sessions                              [X]  │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Your Saved Sessions                                │
│  ┌─────────────────────────────────────────────┐   │
│  │ MyTwitter                          [Delete]  │   │
│  │ twitter.com, x.com                          │   │
│  │ Created: Jan 30, 2026                       │   │
│  └─────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────┐   │
│  │ WorkGitHub                         [Delete]  │   │
│  │ github.com                                  │   │
│  │ Created: Jan 29, 2026                       │   │
│  └─────────────────────────────────────────────┘   │
│                                                     │
│  [+ Capture New Session]                           │
│                                                     │
└─────────────────────────────────────────────────────┘
```

## Notes

- Consider session timeout (kill sandbox after inactivity)
- Consider progress indicator during capture
- Consider session preview before saving

---

*Reference: docs/browser-user-session-pre-research.md*
*Depends on: Spec 119 (session store), Spec 120 (agent-ready sandbox)*
