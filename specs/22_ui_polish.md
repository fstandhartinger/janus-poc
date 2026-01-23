# Spec 22: UI Polish & Chat Fix

## Status: COMPLETE

## Context

The current UI needs significant polish to match a premium, award-winning aesthetic. The chat functionality is broken with connection errors. This spec addresses both visual improvements and critical functionality fixes.

## Requirements

### 22.1 Landing Page Premium Redesign

Transform the landing page into a bold, exclusive, award-winning design.

#### 22.1.1 Hero Section Restructure
- **Hero image FIRST**: Full-width hero image at the top (the Janus bull rider)
- **Text section BELOW the image**: Not overlaid, positioned after
- **Change copy**: Replace "the best AI agent" with **"the intelligence engine"**
- **Fix button text**: Change "Manus Chat" to **"Janus Chat"**

#### 22.1.2 Premium Visual Style
Take inspiration from:
- `/home/flori/Dev/chutes/style/chutes_style.md` - Chutes design system
- `/home/flori/Dev/chutes/chutes-frontend/` - Production Chutes frontend

Make it look **even more high-end**:
- Bold typography with dramatic scale contrasts
- Generous whitespace (luxury brands use space)
- Subtle micro-animations on scroll
- Premium gradients (deeper, richer aurora effects)
- Glass morphism with more dramatic blur/opacity
- High-contrast text hierarchy
- Sophisticated color palette (less saturated, more refined)

#### 22.1.3 Add API Section
Add a new section showcasing the API:
- OpenAI-compatible endpoint highlight
- Code snippet example (curl or Python)
- "Drop-in replacement" messaging
- Link to API documentation

### 22.2 Chat App Design Overhaul

#### 22.2.1 Reference Design
Study and reverse-engineer https://chat.chutes.ai/:
- Take screenshots at multiple viewports
- Inspect HTML structure and Tailwind classes
- Note the sidebar design, message bubbles, input area
- Capture the color scheme, spacing, typography

#### 22.2.2 Implement Matching Design
Update the Janus chat UI to match the Chutes chat aesthetic:
- Sidebar with conversation list
- Message bubbles with proper styling
- Input area with send button
- Loading states and animations
- Model selector (if present)
- Responsive design

### 22.3 FIX CRITICAL BUG: Chat Connection Error

**Current Issue**: Chat always fails with "Connection error: All connection attempts failed"

#### 22.3.1 Debug & Fix
1. **Investigate the error source**:
   - Check `ui/src/components/ChatArea.tsx` or similar
   - Find where the API call is made
   - Check the API endpoint URL
   - Verify CORS settings

2. **Test the API directly**:
   ```bash
   # Test gateway health
   curl http://localhost:8000/health

   # Test chat completions endpoint
   curl -X POST http://localhost:8000/v1/chat/completions \
     -H "Content-Type: application/json" \
     -d '{"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "Hello"}]}'
   ```

3. **Common fixes to check**:
   - API base URL configuration (env vars)
   - CORS headers on gateway
   - WebSocket vs HTTP streaming
   - Authentication headers
   - Network/firewall issues

4. **Fix the root cause** - don't just handle the error, make it work!

#### 22.3.2 Comprehensive Testing
- **Unit tests**: API client functions
- **Integration tests**: Full chat flow
- **E2E tests with Playwright**: Visual browser testing
- **API smoke tests**: Direct endpoint testing

### 22.4 Visual Testing Requirements

Use Playwright MCP to:
1. Navigate to landing page - screenshot at 1920x1080, 768x1024, 375x812
2. Navigate to /chat - screenshot same viewports
3. Test chat interaction - send message, verify response
4. Check browser console for errors
5. Check network tab for failed requests

### 22.5 Telegram Status Updates

Send progress updates to Telegram:
- Use the Telegram bot configured for this project
- Report: iteration progress, bugs found/fixed, deployment status

## Acceptance Criteria

### Landing Page
- [ ] Hero image displays full-width at top of page
- [ ] Text section appears below hero image
- [ ] Copy says "the intelligence engine" (not "the best AI agent")
- [ ] Button says "Janus Chat" (not "Manus Chat")
- [ ] API section is present with code example
- [ ] Design feels premium, bold, award-winning
- [ ] Matches or exceeds Chutes frontend quality

### Chat App
- [ ] Design matches https://chat.chutes.ai/ aesthetic
- [ ] Chat actually WORKS - messages send and receive
- [ ] No "Connection error" messages
- [ ] Streaming responses display properly
- [ ] Responsive on all viewports

### Testing
- [ ] Unit tests for API client pass
- [ ] Integration tests for chat flow pass
- [ ] E2E Playwright tests pass
- [ ] No console errors in browser
- [ ] No failed network requests

### Deployment
- [ ] Changes deployed to Render
- [ ] Production site verified working
- [ ] Telegram status sent

## Test Plan

### Unit Tests
```bash
cd ui && npm test
```
- Test API client configuration
- Test message formatting
- Test error handling

### Integration Tests
```bash
cd gateway && pytest tests/test_chat.py
```
- Test full chat completions flow
- Test streaming responses
- Test error cases

### E2E Tests (Playwright)
```typescript
test('chat sends and receives messages', async ({ page }) => {
  await page.goto('/chat');
  await page.fill('[data-testid="chat-input"]', 'Hello');
  await page.click('[data-testid="send-button"]');
  await expect(page.locator('[data-testid="assistant-message"]')).toBeVisible();
});
```

### Visual Tests
- Screenshots at 3 viewports
- Compare against reference designs
- Check for visual regressions

## Dependencies

- Spec 18 (landing page) - must be complete
- Spec 11 (chat UI) - must be complete
- Gateway must be deployed and accessible

## Notes

**Priority**: This is HIGH priority because the chat being broken is a critical bug.

**Research first**: Before implementing, spend time:
1. Taking screenshots of chat.chutes.ai
2. Inspecting their CSS/Tailwind
3. Understanding their component structure
4. Testing the current API to understand the connection error

**Don't guess**: Actually debug the connection error with proper logging and network inspection.
