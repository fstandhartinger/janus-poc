# Spec 61: Fix Chat UI Issues (Vision, LangChain, Dropdown)

## Status: DRAFT

## Context / Why

Several issues have been identified in the chat UI:

### Issue 1: Images Not Processed by Vision Model

When sending an image with a message like "was siehst du auf dem bild" (what do you see in the image), the response shows placeholder tokens instead of image analysis:

```
<|media_start|>image<|media_content|><|media_pad|><|media_end|>
```

This indicates the baseline is not routing image requests to a vision-capable model.

### Issue 2: LangChain Baseline Connection Error

When switching to the langchain baseline:
```
Connection error: All connection attempts failed
```

The LangChain baseline service may be misconfigured or unavailable on Render.

### Issue 3: Dropdown Styling Problems

1. **Naming**: The model dropdown shows "baseline" instead of "baseline-cli-agent"
2. **Contrast**: Non-focused dropdown items have white/light text on white background, making them unreadable
3. **Styling**: The native `<select>` element looks inconsistent with the dark theme

## Goals

- Fix image routing to vision models
- Fix LangChain baseline connectivity
- Rename "baseline" to "baseline-cli-agent" in UI
- Improve dropdown styling for better contrast and appearance
- Scan and fix similar styling issues across the frontend
- Fix or remove non-functional hamburger menu button

## Functional Requirements

### FR-1: Rename Baseline in Competitor Registry

```python
# gateway/janus_gateway/services/competitor_registry.py

def _init_default_competitors(self) -> None:
    """Initialize with the baseline competitors."""
    baseline_url = self._normalize_url(self._baseline_url) if self._baseline_url else None
    baseline = CompetitorInfo(
        id="baseline-cli-agent",  # Changed from "baseline"
        name="Baseline CLI Agent",
        description="Reference agent-based baseline competitor",
        url=baseline_url or "http://localhost:8001",
        status="active",
        is_baseline=True,
    )
    self.register(baseline, is_default=True)

    # LangChain baseline
    baseline_langchain_url = (
        self._normalize_url(self._baseline_langchain_url)
        if self._baseline_langchain_url
        else None
    )
    if baseline_langchain_url:
        langchain_baseline = CompetitorInfo(
            id="baseline-langchain",
            name="Baseline LangChain",
            description="LangChain-based baseline competitor",
            url=baseline_langchain_url,
            status="active",
            is_baseline=True,
        )
        self.register(langchain_baseline)
```

### FR-2: Update UI Default Model

```tsx
// ui/src/components/ChatArea.tsx

// Change default from 'baseline' to 'baseline-cli-agent'
const [selectedModel, setSelectedModel] = useState('baseline-cli-agent');

// Update fallback models array
const fallbackModels: Model[] = [
  { id: 'baseline-cli-agent', object: 'model', created: 0, owned_by: 'janus' },
];
```

### FR-3: Fix Dropdown Styling

Replace the native `<select>` with a custom styled dropdown component:

