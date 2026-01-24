# Spec 26: Rename Baseline to baseline-agent-cli

## Status: COMPLETE

## Context / Why

The current "baseline" folder name is ambiguous. As Janus grows, there will be multiple baseline implementations:
- `baseline-agent-cli` - Current implementation using Claude Code CLI agent in Sandy sandbox
- `baseline-n8n` - Future: n8n workflow-based implementation
- `baseline-langchain` - Future: LangChain-based implementation

Renaming now establishes a clear naming convention and makes it obvious what approach each baseline uses.

## Goals

- Rename `baseline/` folder to `baseline-agent-cli/`
- Update all internal imports from `janus_baseline` to `janus_baseline_agent_cli`
- Update all configuration and deployment references
- Maintain backward compatibility where possible

## Non-Goals

- Changing functionality of the baseline
- Creating new baseline implementations (separate specs)
- Changing the external API contract

## Functional Requirements

### FR-1: Rename Directory Structure

```
baseline/                    →  baseline-agent-cli/
├── janus_baseline/          →  ├── janus_baseline_agent_cli/
│   ├── __init__.py          →  │   ├── __init__.py
│   ├── config.py            →  │   ├── config.py
│   ├── main.py              →  │   ├── main.py
│   ├── models/              →  │   ├── models/
│   └── services/            →  │   └── services/
├── agent-pack/              →  ├── agent-pack/
├── tests/                   →  ├── tests/
├── pyproject.toml           →  ├── pyproject.toml
└── README.md                →  └── README.md
```

### FR-2: Update pyproject.toml

```toml
[project]
name = "janus-baseline-agent-cli"

[project.scripts]
janus-baseline-agent-cli = "janus_baseline_agent_cli.main:main"
```

### FR-3: Update Python Imports

All files in the package must update imports:

```python
# Before
from janus_baseline.config import Settings
from janus_baseline.models import Message
from janus_baseline.services import LLMService

# After
from janus_baseline_agent_cli.config import Settings
from janus_baseline_agent_cli.models import Message
from janus_baseline_agent_cli.services import LLMService
```

Files to update:
- `janus_baseline_agent_cli/__init__.py`
- `janus_baseline_agent_cli/main.py`
- `janus_baseline_agent_cli/config.py`
- `janus_baseline_agent_cli/services/__init__.py`
- `janus_baseline_agent_cli/services/complexity.py`
- `janus_baseline_agent_cli/services/llm.py`
- `janus_baseline_agent_cli/services/sandy.py`
- `janus_baseline_agent_cli/models/__init__.py`
- All test files in `tests/`

### FR-4: Update Render Configuration

Update `render.yaml`:

```yaml
services:
  - type: web
    name: janus-baseline-agent-cli
    runtime: python
    rootDir: baseline-agent-cli
    buildCommand: pip install -e .
    startCommand: uvicorn janus_baseline_agent_cli.main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: BASELINE_HOST
        value: 0.0.0.0
      - key: BASELINE_PORT
        fromService:
          type: web
          name: janus-baseline-agent-cli
          property: port
```

### FR-5: Update Gateway References

Update gateway configuration for baseline URL:

```python
# In gateway/janus_gateway/config.py or equivalent
baseline_url: str = Field(
    default="https://janus-baseline-agent-cli.onrender.com",
    description="URL of the baseline agent CLI implementation"
)
```

### FR-6: Update Environment Variable Prefix

Change from `BASELINE_` to `BASELINE_AGENT_CLI_`:

```python
# In config.py
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="BASELINE_AGENT_CLI_",
        ...
    )
```

### FR-7: Update Documentation

- Update `README.md` in root and baseline-agent-cli folder
- Update `docs/architecture.md`
- Update `docs/runbook.md`
- Update spec files that reference "baseline"

### FR-8: Update Tests

Gateway tests that reference baseline:

```python
# Before
monkeypatch.setenv("BASELINE_URL", "janus-baseline:10000")
assert _load_baseline_url() == "http://janus-baseline:10000"

# After
monkeypatch.setenv("BASELINE_URL", "janus-baseline-agent-cli:10000")
assert _load_baseline_url() == "http://janus-baseline-agent-cli:10000"
```

## Non-Functional Requirements

### NFR-1: Zero Downtime

- Render allows service renames
- DNS changes may take a few minutes
- Gateway should handle both old and new URLs during transition

### NFR-2: Git History

- Use `git mv` to preserve file history
- Single commit for all renames

## Acceptance Criteria

- [ ] Directory renamed from `baseline/` to `baseline-agent-cli/`
- [ ] Python package renamed from `janus_baseline` to `janus_baseline_agent_cli`
- [ ] All imports updated and working
- [ ] `pytest` passes in baseline-agent-cli folder
- [ ] `mypy` passes (if configured)
- [ ] Render deployment succeeds
- [ ] Gateway can reach renamed baseline
- [ ] Chat functionality works end-to-end
- [ ] Documentation updated

## Implementation Script

```bash
#!/bin/bash
# Run from janus-poc root

# 1. Rename directory
git mv baseline baseline-agent-cli

# 2. Rename Python package
git mv baseline-agent-cli/janus_baseline baseline-agent-cli/janus_baseline_agent_cli

# 3. Update imports in all Python files
find baseline-agent-cli -name "*.py" -exec sed -i 's/janus_baseline/janus_baseline_agent_cli/g' {} \;

# 4. Update pyproject.toml
sed -i 's/janus-baseline/janus-baseline-agent-cli/g' baseline-agent-cli/pyproject.toml
sed -i 's/janus_baseline/janus_baseline_agent_cli/g' baseline-agent-cli/pyproject.toml

# 5. Update render.yaml
sed -i 's/janus-baseline/janus-baseline-agent-cli/g' render.yaml
sed -i 's/janus_baseline/janus_baseline_agent_cli/g' render.yaml
sed -i 's/rootDir: baseline/rootDir: baseline-agent-cli/g' render.yaml

# 6. Update gateway tests
find gateway -name "*.py" -exec sed -i 's/janus-baseline/janus-baseline-agent-cli/g' {} \;

# 7. Verify
cd baseline-agent-cli
pip install -e .
pytest
```

## Files to Modify

- `baseline/` → `baseline-agent-cli/` (directory rename)
- `baseline/janus_baseline/` → `baseline-agent-cli/janus_baseline_agent_cli/` (package rename)
- All `.py` files in the package (import updates)
- `render.yaml`
- `gateway/tests/test_competitor_registry.py`
- `bench/janus_bench/config.py`
- `bench/janus_bench/cli.py`
- Documentation files

## Rollback Plan

If issues arise:
1. `git revert` the rename commit
2. Redeploy original baseline service on Render
3. Update gateway to point to original URL

## Related Specs

- Spec 27: Baseline-LangChain (will follow this naming convention)
- Spec 21: Enhanced Baseline Implementation
