# Spec 101: Baseline LangChain Full Parity with Agent CLI

## Status: COMPLETE

## Context / Why

The baseline-agent-cli has capabilities that baseline-langchain currently lacks. For a fair competition and to demonstrate different architectural approaches, both baselines should be able to handle the same set of tasks.

## Current Feature Gap

| Feature | Agent CLI | LangChain | Gap |
|---------|-----------|-----------|-----|
| Simple chat (fast path) | ✅ | ✅ | - |
| Web search | ✅ | ✅ | - |
| Image generation | ✅ | ✅ | - |
| TTS | ✅ | ✅ | - |
| Code execution | ✅ (sandbox) | ✅ (in-process) | Different approach |
| **Git clone/repo ops** | ✅ | ❌ | **Missing** |
| **File system operations** | ✅ | ⚠️ Limited | **Needs work** |
| **Deep research** | ✅ | ⚠️ | **Needs testing** |
| **Artifact generation** | ✅ | ⚠️ | **Needs work** |
| **Screenshot/browser** | ✅ | ❌ | **Missing** |
| Memory integration | ✅ | ✅ | - |
| Complexity routing | ✅ | ✅ | - |

## Goals

- Add missing tools to baseline-langchain
- Ensure both baselines can handle the same demo prompts
- Document architectural differences (sandbox vs in-process)

## Functional Requirements

### FR-1: Git/Repository Operations Tool

```python
# baseline-langchain/janus_baseline_langchain/tools/git_tools.py

from langchain.tools import tool
import subprocess
import tempfile
import os

@tool
def clone_repository(url: str, branch: str = "main") -> str:
    """
    Clone a git repository and return the path.

    Args:
        url: The git repository URL (https://github.com/...)
        branch: Branch to clone (default: main)

    Returns:
        Path to the cloned repository
    """
    work_dir = tempfile.mkdtemp(prefix="janus_repo_")

    result = subprocess.run(
        ["git", "clone", "--depth", "1", "--branch", branch, url, work_dir],
        capture_output=True,
        text=True,
        timeout=120,
    )

    if result.returncode != 0:
        raise Exception(f"Git clone failed: {result.stderr}")

    return work_dir

@tool
def list_repository_files(repo_path: str, pattern: str = "*") -> str:
    """
    List files in a cloned repository.

    Args:
        repo_path: Path to the repository
        pattern: Glob pattern to filter files

    Returns:
        List of file paths
    """
    from pathlib import Path

    files = list(Path(repo_path).rglob(pattern))
    # Filter out .git directory
    files = [f for f in files if ".git" not in str(f)]

    return "\n".join(str(f) for f in files[:100])  # Limit output

@tool
def read_repository_file(file_path: str) -> str:
    """
    Read a file from a cloned repository.

    Args:
        file_path: Path to the file

    Returns:
        File contents (truncated if too long)
    """
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    # Truncate if too long
    if len(content) > 50000:
        content = content[:50000] + "\n\n[... truncated ...]"

    return content
```

### FR-2: Enhanced File System Tool

```python
# baseline-langchain/janus_baseline_langchain/tools/filesystem.py

@tool
def write_file(path: str, content: str) -> str:
    """
    Write content to a file and return it as an artifact.

    Args:
        path: Filename (will be created in artifacts directory)
        content: File content

    Returns:
        Artifact URL for download
    """
    artifacts_dir = Path(tempfile.gettempdir()) / "janus_artifacts"
    artifacts_dir.mkdir(exist_ok=True)

    file_path = artifacts_dir / path
    file_path.write_text(content)

    # Register as artifact for retrieval
    artifact_id = register_artifact(file_path)

    return f"File saved. Download: /api/artifacts/{artifact_id}"

@tool
def create_directory(path: str) -> str:
    """Create a directory for file operations."""
    work_dir = Path(tempfile.gettempdir()) / "janus_work" / path
    work_dir.mkdir(parents=True, exist_ok=True)
    return str(work_dir)
```

### FR-3: Browser/Screenshot Tool (Optional for LangChain)