```tsx
// ui/src/components/ModelSelector.tsx

'use client';

import { useState, useRef, useEffect } from 'react';
import type { Model } from '@/types/chat';

interface ModelSelectorProps {
  models: Model[];
  selectedModel: string;
  onSelect: (modelId: string) => void;
}

export function ModelSelector({ models, selectedModel, onSelect }: ModelSelectorProps) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close on click outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Close on escape
  useEffect(() => {
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setIsOpen(false);
    };
    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, []);

  const selectedModelObj = models.find((m) => m.id === selectedModel);

  return (
    <div ref={dropdownRef} className="model-selector">
      <span className="model-selector-label">Model</span>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="model-selector-trigger"
        aria-expanded={isOpen}
        aria-haspopup="listbox"
      >
        <span className="model-selector-value">
          {selectedModelObj?.id || selectedModel}
        </span>
        <svg
          className={`model-selector-chevron ${isOpen ? 'rotate-180' : ''}`}
          viewBox="0 0 20 20"
          fill="currentColor"
        >
          <path
            fillRule="evenodd"
            d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z"
            clipRule="evenodd"
          />
        </svg>
      </button>

      {isOpen && (
        <div className="model-selector-dropdown" role="listbox">
          {models.map((model) => (
            <button
              key={model.id}
              type="button"
              role="option"
              aria-selected={model.id === selectedModel}
              className={`model-selector-option ${
                model.id === selectedModel ? 'model-selector-option-selected' : ''
              }`}
              onClick={() => {
                onSelect(model.id);
                setIsOpen(false);
              }}
            >
              <span className="model-selector-option-name">{model.id}</span>
              {model.id.includes('langchain') && (
                <span className="model-selector-option-badge">LangChain</span>
              )}
              {model.id.includes('cli-agent') && (
                <span className="model-selector-option-badge">CLI</span>
              )}
              {model.id === selectedModel && (
                <svg className="model-selector-check" viewBox="0 0 20 20" fill="currentColor">
                  <path
                    fillRule="evenodd"
                    d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                    clipRule="evenodd"
                  />
                </svg>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
```

### FR-4: Updated CSS for Dropdown

```css
/* ui/src/app/globals.css */

/* ─── Model Selector (Custom Dropdown) ─────────────────────────────────────── */

.model-selector {
  position: relative;
  display: flex;
  align-items: center;
  gap: 8px;
}

.model-selector-label {
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.3em;
  color: #6B7280;
}

.model-selector-trigger {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 8px;
  border: 1px solid rgba(55, 65, 81, 0.8);
  background: rgba(17, 23, 38, 0.9);
  color: #F3F4F6;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.model-selector-trigger:hover {
  border-color: rgba(99, 210, 151, 0.4);
  background: rgba(17, 23, 38, 1);
}

.model-selector-trigger:focus {
  outline: none;
  border-color: #63D297;
  box-shadow: 0 0 0 2px rgba(99, 210, 151, 0.2);
}

.model-selector-value {
  max-width: 160px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.model-selector-chevron {
  width: 14px;
  height: 14px;
  color: #9CA3AF;
  transition: transform 0.15s ease;
}

.model-selector-dropdown {
  position: absolute;
  top: calc(100% + 4px);
  right: 0;
  min-width: 200px;
  max-height: 300px;
  overflow-y: auto;
  padding: 4px;
  border-radius: 10px;
  border: 1px solid rgba(55, 65, 81, 0.9);
  background: rgba(17, 23, 38, 0.98);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5);
  z-index: 50;
  animation: dropdownFadeIn 0.15s ease;
}

@keyframes dropdownFadeIn {
  from {
    opacity: 0;
    transform: translateY(-4px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.model-selector-option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 10px 12px;
  border-radius: 6px;
  border: none;
  background: transparent;
  color: #D1D5DB;
  font-size: 13px;
  text-align: left;
  cursor: pointer;
  transition: all 0.1s ease;
}

.model-selector-option:hover {
  background: rgba(99, 210, 151, 0.1);
  color: #F3F4F6;
}

.model-selector-option-selected {
  background: rgba(99, 210, 151, 0.15);
  color: #63D297;
}

.model-selector-option-selected:hover {
  background: rgba(99, 210, 151, 0.2);
}

.model-selector-option-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.model-selector-option-badge {
  margin-left: 8px;
  padding: 2px 6px;
  border-radius: 4px;
  background: rgba(99, 210, 151, 0.15);
  color: #63D297;
  font-size: 9px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.model-selector-check {
  width: 16px;
  height: 16px;
  margin-left: 8px;
  color: #63D297;
}

/* ─── Fallback for native select (mobile) ─────────────────────────────────── */

.chat-model-dropdown {
  appearance: none;
  -webkit-appearance: none;
  background: rgba(17, 23, 38, 0.9);
  border: 1px solid rgba(55, 65, 81, 0.8);
  border-radius: 8px;
  padding: 6px 28px 6px 12px;
  color: #F3F4F6;
  font-size: 12px;
  outline: none;
  cursor: pointer;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 20 20' fill='%239CA3AF'%3E%3Cpath fill-rule='evenodd' d='M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z' clip-rule='evenodd'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 8px center;
  background-size: 14px;
}

.chat-model-dropdown:focus {
  border-color: #63D297;
  box-shadow: 0 0 0 2px rgba(99, 210, 151, 0.2);
}

/* Style options for browsers that support it */
.chat-model-dropdown option {
  background: #111726;
  color: #F3F4F6;
  padding: 8px;
}

.chat-model-dropdown option:checked {
  background: linear-gradient(0deg, rgba(99, 210, 151, 0.2), rgba(99, 210, 151, 0.2));
}
```

