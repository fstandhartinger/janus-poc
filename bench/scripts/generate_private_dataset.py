from __future__ import annotations

from pathlib import Path

from generate_public_dataset import (
    build_chat_items,
    build_code_items,
    build_deep_research_items,
    build_multimodal_items,
    build_research_items,
    build_tool_items,
    write_jsonl,
)


ROOT = Path(__file__).resolve().parents[1]
PRIVATE_ROOT = ROOT / "datasets" / "private" / "test"

PRIVATE_CHAT_QA = [
    ("What is the capital of Sweden?", ["Stockholm"]),
    ("What is 8 * 7?", ["56"]),
    ("What is the chemical symbol for oxygen?", ["O"]),
    ("What planet is known for its rings?", ["Saturn"]),
    ("How many hours are in a day?", ["24"]),
    ("What is the largest bird?", ["ostrich"]),
]

PRIVATE_RESEARCH_QA = [
    ("What year was the first version of Kubernetes released?", ["2014"]),
    ("Who created the Go programming language?", ["Robert Griesemer", "Rob Pike", "Ken Thompson"]),
    ("What year was Docker first released?", ["2013"]),
    ("Who invented the Python programming language?", ["Guido van Rossum", "van Rossum"]),
    ("What year did the first Raspberry Pi ship?", ["2012"]),
    ("Who founded the Apache Software Foundation?", ["Brian Behlendorf"]),
]

PRIVATE_CODE_TASKS = [
    {
        "function_name": "is_positive",
        "prompt": "Write a Python function is_positive(n) that returns True if n is greater than zero.",
        "test_cases": [
            {"input": [3], "output": True},
            {"input": [-1], "output": False},
        ],
    },
    {
        "function_name": "double",
        "prompt": "Write a Python function double(n) that returns n * 2.",
        "test_cases": [
            {"input": [4], "output": 8},
            {"input": [-2], "output": -4},
        ],
    },
    {
        "function_name": "string_length",
        "prompt": "Write a Python function string_length(text) that returns the length of a string.",
        "test_cases": [
            {"input": ["hello"], "output": 5},
            {"input": [""], "output": 0},
        ],
    },
    {
        "function_name": "sum_range",
        "prompt": "Write a Python function sum_range(n) that sums numbers from 1 to n inclusive.",
        "test_cases": [
            {"input": [3], "output": 6},
            {"input": [5], "output": 15},
        ],
    },
    {
        "function_name": "reverse_list",
        "prompt": "Write a Python function reverse_list(values) that returns the list reversed.",
        "test_cases": [
            {"input": [[1, 2, 3]], "output": [3, 2, 1]},
            {"input": [["a", "b"]], "output": ["b", "a"]},
        ],
    },
    {
        "function_name": "starts_with",
        "prompt": "Write a Python function starts_with(text, prefix) that returns True if text starts with prefix.",
        "test_cases": [
            {"input": ["janus", "ja"], "output": True},
            {"input": ["janus", "no"], "output": False},
        ],
    },
]

PRIVATE_MULTIMODAL_PROMPTS = [
    "What color is the pixel in this image?",
    "Describe the dominant color in this image.",
    "Identify the color shown in the image.",
    "What color is visible here?",
]

PRIVATE_TOOL_TASKS = [
    {
        "prompt": "Get the current weather in Oslo.",
        "tool": "get_weather",
        "arguments": {"location": "Oslo"},
    },
    {
        "prompt": "Calculate 42 + 58.",
        "tool": "calculator",
        "arguments": {"expression": "42+58"},
    },
    {
        "prompt": "Convert from EUR to USD using the exchange rate tool.",
        "tool": "get_exchange_rate",
        "arguments": {"base_currency": "EUR", "target_currency": "USD"},
    },
    {
        "prompt": "What time is it in Asia/Tokyo?",
        "tool": "get_time",
        "arguments": {"timezone": "Asia/Tokyo"},
    },
]

PRIVATE_DEEP_RESEARCH_TOPICS = [
    {
        "prompt": "Write a detailed analysis of the trade-offs between SQLite and PostgreSQL.",
        "must_cover": ["features", "performance", "deployment", "use cases"],
    },
    {
        "prompt": "Provide an in-depth discussion of zero-trust security models.",
        "must_cover": ["identity", "network", "policy", "monitoring"],
    },
    {
        "prompt": "Analyze the benefits and drawbacks of event sourcing in SaaS systems.",
        "must_cover": ["auditability", "complexity", "storage", "debugging"],
    },
    {
        "prompt": "Compare Kafka and RabbitMQ for real-time messaging workloads.",
        "must_cover": ["throughput", "ordering", "scaling", "operations"],
    },
]


def main() -> None:
    PRIVATE_ROOT.mkdir(parents=True, exist_ok=True)

    write_jsonl(PRIVATE_ROOT / "chat.jsonl", build_chat_items("test", PRIVATE_CHAT_QA))
    write_jsonl(
        PRIVATE_ROOT / "research.jsonl",
        build_research_items("test", PRIVATE_RESEARCH_QA),
    )
    write_jsonl(PRIVATE_ROOT / "code.jsonl", build_code_items("test", PRIVATE_CODE_TASKS))
    write_jsonl(
        PRIVATE_ROOT / "multimodal.jsonl",
        build_multimodal_items("test", PRIVATE_MULTIMODAL_PROMPTS),
    )
    write_jsonl(PRIVATE_ROOT / "agentic.jsonl", build_tool_items("test", PRIVATE_TOOL_TASKS))
    write_jsonl(
        PRIVATE_ROOT / "deep_research.jsonl",
        build_deep_research_items("test", PRIVATE_DEEP_RESEARCH_TOPICS, min_length=900),
    )


if __name__ == "__main__":
    main()
