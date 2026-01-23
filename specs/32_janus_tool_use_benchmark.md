# Spec 32: Janus Tool Use Benchmark

## Status: COMPLETE

## Context / Why

Effective tool use is a critical capability for Janus intelligence implementations. Unlike standard chat, complex tasks require calling APIs, executing code, fetching data, and coordinating multiple tools. The Janus Tool Use Benchmark evaluates:

1. **Function calling** - Correctly invoking tools with proper parameters
2. **Tool selection** - Choosing the right tool for the task
3. **Tool chaining** - Coordinating multiple tools in sequence
4. **Error handling** - Recovering from tool failures
5. **Code execution** - Running code in the sandbox

This benchmark directly tests whether implementations can effectively use the platform services (sandbox, search, proxy, inference) that are available to them.

## Goals

- Measure function calling accuracy and parameter correctness
- Evaluate tool selection and orchestration
- Test code execution in Sandy sandbox
- Assess error handling and recovery
- Provide reproducible scores for competition

## Non-Goals

- Testing research quality (covered by janus_research)
- Testing multimodal capabilities (covered by janus_multimodal)
- Testing raw coding ability (covered by HumanEval, LiveCodeBench)

## Functional Requirements

### FR-1: Task Types

The benchmark includes four task types:

#### 1. Function Calling (25 items)

Test correct API invocation:

```json
{
  "id": "func_001",
  "task_type": "function_calling",
  "description": "Get the current weather in Tokyo",
  "available_tools": [
    {
      "type": "function",
      "function": {
        "name": "get_weather",
        "description": "Get current weather for a location",
        "parameters": {
          "type": "object",
          "properties": {
            "location": {"type": "string", "description": "City name"},
            "units": {"type": "string", "enum": ["celsius", "fahrenheit"]}
          },
          "required": ["location"]
        }
      }
    }
  ],
  "expected_call": {
    "function": "get_weather",
    "arguments": {"location": "Tokyo"}
  },
  "evaluation": {
    "type": "function_call_match",
    "allow_extra_args": true
  }
}
```

#### 2. Tool Selection (20 items)

Test choosing the right tool:

```json
{
  "id": "select_001",
  "task_type": "tool_selection",
  "description": "I need to calculate the compound interest on $10,000 at 5% for 10 years",
  "available_tools": [
    {"name": "calculator", "description": "Basic math operations"},
    {"name": "search", "description": "Web search"},
    {"name": "code_execute", "description": "Run Python code"},
    {"name": "fetch_url", "description": "Fetch web page content"}
  ],
  "expected_tools": ["calculator"],
  "acceptable_alternatives": ["code_execute"],
  "evaluation": {
    "type": "tool_choice",
    "score_alternatives": 0.8
  }
}
```

#### 3. Tool Chaining (20 items)

Test multi-step tool coordination:

```json
{
  "id": "chain_001",
  "task_type": "tool_chaining",
  "description": "Find the current stock price of Apple and calculate what $1000 would have grown to if invested 5 years ago",
  "available_tools": [
    {"name": "search", "description": "Web search"},
    {"name": "fetch_url", "description": "Fetch web page"},
    {"name": "code_execute", "description": "Run calculations"}
  ],
  "expected_sequence": ["search", "code_execute"],
  "evaluation": {
    "type": "sequence_match",
    "partial_credit": true,
    "verify_final_answer": true
  }
}
```

#### 4. Code Execution (15 items)

Test sandbox usage:

```json
{
  "id": "code_001",
  "task_type": "code_execution",
  "description": "Write and run Python code to find all prime numbers under 100",
  "expected_output_contains": ["2", "3", "5", "7", "97"],
  "evaluation": {
    "type": "code_output_match",
    "verify_correctness": true,
    "check_efficiency": false
  }
}
```

### FR-2: Tool Simulation Layer

For benchmarking, we simulate tool responses:

