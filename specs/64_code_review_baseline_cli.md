# Spec 64: Code Review - Baseline Agent CLI

## Status: DRAFT

## Context / Why

The Baseline Agent CLI is the reference implementation that competes against user submissions. It includes complexity detection, Sandy sandbox integration, and agent orchestration. A thorough code review is needed to identify and fix:

- Bugs and edge cases
- Performance bottlenecks
- Design/architecture issues
- Naming inconsistencies
- Overly complicated solutions
- Security concerns
- Error handling gaps
- Logging deficiencies

## Scope

Review all code in `baseline-agent-cli/`:

```
baseline-agent-cli/
├── janus_baseline_agent_cli/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app, endpoints
│   ├── config.py                  # Settings/configuration
│   ├── models/
│   │   ├── __init__.py
│   │   └── openai.py              # Request/response models
│   └── services/
│       ├── __init__.py
│       ├── complexity.py          # Complexity detection
│       ├── llm.py                 # LLM client wrapper
│       ├── sandy.py               # Sandy sandbox integration
│       ├── streaming.py           # SSE streaming
│       ├── vision.py              # Image detection
│       └── response_processor.py  # Response processing
├── agent-pack/
│   ├── bootstrap.sh               # Sandbox initialization
│   ├── run_agent.py               # Agent runner script
│   └── prompts/
│       └── system.md              # Agent system prompt
└── tests/
```

## Review Checklist

### 1. Configuration (config.py)

- [ ] **Validation**: All settings validated
- [ ] **Naming**: Consistent BASELINE_* prefix
- [ ] **Defaults**: Sensible defaults for all settings
- [ ] **Secrets**: API keys not logged
- [ ] **Model selection**: Model names validated
- [ ] **Sandy config**: Sandbox settings complete

### 2. Models (models/*.py)

- [ ] **OpenAI compatibility**: Request/response match spec
- [ ] **Message types**: All content types supported
- [ ] **Streaming**: Delta models for streaming
- [ ] **Artifacts**: Artifact model complete
- [ ] **Validation**: Field validators where needed

### 3. Complexity Detection (services/complexity.py)

- [ ] **Keyword matching**: Complete keyword list
- [ ] **Multimodal detection**: Image/audio/video detected
- [ ] **Edge cases**: Empty messages, unicode, etc.
- [ ] **Performance**: Fast first pass (<10ms)
- [ ] **Logging**: Detection reasons logged
- [ ] **Testability**: Easy to unit test

### 4. LLM Second Pass (services/llm.py)

- [ ] **Timeout**: 3 second timeout enforced
- [ ] **Fallback**: Falls back on error
- [ ] **Model**: Uses fast model (GLM-4.7-Flash)
- [ ] **Tool calling**: use_agent tool parsed correctly
- [ ] **Error handling**: API errors caught
- [ ] **Caching**: Repeated queries cached

### 5. Sandy Integration (services/sandy.py)

- [ ] **Sandbox creation**: Proper API calls
- [ ] **File operations**: Read/write work
- [ ] **Exec**: Command execution works
- [ ] **Cleanup**: Sandbox terminated on completion/error
- [ ] **Timeout**: Job timeout enforced
- [ ] **Error handling**: Sandy errors propagated
- [ ] **Resource limits**: Limits configured

### 6. Streaming (services/streaming.py)

- [ ] **SSE format**: Correct format
- [ ] **Keep-alives**: Sent during idle
- [ ] **Reasoning content**: Tool steps in reasoning_content
- [ ] **Final chunk**: [DONE] marker sent
- [ ] **Usage**: Token usage tracked
- [ ] **Errors**: Errors streamed properly

### 7. Agent Pack (agent-pack/)

- [ ] **Bootstrap**: Script runs successfully
- [ ] **Dependencies**: All deps installed
- [ ] **System prompt**: Clear and effective
- [ ] **Model docs**: Documentation complete
- [ ] **Run script**: Agent starts correctly

### 8. Main Application (main.py)

- [ ] **Endpoint routing**: All paths correct
- [ ] **Middleware**: Logging, CORS, etc.
- [ ] **Error handlers**: Global error handling
- [ ] **Startup/shutdown**: Lifecycle hooks
- [ ] **Health check**: /health works

### 9. General Code Quality

- [ ] **DRY**: No duplicated code
- [ ] **Complexity**: Functions not too long
- [ ] **Type hints**: Complete type hints
- [ ] **Docstrings**: Public functions documented
- [ ] **Constants**: Named constants used
- [ ] **Async**: Proper async/await patterns
- [ ] **Tests**: Good test coverage

## Common Issues to Look For

### Performance
- Blocking I/O in async code
- Repeated API calls
- Memory leaks in streaming
- Slow complexity detection

### Security
- Command injection in sandbox
- Path traversal
- API keys exposed
- Untrusted input executed

### Reliability
- Sandbox not cleaned up
- Timeout not enforced
- Race conditions
- Resource exhaustion

### Maintainability
- God objects/functions
- Unclear naming
- Missing error context
- Tight coupling

## Improvement Actions

For each issue found:

1. **Document**: File, line, issue description
2. **Categorize**: Bug, Performance, Design, Naming, Complexity
3. **Prioritize**: Critical, High, Medium, Low
4. **Fix**: Implement the fix
5. **Test**: Add/update tests
6. **Log**: Add logging if needed

## Deliverables

- [ ] All identified issues fixed
- [ ] Comprehensive logging added
- [ ] Tests updated
- [ ] No regression
- [ ] Documentation current

## Acceptance Criteria

- [ ] Zero linting errors
- [ ] All tests pass
- [ ] No security issues
- [ ] Complexity detection accurate
- [ ] Sandy integration reliable
- [ ] Streaming works correctly
