# Spec 76: Memory Investigation Tool

**Status:** NOT STARTED
**Priority:** Medium
**Complexity:** Medium
**Prerequisites:** Spec 72, Spec 73, Spec 74

---

## Overview

Extend the memory system with an `investigate_memory` tool that allows the agent to retrieve and search through full memory content. When the agent determines it needs more context from memories, it can call this tool with a list of memory IDs to get the complete memory text for deeper research.

---

## Functional Requirements

### FR-1: Investigate Memory Tool Definition

Add a new tool to the agent's toolkit that fetches full memory content.

**Tool Schema:**
```json
{
  "name": "investigate_memory",
  "description": "Retrieve full content of specific memories for deeper investigation. Use this when the memory captions in the notice section aren't providing enough context and you need to understand the full details.",
  "parameters": {
    "type": "object",
    "properties": {
      "memory_ids": {
        "type": "array",
        "items": { "type": "string" },
        "description": "List of memory IDs to retrieve (e.g., ['mem_abc123', 'mem_def456'])"
      },
      "query": {
        "type": "string",
        "description": "Optional: What you're looking for in these memories"
      }
    },
    "required": ["memory_ids"]
  }
}
```

### FR-2: Tool Implementation (baseline-agent-cli)

**Sandy Integration:**

The Sandy agent already supports custom tools. Add this tool to the agent's toolkit.

```python
# services/tools/memory_tool.py

from typing import Any
from pydantic import BaseModel, Field


class InvestigateMemoryInput(BaseModel):
    memory_ids: list[str] = Field(
        description="List of memory IDs to retrieve"
    )
    query: str | None = Field(
        default=None,
        description="Optional: What you're looking for in these memories"
    )


async def investigate_memory(
    memory_ids: list[str],
    user_id: str,
    memory_service_url: str,
    query: str | None = None,
) -> str:
    """
    Retrieve full memory content for investigation.
    Returns formatted memory content for the agent to analyze.
    """
    import httpx

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{memory_service_url}/memories/full",
                params={
                    "user_id": user_id,
                    "ids": ",".join(memory_ids),
                },
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()

        memories = data.get("memories", [])
        if not memories:
            return "No memories found with the provided IDs."

        # Format memories for agent consumption
        formatted = ["## Retrieved Memories\n"]
        for mem in memories:
            formatted.append(f"### [{mem['id']}] {mem['caption']}")
            formatted.append(f"**Created:** {mem['created_at']}")
            formatted.append(f"\n{mem['full_text']}\n")

        if query:
            formatted.insert(0, f"*Investigating: {query}*\n")

        return "\n".join(formatted)

    except Exception as exc:
        return f"Error retrieving memories: {str(exc)}"
```

### FR-3: Tool Registration with Sandy

Sandy needs to know about this tool and how to call it.

```python
# In sandy configuration or tool registration

MEMORY_TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "investigate_memory",
        "description": (
            "Retrieve full content of specific memories for deeper investigation. "
            "Use this when the memory captions in the notice section aren't providing "
            "enough context and you need to understand the full details. "
            "Memory IDs are shown in square brackets in the memory references section."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "memory_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of memory IDs (e.g., 'mem_abc123')"
                },
                "query": {
                    "type": "string",
                    "description": "What specific information you're looking for"
                }
            },
            "required": ["memory_ids"]
        }
    }
}
```

### FR-4: Tool Implementation (baseline-langchain)

For LangChain, create a proper LangChain tool.

```python
# services/tools/memory_tool.py

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
import httpx


class InvestigateMemoryInput(BaseModel):
    memory_ids: list[str] = Field(description="List of memory IDs to retrieve")
    query: str | None = Field(default=None, description="What to look for")


class InvestigateMemoryTool(BaseTool):
    name: str = "investigate_memory"
    description: str = (
        "Retrieve full content of specific memories for deeper investigation. "
        "Use when memory captions don't provide enough context. "
        "Pass memory IDs from the [mem_xxx] references in the notice section."
    )
    args_schema: type[BaseModel] = InvestigateMemoryInput

    user_id: str
    memory_service_url: str

    def _run(self, memory_ids: list[str], query: str | None = None) -> str:
        import asyncio
        return asyncio.run(self._arun(memory_ids, query))

    async def _arun(self, memory_ids: list[str], query: str | None = None) -> str:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.memory_service_url}/memories/full",
                    params={
                        "user_id": self.user_id,
                        "ids": ",".join(memory_ids),
                    },
                    timeout=10.0,
                )
                response.raise_for_status()
                data = response.json()

            memories = data.get("memories", [])
            if not memories:
                return "No memories found with the provided IDs."

            formatted = ["## Retrieved Memories\n"]
            for mem in memories:
                formatted.append(f"### [{mem['id']}] {mem['caption']}")
                formatted.append(f"**Created:** {mem['created_at']}")
                formatted.append(f"\n{mem['full_text']}\n")

            if query:
                formatted.insert(0, f"*Investigating: {query}*\n")

            return "\n".join(formatted)

        except Exception as exc:
            return f"Error retrieving memories: {str(exc)}"
```