```python
class ToolSimulator:
    """Simulate tool responses for benchmark evaluation."""

    TOOL_RESPONSES = {
        "get_weather": lambda args: {
            "location": args.get("location"),
            "temperature": 22,
            "condition": "sunny",
            "units": args.get("units", "celsius")
        },
        "search": lambda args: {
            "query": args.get("query"),
            "results": [
                {"title": "Result 1", "url": "https://example.com/1", "snippet": "..."},
                {"title": "Result 2", "url": "https://example.com/2", "snippet": "..."},
            ]
        },
        "calculator": lambda args: {
            "expression": args.get("expression"),
            "result": eval(args.get("expression", "0"))  # Simplified
        }
    }

    def execute(self, tool_name: str, arguments: dict) -> dict:
        if tool_name in self.TOOL_RESPONSES:
            return {"success": True, "result": self.TOOL_RESPONSES[tool_name](arguments)}
        return {"success": False, "error": f"Unknown tool: {tool_name}"}
```

### FR-3: Evaluation Methods

#### Function Call Matching

```python
def evaluate_function_call(
    expected: dict,
    actual: dict,
    allow_extra_args: bool = True
) -> tuple[float, str]:
    """
    Evaluate function call correctness.

    Returns:
        (score, reasoning)
    """
    # Check function name
    if expected.get("function") != actual.get("function"):
        return 0.0, f"Wrong function: expected {expected['function']}, got {actual.get('function')}"

    # Check required arguments
    expected_args = expected.get("arguments", {})
    actual_args = actual.get("arguments", {})

    missing = []
    wrong = []

    for key, value in expected_args.items():
        if key not in actual_args:
            missing.append(key)
        elif actual_args[key] != value:
            # Fuzzy match for strings
            if isinstance(value, str) and isinstance(actual_args[key], str):
                if value.lower() not in actual_args[key].lower():
                    wrong.append(f"{key}: expected '{value}', got '{actual_args[key]}'")
            else:
                wrong.append(f"{key}: expected {value}, got {actual_args[key]}")

    if missing:
        return 0.3, f"Missing arguments: {missing}"

    if wrong:
        return 0.6, f"Wrong argument values: {wrong}"

    # Check for unexpected arguments
    if not allow_extra_args:
        extra = set(actual_args.keys()) - set(expected_args.keys())
        if extra:
            return 0.9, f"Extra arguments (minor penalty): {extra}"

    return 1.0, "Perfect match"
```

#### Tool Selection Scoring

```python
def evaluate_tool_selection(
    expected_tools: list[str],
    actual_tools: list[str],
    acceptable_alternatives: list[str] | None = None
) -> tuple[float, str]:
    """Evaluate tool selection."""
    acceptable = set(expected_tools + (acceptable_alternatives or []))

    if not actual_tools:
        return 0.0, "No tools selected"

    # Check primary tool
    if actual_tools[0] in expected_tools:
        return 1.0, "Correct tool selected"

    if actual_tools[0] in acceptable:
        return 0.8, f"Acceptable alternative: {actual_tools[0]}"

    # Check if any selected tool is acceptable
    for tool in actual_tools:
        if tool in acceptable:
            return 0.5, f"Found acceptable tool in selection: {tool}"

    return 0.0, f"Wrong tools selected: {actual_tools}"
```

### FR-4: Adapter Implementation