### FR-5: Fix LangChain Baseline Connectivity

Check and fix the LangChain baseline URL configuration:

```yaml
# render.yaml - Update LangChain baseline URL reference

services:
  - type: web
    name: janus-gateway
    # ... other config ...
    envVars:
      # ... other vars ...
      - key: BASELINE_LANGCHAIN_URL
        fromService:
          type: web
          name: janus-baseline-langchain
          property: host  # Changed from hostport if needed
          envVarKey: BASELINE_LANGCHAIN_URL
```

Also add health check and connection validation:

```python
# gateway/janus_gateway/services/competitor_registry.py

import httpx
import structlog

logger = structlog.get_logger()


async def check_competitor_health(url: str) -> bool:
    """Check if a competitor is reachable."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{url}/health")
            return response.status_code == 200
    except Exception as e:
        logger.warning("competitor_health_check_failed", url=url, error=str(e))
        return False


class CompetitorRegistry:
    # ... existing code ...

    async def get_available(self, competitor_id: str) -> Optional[CompetitorInfo]:
        """Get a competitor only if it's healthy."""
        competitor = self.get(competitor_id)
        if competitor and await check_competitor_health(competitor.url):
            return competitor
        return None
```

### FR-6: Fix Image Routing to Vision Models

The baseline needs to detect image content and route to a vision model. This should be handled by the composite model router (Spec 58/59), but we also need immediate fixes:

```python
# baseline-agent-cli/janus_baseline_agent_cli/services/vision.py

from typing import Union
from janus_baseline_agent_cli.models.openai import Message, MessageContent


def contains_images(messages: list[Message]) -> bool:
    """Check if any message contains image content."""
    for message in messages:
        if has_image_content(message.content):
            return True
    return False


def has_image_content(content: Union[str, list, None]) -> bool:
    """Check if message content contains images."""
    if content is None or isinstance(content, str):
        return False

    for part in content:
        if isinstance(part, dict):
            if part.get('type') == 'image_url':
                return True
        elif hasattr(part, 'type') and part.type == 'image_url':
            return True

    return False
```

Update the baseline to use vision models for image requests:

```python
# baseline-agent-cli/janus_baseline_agent_cli/main.py

from .services.vision import contains_images
from .config import get_settings

VISION_MODELS = [
    "Qwen/Qwen3-VL-235B-A22B-Instruct",
    "zai-org/GLM-4.6V",
]


@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest) -> StreamingResponse:
    settings = get_settings()

    # Check for images and switch to vision model
    if contains_images(request.messages):
        # Use vision model instead of default
        effective_model = settings.vision_model_primary
        logger.info("switching_to_vision_model", model=effective_model)
    else:
        effective_model = request.model or settings.model

    # ... rest of implementation
```

### FR-7: Scan and Fix Other Styling Issues

Audit and fix these common styling issues across the frontend:

