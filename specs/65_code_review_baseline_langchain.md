# Spec 65: Code Review - Baseline LangChain

## Status: DRAFT

## Context / Why

The Baseline LangChain is an alternative baseline implementation using LangChain for agent orchestration. It provides different tools and capabilities compared to the CLI baseline. A thorough code review is needed to identify and fix:

- Bugs and edge cases
- Performance bottlenecks
- Design/architecture issues
- Naming inconsistencies
- Overly complicated solutions
- Security concerns
- Error handling gaps
- Logging deficiencies

## Scope

Review all code in `baseline-langchain/`:

```
baseline-langchain/
├── janus_baseline_langchain/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app
│   ├── config.py                  # Settings
│   ├── agent.py                   # LangChain agent setup
│   ├── models/
│   │   └── openai.py              # Request/response models
│   └── tools/
│       ├── __init__.py
│       ├── web_search.py          # Tavily search tool
│       ├── image_generation.py    # Image gen tool
│       ├── text_to_speech.py      # TTS tool
│       └── code_execution.py      # Code exec tool
└── tests/
```

## Review Checklist

### 1. Configuration (config.py)

- [ ] **Naming**: BASELINE_LANGCHAIN_* prefix
- [ ] **API keys**: All required keys configurable
- [ ] **Defaults**: Sensible defaults
- [ ] **Validation**: Types validated
- [ ] **Logging**: Config logged at startup (sans secrets)

### 2. Agent Setup (agent.py)

- [ ] **LLM config**: Model configured correctly
- [ ] **Tool binding**: Tools bound properly
- [ ] **Memory**: Conversation memory if needed
- [ ] **Streaming**: Stream events handled
- [ ] **Max iterations**: Limit enforced
- [ ] **Error handling**: Agent errors caught

### 3. Tools (tools/*.py)

#### Web Search (web_search.py)
- [ ] **API integration**: Tavily API called correctly
- [ ] **Result parsing**: Results extracted properly
- [ ] **Error handling**: API errors caught
- [ ] **Rate limiting**: Limits respected
- [ ] **Timeout**: Request timeout set

#### Image Generation (image_generation.py)
- [ ] **API integration**: Chutes API called
- [ ] **Prompt handling**: Prompt passed correctly
- [ ] **Response parsing**: Image URL extracted
- [ ] **Error handling**: Generation errors caught
- [ ] **Size options**: Resolution options work

#### Text-to-Speech (text_to_speech.py)
- [ ] **API integration**: Kokoro/TTS API called
- [ ] **Voice selection**: Voices work
- [ ] **Audio format**: Correct format returned
- [ ] **Base64 encoding**: Audio encoded properly
- [ ] **Error handling**: TTS errors caught

#### Code Execution (code_execution.py)
- [ ] **Sandbox**: Code runs in sandbox
- [ ] **Security**: No arbitrary code execution
- [ ] **Timeout**: Execution timeout
- [ ] **Output capture**: stdout/stderr captured
- [ ] **Error handling**: Execution errors caught

### 4. Streaming (main.py)

- [ ] **LangChain events**: Events streamed
- [ ] **OpenAI format**: Converted to OpenAI format
- [ ] **Reasoning content**: Tool steps in reasoning
- [ ] **Final response**: Content in content field
- [ ] **Keep-alives**: Sent during processing
- [ ] **Error streaming**: Errors handled

### 5. Models (models/openai.py)

- [ ] **Request model**: Matches OpenAI spec
- [ ] **Response model**: Matches OpenAI spec
- [ ] **Streaming delta**: Delta models correct
- [ ] **Tool calls**: Tool call format correct
- [ ] **Validation**: Field validators work

### 6. Main Application (main.py)

- [ ] **Endpoints**: All routes correct
- [ ] **Middleware**: Logging, errors, etc.
- [ ] **Health check**: /health works
- [ ] **CORS**: Headers if needed
- [ ] **Startup**: Initialization correct

### 7. General Code Quality

- [ ] **DRY**: No duplication
- [ ] **Complexity**: Functions not too long
- [ ] **Type hints**: Complete
- [ ] **Docstrings**: Public functions documented
- [ ] **Imports**: Organized
- [ ] **Tests**: Good coverage

## Common Issues to Look For

### Performance
- Blocking calls in async handlers
- Tool calls not parallelized
- Memory leaks
- Slow tool execution

### Security
- Tool injection
- Arbitrary code execution
- API key exposure
- Input not validated

### LangChain Specific
- Deprecated APIs used
- Stream events not handled
- Callback errors not caught
- Memory overflow

### Reliability
- Tool failures not handled
- Timeout not enforced
- Agent stuck in loop
- Resource cleanup missing

## Improvement Actions

For each issue found:

1. **Document**: File, line, issue
2. **Categorize**: Bug, Performance, Design, Naming, Complexity
3. **Prioritize**: Critical, High, Medium, Low
4. **Fix**: Implement fix
5. **Test**: Add/update tests
6. **Log**: Add logging

## Deliverables

- [ ] All issues fixed
- [ ] Logging improved
- [ ] Tests updated
- [ ] No regression
- [ ] Documentation current

## Acceptance Criteria

- [ ] Zero linting errors
- [ ] All tests pass
- [ ] Tools work correctly
- [ ] Streaming works
- [ ] Agent doesn't hang
- [ ] Error handling complete