```python
# backend/app/benchmarks/adapters/janus_tool_use.py

import json
import time
from typing import AsyncIterator
from pathlib import Path

from app.benchmarks.base import BenchmarkAdapter, ItemResult
from app.benchmarks.registry import register_adapter


@register_adapter("janus_tool_use")
class JanusToolUseAdapter(BenchmarkAdapter):
    """Benchmark for tool use and function calling capabilities."""

    def __init__(self, client, model_slug, judge_client=None):
        super().__init__(client, model_slug, judge_client)
        self._items: list[dict] = []

    def get_name(self) -> str:
        return "janus_tool_use"

    def get_display_name(self) -> str:
        return "Janus Tool Use"

    def get_category(self) -> str:
        return "Janus Intelligence"

    async def get_total_items(self) -> int:
        if not self._items:
            await self.preload()
        return len(self._items)

    async def preload(self) -> None:
        data_path = Path(__file__).parent.parent / "data" / "janus" / "tool_use_items.json"
        if data_path.exists():
            with open(data_path) as f:
                data = json.load(f)
                self._items = data.get("items", [])

    async def enumerate_items(self) -> AsyncIterator[str]:
        if not self._items:
            await self.preload()
        for item in self._items:
            yield item["id"]

    async def evaluate_item(self, item_id: str) -> ItemResult:
        """Evaluate a single tool use task."""
        item = next((i for i in self._items if i["id"] == item_id), None)
        if not item:
            return ItemResult(item_id=item_id, error=f"Item {item_id} not found")

        task_type = item.get("task_type")

        # Build request with tools if available
        messages = [{"role": "user", "content": item["description"]}]
        tools = item.get("available_tools")

        try:
            start_time = time.time()

            # Make request with tools
            response = await self.client.chat_completion(
                model=self.model_slug,
                messages=messages,
                tools=tools,
                tool_choice="auto" if tools else None,
                temperature=0.0,
            )

            latency_ms = int((time.time() - start_time) * 1000)

            # Extract tool calls from response
            tool_calls = []
            message = response.choices[0].message
            if hasattr(message, 'tool_calls') and message.tool_calls:
                for tc in message.tool_calls:
                    tool_calls.append({
                        "function": tc.function.name,
                        "arguments": json.loads(tc.function.arguments)
                    })

            response_text = message.content or ""

        except Exception as e:
            return ItemResult(
                item_id=item_id,
                prompt=item["description"],
                error=str(e)
            )

        # Evaluate based on task type
        if task_type == "function_calling":
            score, reasoning = self._evaluate_function_call(item, tool_calls)
        elif task_type == "tool_selection":
            score, reasoning = self._evaluate_tool_selection(item, tool_calls)
        elif task_type == "tool_chaining":
            score, reasoning = self._evaluate_tool_chain(item, tool_calls)
        elif task_type == "code_execution":
            score, reasoning = self._evaluate_code_execution(item, response_text, tool_calls)
        else:
            score, reasoning = 0.0, f"Unknown task type: {task_type}"

        return ItemResult(
            item_id=item_id,
            item_hash=self.compute_item_hash(item),
            prompt=item["description"],
            response=response_text,
            is_correct=score >= 0.7,
            score=score,
            judge_output={"reasoning": reasoning, "tool_calls": tool_calls},
            latency_ms=latency_ms,
            input_tokens=response.usage.prompt_tokens if response.usage else None,
            output_tokens=response.usage.completion_tokens if response.usage else None,
        )

    def _evaluate_function_call(self, item: dict, tool_calls: list) -> tuple[float, str]:
        expected = item.get("expected_call", {})
        allow_extra = item.get("evaluation", {}).get("allow_extra_args", True)

        if not tool_calls:
            return 0.0, "No function call made"

        # Check first tool call
        actual = tool_calls[0]
        return evaluate_function_call(expected, actual, allow_extra)

    def _evaluate_tool_selection(self, item: dict, tool_calls: list) -> tuple[float, str]:
        expected = item.get("expected_tools", [])
        alternatives = item.get("acceptable_alternatives", [])

        actual_tools = [tc.get("function") for tc in tool_calls]
        return evaluate_tool_selection(expected, actual_tools, alternatives)

    def _evaluate_tool_chain(self, item: dict, tool_calls: list) -> tuple[float, str]:
        expected_seq = item.get("expected_sequence", [])
        actual_seq = [tc.get("function") for tc in tool_calls]

        if not actual_seq:
            return 0.0, "No tools called"

        # Check sequence match
        matches = 0
        for i, expected_tool in enumerate(expected_seq):
            if i < len(actual_seq) and actual_seq[i] == expected_tool:
                matches += 1

        if matches == len(expected_seq):
            return 1.0, "Perfect sequence match"

        partial = matches / len(expected_seq)
        return partial, f"Partial sequence match: {matches}/{len(expected_seq)}"

    def _evaluate_code_execution(
        self,
        item: dict,
        response: str,
        tool_calls: list
    ) -> tuple[float, str]:
        """Evaluate code execution tasks."""
        expected_outputs = item.get("expected_output_contains", [])

        # Check if code was executed
        code_executed = any(
            tc.get("function") in ["code_execute", "execute_code", "run_code"]
            for tc in tool_calls
        )

        if not code_executed and "```" not in response:
            return 0.2, "No code execution detected"

        # Check for expected outputs in response
        found = sum(1 for exp in expected_outputs if exp in response)
        score = found / len(expected_outputs) if expected_outputs else 0.5

        return score, f"Found {found}/{len(expected_outputs)} expected outputs"

    def supports_parallel_items(self) -> bool:
        return True

    def get_item_concurrency(self) -> int:
        return 5

    def get_item_timeout_seconds(self) -> int:
        return 120  # 2 minutes per item