```css
/* ui/src/app/globals.css - Add these fixes */

/* ─── Form Elements (Inputs, Selects, Textareas) ──────────────────────────── */

/* Ensure all form elements have proper dark mode styling */
input,
select,
textarea {
  color-scheme: dark;
}

input::placeholder,
textarea::placeholder {
  color: #6B7280;
}

/* Focus states */
input:focus,
select:focus,
textarea:focus {
  outline: none;
  border-color: #63D297;
  box-shadow: 0 0 0 2px rgba(99, 210, 151, 0.2);
}

/* ─── Buttons ─────────────────────────────────────────────────────────────── */

button:focus-visible {
  outline: 2px solid #63D297;
  outline-offset: 2px;
}

/* ─── Links ───────────────────────────────────────────────────────────────── */

a:focus-visible {
  outline: 2px solid #63D297;
  outline-offset: 2px;
  border-radius: 2px;
}

/* ─── Scrollbars ──────────────────────────────────────────────────────────── */

::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: rgba(17, 23, 38, 0.5);
}

::-webkit-scrollbar-thumb {
  background: rgba(99, 210, 151, 0.3);
  border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
  background: rgba(99, 210, 151, 0.5);
}

/* ─── Tables ──────────────────────────────────────────────────────────────── */

table {
  color: #D1D5DB;
}

th {
  color: #9CA3AF;
}

/* ─── Code Blocks ─────────────────────────────────────────────────────────── */

pre,
code {
  background: rgba(17, 23, 38, 0.8);
  color: #E5E7EB;
}

/* ─── Tooltips ────────────────────────────────────────────────────────────── */

[title] {
  position: relative;
}

/* ─── Modal/Dialog Backdrops ──────────────────────────────────────────────── */

.modal-backdrop,
.dialog-backdrop {
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(4px);
}

/* ─── Toast/Notification styling ──────────────────────────────────────────── */

.toast {
  background: rgba(17, 23, 38, 0.95);
  border: 1px solid rgba(55, 65, 81, 0.8);
  color: #F3F4F6;
}

.toast-success {
  border-color: rgba(99, 210, 151, 0.5);
}

.toast-error {
  border-color: rgba(239, 68, 68, 0.5);
}

/* ─── Card/Glass Component consistency ────────────────────────────────────── */

.glass-card,
.glass {
  background: rgba(17, 23, 38, 0.7);
  border: 1px solid rgba(55, 65, 81, 0.6);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
}
```

### FR-8: Fix or Remove Non-Functional Hamburger Menu Button

The hamburger menu button (left of the home button in chat header) is non-functional. The button exists with class `chat-menu-btn lg:hidden` and is intended to open the sidebar on mobile, but:

1. It may be visible on desktop when it shouldn't be (due to CSS issues)
2. The sidebar toggle may not be working as expected

**Option A: Remove the button entirely** (if sidebar is always accessible via other means):

```tsx
// ui/src/components/ChatArea.tsx - Remove lines 168-177

// REMOVE this entire button block:
// <button
//   type="button"
//   onClick={onMenuClick}
//   className="chat-menu-btn lg:hidden"
//   aria-label="Open sidebar"
// >
//   <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="1.6">
//     <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
//   </svg>
// </button>
```

**Option B: Fix the button to properly toggle sidebar** (recommended for mobile UX):

```tsx
// ui/src/components/ChatArea.tsx

interface ChatAreaProps {
  onMenuClick?: () => void;
  isSidebarOpen?: boolean;  // Add this prop
}

export function ChatArea({ onMenuClick, isSidebarOpen }: ChatAreaProps) {
  // ...

  return (
    <div className="flex-1 flex flex-col min-h-0">
      <div className="chat-topbar shrink-0">
        <div className="chat-topbar-left">
          {/* Only show hamburger on mobile when sidebar is hidden */}
          {onMenuClick && (
            <button
              type="button"
              onClick={onMenuClick}
              className="chat-menu-btn"
              aria-label={isSidebarOpen ? "Close sidebar" : "Open sidebar"}
              aria-expanded={isSidebarOpen}
            >
              <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth="1.6">
                {isSidebarOpen ? (
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                ) : (
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
                )}
              </svg>
            </button>
          )}
          {/* ... rest of topbar */}
```

Update the CSS to properly show/hide on breakpoints:

