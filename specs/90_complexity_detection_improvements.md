# Spec 90: Complexity Detection Improvements

## Status: COMPLETE

## Context / Why

The current complexity detection has several issues discovered during testing:

1. **Missing German keywords** - German phrases like "lade herunter" (download), "suche" (search) are not detected
2. **Missing git/code keywords** - "git clone", "github", "git pull", "repository", "repo" not in keywords
3. **Sandy unavailability not handled gracefully** - When Sandy is unavailable, users get confusing LLM responses
4. **No fallback messaging** - Users don't understand why agent features aren't working

## Goals

- Add multilingual support for complexity keywords (German initially)
- Add git/repository-related keywords
- Improve handling when Sandy is unavailable
- Provide clear user feedback when agent features are unavailable

## Functional Requirements

### FR-1: Add German Keywords

```python
# In complexity.py - extend COMPLEX_KEYWORDS

COMPLEX_KEYWORDS_DE = [
    # Download/Fetch
    "herunterladen",
    "lade herunter",
    "lade...herunter",
    "downloaden",
    "holen",

    # Search
    "suche",
    "such nach",
    "recherchiere",
    "finde",
    "finde heraus",

    # Code execution
    "führe aus",
    "ausführen",
    "starte",
    "kompiliere",
    "teste",
    "debugge",

    # File operations
    "speichere",
    "schreibe",
    "erstelle datei",
    "lösche",

    # Web/Browser
    "öffne",
    "besuche",
    "navigiere",
    "screenshot",

    # Generation
    "generiere",
    "erstelle bild",
    "erzeuge",
]

COMPLEX_KEYWORDS = [
    # ... existing keywords ...

    # Git/Repository
    "git clone",
    "git pull",
    "git push",
    "github",
    "gitlab",
    "repository",
    "repo",
    "clone the",
    "pull the repo",

    # Add German keywords
    *COMPLEX_KEYWORDS_DE,
]
```

### FR-2: Handle Separable German Verbs

German has separable verbs like "herunter**laden**" → "lade X **herunter**"

```python
def _matched_complex_keywords_german(self, text: str) -> list[str]:
    """Match German separable verb patterns."""
    text_lower = text.lower()
    matches = []

    # Separable verb patterns: "lade ... herunter"
    separable_patterns = [
        (r"lade\s+.+\s+herunter", "herunterladen"),
        (r"such\s+.+\s+nach", "suchen nach"),
        (r"führ\s+.+\s+aus", "ausführen"),
        (r"stell\s+.+\s+ein", "einstellen"),
    ]

    for pattern, keyword in separable_patterns:
        if re.search(pattern, text_lower):
            matches.append(keyword)

    return matches
```

### FR-3: Graceful Sandy Unavailability

When Sandy is unavailable but request is complex, inform the user:

```python
# In main.py - stream_response and non-streaming

if is_complex and not sandy_service.is_available:
    logger.warning(
        "sandy_unavailable_for_complex_request",
        reason=reason,
        text_preview=analysis.text_preview,
    )

    # Option 1: Return informative error
    yield create_error_chunk(
        "Agent sandbox is currently unavailable. "
        "This request requires agent capabilities (code execution, web search, etc.) "
        "which are not available at this time. Please try again later."
    )
    return

    # Option 2: Fall back with warning prefix
    # Prepend warning to LLM response
```

### FR-4: Add Sandbox Status to Health Check

```python
@app.get("/health", response_model=HealthResponse)
async def health_check(
    sandy_service: SandyService = Depends(get_sandy_service),
) -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(
        status="ok",
        version=__version__,
        sandbox_available=sandy_service.is_available,
        features={
            "agent_sandbox": sandy_service.is_available,
            "memory": settings.enable_memory_feature,
            "vision": True,
        }
    )
```

### FR-5: UI Indication of Agent Availability

Show in the chat UI whether agent features are available:

```typescript
// In chat header or model selector
function AgentStatusIndicator() {
  const { isAgentAvailable } = useServiceHealth();

  return (
    <div className="flex items-center gap-2 text-xs">
      <div className={cn(
        "w-2 h-2 rounded-full",
        isAgentAvailable ? "bg-green-500" : "bg-yellow-500"
      )} />
      <span className="text-white/60">
        {isAgentAvailable ? "Full capabilities" : "Limited mode"}
      </span>
    </div>
  );
}
```

## Acceptance Criteria

- [ ] German phrases trigger complexity detection
- [ ] Git/repository keywords trigger agent path
- [ ] Separable German verbs are matched correctly
- [ ] Clear error message when Sandy unavailable for complex requests
- [ ] Health endpoint shows sandbox status
- [ ] UI indicates when agent features are unavailable

## Files to Modify

```
baseline-agent-cli/janus_baseline_agent_cli/
├── services/complexity.py    # Add keywords, German patterns
├── main.py                   # Handle Sandy unavailability gracefully

ui/src/
├── hooks/useServiceHealth.ts # NEW: Check agent availability
└── components/chat/
    └── AgentStatusIndicator.tsx  # NEW: Show status in UI
```

## Testing

```python
def test_german_keywords():
    detector = ComplexityDetector(settings)

    # Test separable verb
    messages = [Message(role="user", content="lade das repo von github herunter")]
    analysis = detector.analyze(messages)
    assert analysis.is_complex
    assert "herunterladen" in analysis.keywords_matched

def test_git_keywords():
    detector = ComplexityDetector(settings)

    messages = [Message(role="user", content="clone the chutes-api repo from github")]
    analysis = detector.analyze(messages)
    assert analysis.is_complex
```

## Related Specs

- `specs/80_debug_mode_flow_visualization.md` - Debug mode (NOT STARTED)
- `specs/88_chat_ui_improvements.md` - Chat UI improvements

NR_OF_TRIES: 1