```python
# baseline-langchain/janus_baseline_langchain/tools/browser.py

from playwright.async_api import async_playwright

@tool
async def take_screenshot(url: str) -> str:
    """
    Take a screenshot of a webpage.

    Args:
        url: URL to screenshot

    Returns:
        Path to screenshot image
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1920, "height": 1080})
        await page.goto(url, wait_until="networkidle")

        screenshot_path = f"/tmp/screenshot_{uuid4().hex[:8]}.png"
        await page.screenshot(path=screenshot_path, full_page=False)

        await browser.close()

    artifact_id = register_artifact(screenshot_path)
    return f"Screenshot saved. View: /api/artifacts/{artifact_id}"
```

### FR-4: Register All Tools

```python
# baseline-langchain/janus_baseline_langchain/tools/__init__.py

from .git_tools import clone_repository, list_repository_files, read_repository_file
from .filesystem import write_file, create_directory
from .browser import take_screenshot  # Optional

LANGCHAIN_TOOLS = [
    # Existing tools
    web_search,
    generate_image,
    text_to_speech,
    python_repl,
    deep_research,

    # New tools for parity
    clone_repository,
    list_repository_files,
    read_repository_file,
    write_file,
    create_directory,
    # take_screenshot,  # Optional - requires playwright
]
```

### FR-5: Update Agent to Use New Tools

```python
# In main.py or agent setup

def create_agent():
    tools = LANGCHAIN_TOOLS

    # Add memory tools if enabled
    if settings.enable_memory:
        tools.extend(memory_tools)

    agent = create_openai_tools_agent(
        llm=llm,
        tools=tools,
        prompt=agent_prompt,
    )

    return AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=15,  # Allow more iterations for complex tasks
    )
```

## Architectural Note

**Key difference between baselines:**

| Aspect | Agent CLI | LangChain |
|--------|-----------|-----------|
| Execution | Full Sandy sandbox (Firecracker VM) | In-process Python |
| Isolation | Complete OS-level | Process-level only |
| Git operations | Native git in sandbox | subprocess calls |
| File access | Full filesystem in sandbox | Limited temp directories |
| Security | High (sandboxed) | Medium (process isolation) |
| Cold start | 10-30s (sandbox creation) | <1s |
| Best for | Complex/untrusted tasks | Fast, simple tool use |

Both approaches are valid - Agent CLI is more capable but slower; LangChain is faster but more limited.

## Acceptance Criteria

- [ ] Git clone/repo operations work in LangChain baseline
- [ ] File write operations create downloadable artifacts
- [ ] Both baselines handle the same demo prompts
- [ ] Documentation explains architectural differences
- [ ] Tests verify parity for key use cases

## Files to Create/Modify

```
baseline-langchain/janus_baseline_langchain/
├── tools/
│   ├── __init__.py       # MODIFY: Export new tools
│   ├── git_tools.py      # NEW
│   ├── filesystem.py     # NEW/MODIFY
│   └── browser.py        # NEW (optional)
├── main.py               # MODIFY: Register tools
└── tests/
    └── test_tool_parity.py  # NEW
```

## Testing

```python
# Test that both baselines handle the same prompts

PARITY_TEST_PROMPTS = [
    "clone https://github.com/anthropics/anthropic-cookbook and list the files",
    "search the web for 'latest AI news' and summarize",
    "generate an image of a sunset over mountains",
    "write a Python script that prints hello world and save it to a file",
]

@pytest.mark.parametrize("prompt", PARITY_TEST_PROMPTS)
async def test_baseline_parity(prompt):
    # Test against both baselines
    response_cli = await call_baseline("agent-cli", prompt)
    response_langchain = await call_baseline("langchain", prompt)

    # Both should succeed (content may differ)
    assert response_cli.status == "success"
    assert response_langchain.status == "success"
```

## Related Specs

- Spec 79: Baseline LangChain Feature Parity (original)
- Spec 27: Baseline LangChain
- Spec 102: Core Demo Use Cases

NR_OF_TRIES: 1