### FR-5: Conditional Tool Availability

The `investigate_memory` tool should ONLY be available when:
1. Memory feature is enabled (`enable_memory=True`)
2. User ID is provided
3. Memory references were injected into the prompt

```python
# When creating agent tools
tools = [
    # ... existing tools ...
]

if request.enable_memory and request.user_id and has_memory_context:
    tools.append(
        InvestigateMemoryTool(
            user_id=request.user_id,
            memory_service_url=settings.memory_service_url,
        )
    )
```

### FR-6: Alternative: File-Based Memory Research

For more complex investigations, save memories to a temporary folder and let the agent search through them.

```python
async def create_memory_research_folder(
    user_id: str,
    memory_ids: list[str],
    memory_service_url: str,
) -> str:
    """
    Save full memories to a temporary folder for agent research.
    Returns the folder path.
    """
    import tempfile
    import json
    from pathlib import Path

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{memory_service_url}/memories/full",
            params={
                "user_id": user_id,
                "ids": ",".join(memory_ids),
            },
        )
        data = response.json()

    # Create temp directory
    temp_dir = tempfile.mkdtemp(prefix="janus_memories_")
    memories_path = Path(temp_dir)

    # Write each memory as a separate file
    for mem in data.get("memories", []):
        mem_file = memories_path / f"{mem['id']}.md"
        mem_file.write_text(
            f"# {mem['caption']}\n\n"
            f"**ID:** {mem['id']}\n"
            f"**Created:** {mem['created_at']}\n\n"
            f"## Full Content\n\n{mem['full_text']}"
        )

    # Write index file
    index_file = memories_path / "INDEX.md"
    index_content = ["# Memory Index\n"]
    for mem in data.get("memories", []):
        index_content.append(f"- [{mem['id']}]({mem['id']}.md): {mem['caption']}")
    index_file.write_text("\n".join(index_content))

    return str(memories_path)
```

Then tell the agent:
```
I've saved the requested memories to {folder_path}/.
You can use file reading tools to search through them.
Each memory is saved as a separate .md file.
See INDEX.md for a list of all memories.
```

---

## Technical Requirements

### TR-1: Files to Create

| File | Purpose |
|------|---------|
| `baseline-agent-cli/janus_baseline_agent_cli/tools/memory.py` | Memory tool for Sandy |
| `baseline-langchain/janus_baseline_langchain/tools/memory.py` | Memory tool for LangChain |

### TR-2: Files to Modify

| File | Changes |
|------|---------|
| `baseline-agent-cli/janus_baseline_agent_cli/services/sandy.py` | Register memory tool |
| `baseline-langchain/janus_baseline_langchain/agent.py` | Add memory tool to agent |
| `memory-service/memory_service/main.py` | Ensure `/memories/full` endpoint exists |

---

## Usage Flow

```
1. User sends message: "What's my dog's name again?"

2. Memory context injected:
   ______ Notice ______
   <memory-references>
   - [mem_abc123] User has a dog named Max (golden retriever)
   - [mem_def456] User got Max 3 years ago
   </memory-references>
   ____________________
   What's my dog's name again?

3. Agent reads context, answers directly: "Your dog's name is Max!"

4. OR if agent needs more detail:
   Agent calls: investigate_memory(["mem_abc123", "mem_def456"], "dog details")

5. Tool returns full memory content

6. Agent synthesizes response with full context
```

---

## Acceptance Criteria

- [ ] `investigate_memory` tool is defined and registered
- [ ] Tool only appears when memory is enabled
- [ ] Tool correctly fetches full memory content
- [ ] Tool returns formatted, readable content
- [ ] Agent can call tool and use results in response
- [ ] Error handling for missing memories / service errors

---

## Testing Checklist

- [ ] Tool appears in agent's available tools (when memory enabled)
- [ ] Tool does NOT appear when memory disabled
- [ ] Tool successfully retrieves full memory content
- [ ] Tool handles non-existent memory IDs gracefully
- [ ] Tool handles memory service errors gracefully
- [ ] Agent uses tool results appropriately in response
- [ ] File-based alternative works (if implemented)

---

## Notes

- This is a "deeper dive" capability - most queries will be answered from captions alone
- The tool should be used sparingly - it adds latency
- Consider rate limiting tool calls (max 1-2 per conversation turn)
- File-based approach is useful for very complex research scenarios
- Memory IDs in captions make them easy for agent to reference