```

### FR-5: Test Data Examples

```json
{
  "metadata": {
    "version": "1.0.0",
    "total_items": 80,
    "categories": {
      "function_calling": 25,
      "tool_selection": 20,
      "tool_chaining": 20,
      "code_execution": 15
    }
  },
  "items": [
    {
      "id": "func_001",
      "task_type": "function_calling",
      "description": "What's the weather like in San Francisco today?",
      "available_tools": [
        {
          "type": "function",
          "function": {
            "name": "get_weather",
            "description": "Get current weather for a city",
            "parameters": {
              "type": "object",
              "properties": {
                "city": {"type": "string"},
                "units": {"type": "string", "enum": ["metric", "imperial"], "default": "metric"}
              },
              "required": ["city"]
            }
          }
        }
      ],
      "expected_call": {
        "function": "get_weather",
        "arguments": {"city": "San Francisco"}
      }
    },
    {
      "id": "select_001",
      "task_type": "tool_selection",
      "description": "Find the latest news about AI regulation in Europe",
      "available_tools": [
        {"name": "calculator", "description": "Perform calculations"},
        {"name": "web_search", "description": "Search the internet"},
        {"name": "code_execute", "description": "Run code"},
        {"name": "image_generate", "description": "Generate images"}
      ],
      "expected_tools": ["web_search"]
    },
    {
      "id": "chain_001",
      "task_type": "tool_chaining",
      "description": "Search for the population of Tokyo, then calculate what percentage it is of Japan's total population",
      "available_tools": [
        {"name": "web_search", "description": "Search the internet"},
        {"name": "calculator", "description": "Perform calculations"}
      ],
      "expected_sequence": ["web_search", "calculator"]
    },
    {
      "id": "code_001",
      "task_type": "code_execution",
      "description": "Write Python code to generate the first 10 Fibonacci numbers and print them",
      "expected_output_contains": ["1", "1", "2", "3", "5", "8", "13", "21", "34", "55"]
    }
  ]
}
```

## Non-Functional Requirements

### NFR-1: Tool Availability

- Standard tools must be defined consistently
- Tool schemas follow OpenAI function calling format
- Implementations receive tool definitions in request

### NFR-2: Determinism

- Same item always has same expected output
- Tool simulation is deterministic
- Scoring is reproducible

### NFR-3: Security

- Code execution items are validated for safety
- Sandbox outputs are sanitized
- No arbitrary code execution in evaluation

## Acceptance Criteria

- [ ] 80 tool use items created and validated
- [ ] 4 task types with specified item counts
- [ ] Function call evaluation working
- [ ] Tool selection scoring working
- [ ] Tool chaining evaluation working
- [ ] Code execution detection working
- [ ] Integration with Janus category in UI
- [ ] All tests passing

## Open Questions / Risks

1. **Tool schema standardization**: Which tool schemas should be "standard" across all implementations?
2. **Multi-turn evaluation**: How do we evaluate multi-turn tool use conversations?
3. **Parallel tool calls**: How do we score parallel vs sequential tool execution?
4. **Sandbox integration**: How do we verify actual sandbox execution vs mock?

## Related Specs

- `specs/30_janus_benchmark_integration.md` - Overview
- `specs/competition/05_architecture_overview.md` - Platform services
- `specs/08_sandy_integration.md` - Sandbox integration

## Files to Create

```
chutes-bench-runner/backend/app/benchmarks/
├── adapters/
│   └── janus_tool_use.py          # Adapter implementation
└── data/
    └── janus/
        └── tool_use_items.json    # Test data (80 items)
```