```css
/* ui/src/app/globals.css */

.chat-menu-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 8px;
  border: 1px solid rgba(55, 65, 81, 0.6);
  background: rgba(17, 23, 38, 0.7);
  color: #9CA3AF;
  cursor: pointer;
  transition: all 0.15s ease;
}

.chat-menu-btn:hover {
  background: rgba(17, 23, 38, 0.9);
  color: #F3F4F6;
  border-color: rgba(99, 210, 151, 0.4);
}

/* Hide on large screens where sidebar is always visible */
@media (min-width: 1024px) {
  .chat-menu-btn {
    display: none;
  }
}
```

Update chat page to pass sidebar state:

```tsx
// ui/src/app/chat/page.tsx

<ChatArea
  onMenuClick={() => setSidebarOpen(!sidebarOpen)}
  isSidebarOpen={sidebarOpen}
/>
```

**Decision**: If the sidebar provides essential navigation that users need on mobile, implement Option B. If the hamburger menu adds complexity without clear value, implement Option A and remove it.

## Deployment Steps

### Step 1: Update Render Environment

1. Check `janus-baseline-langchain` service is running
2. Verify the URL is correctly set in gateway's `BASELINE_LANGCHAIN_URL`
3. Check service logs for errors

### Step 2: Set Vision Model API Key

Ensure `CHUTES_API_KEY` is set on baseline-agent-cli for vision model access.

### Step 3: Deploy Code Changes

```bash
# Gateway changes
cd gateway
pytest
git add -A && git commit -m "Rename baseline to baseline-cli-agent"
git push

# UI changes
cd ../ui
npm run typecheck && npm test
git add -A && git commit -m "Fix dropdown styling and model naming"
git push
```

## Testing Checklist

- [ ] Model dropdown shows "baseline-cli-agent" instead of "baseline"
- [ ] Dropdown has proper contrast (dark background, light text)
- [ ] Dropdown opens/closes smoothly with animation
- [ ] Clicking outside dropdown closes it
- [ ] LangChain baseline connection works
- [ ] Switching between baselines works
- [ ] Image messages are processed by vision model
- [ ] Vision model returns proper analysis (not placeholder tokens)
- [ ] All form elements have consistent dark styling
- [ ] Focus states are visible and consistent
- [ ] Hamburger menu button is NOT visible on desktop (lg breakpoint)
- [ ] Hamburger menu button IS visible on mobile/tablet
- [ ] Clicking hamburger opens sidebar on mobile
- [ ] Clicking hamburger again (or X) closes sidebar
- [ ] Sidebar overlay dismisses when clicking outside

## Acceptance Criteria

- [ ] "baseline" renamed to "baseline-cli-agent" in gateway and UI
- [ ] Custom dropdown component with proper dark theme styling
- [ ] LangChain baseline connectivity fixed
- [ ] Image requests routed to vision models
- [ ] No more placeholder tokens in vision responses
- [ ] Styling audit complete with fixes applied
- [ ] Hamburger menu button fixed or removed
- [ ] All tests pass

## Files to Modify

```
gateway/
├── janus_gateway/
│   └── services/
│       └── competitor_registry.py  # Rename baseline

ui/
├── src/
│   ├── app/
│   │   ├── globals.css             # Dropdown styling, global fixes, hamburger btn
│   │   └── chat/
│   │       └── page.tsx            # Pass sidebar state to ChatArea
│   └── components/
│       ├── ChatArea.tsx            # Use new dropdown, fix hamburger menu
│       └── ModelSelector.tsx       # NEW: Custom dropdown component

baseline-agent-cli/
├── janus_baseline_agent_cli/
│   ├── main.py                     # Vision routing
│   └── services/
│       └── vision.py               # Image detection
```

## Related Specs

- `specs/38_multimodal_vision_models.md` - Vision model configuration
- `specs/58_composite_model_router.md` - Model routing
- `specs/59_langchain_composite_model_router.md` - LangChain routing
