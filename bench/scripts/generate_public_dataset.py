from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_ROOT = ROOT / "datasets" / "public"

IMAGE_RED = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=="
)


CHAT_QA = [
    ("What is the capital of France?", ["Paris"]),
    ("What is the capital of Japan?", ["Tokyo"]),
    ("What is the largest planet in our solar system?", ["Jupiter"]),
    ("What is the chemical formula for water?", ["H2O"]),
    ("What is 15 + 27?", ["42"]),
    ("What is 9 * 8?", ["72"]),
    ("What is the square root of 81?", ["9"]),
    ("Who wrote the novel 1984?", ["George Orwell", "Orwell"]),
    ("What is the largest mammal?", ["blue whale", "whale"]),
    ("What is the fastest land animal?", ["cheetah"]),
    ("What language is primarily spoken in Brazil?", ["Portuguese"]),
    ("How many continents are there on Earth?", ["7", "seven"]),
    ("Which planet is known as the Red Planet?", ["Mars"]),
    ("What is the boiling point of water in Celsius?", ["100"]),
    ("What is the smallest prime number?", ["2"]),
    ("What is the first month of the year?", ["January"]),
    ("What currency is used in the United States?", ["dollar", "USD"]),
    ("What is the capital of Canada?", ["Ottawa"]),
    ("What is the capital of Australia?", ["Canberra"]),
    ("What is the largest ocean?", ["Pacific"]),
    ("Who is credited with inventing the telephone?", ["Alexander Graham Bell", "Bell"]),
    ("What is 5 to the power of 3?", ["125"]),
    ("What is the largest desert in the world?", ["Sahara"]),
    ("What is the chemical symbol for gold?", ["Au"]),
    ("What is the symbol for the joule?", ["J"]),
    ("What is 12 * 12?", ["144"]),
    ("What color do you get by mixing red and blue?", ["purple"]),
    ("How many days are in a leap year?", ["366"]),
    ("Who wrote Pride and Prejudice?", ["Jane Austen", "Austen"]),
    ("What is the largest continent?", ["Asia"]),
    ("What is the capital of Italy?", ["Rome"]),
    ("What is the capital of Spain?", ["Madrid"]),
    ("How many meters are in a kilometer?", ["1000"]),
    ("What gas do plants absorb from the air?", ["carbon dioxide", "CO2"]),
    ("Which organ pumps blood through the body?", ["heart"]),
    ("What is the freezing point of water in Celsius?", ["0"]),
    ("What is the largest bone in the human body?", ["femur"]),
    ("What is the binary representation of 5?", ["101"]),
    ("What is the opposite of north?", ["south"]),
]

RESEARCH_QA = [
    ("What year was Python first released?", ["1991"]),
    ("Who created the Linux kernel?", ["Linus Torvalds", "Torvalds"]),
    ("Who invented the World Wide Web?", ["Tim Berners-Lee", "Berners-Lee"]),
    ("What year was Git first released?", ["2005"]),
    ("In what year was Java first released?", ["1995"]),
    ("What year did Apollo 11 land on the Moon?", ["1969"]),
    ("In what year was NASA founded?", ["1958"]),
    ("What year was the Eiffel Tower completed?", ["1889"]),
    ("What year was Google founded?", ["1998"]),
    ("Who proposed the theory of relativity?", ["Albert Einstein", "Einstein"]),
    ("What year did the Berlin Wall fall?", ["1989"]),
    ("What year was the first iPhone released?", ["2007"]),
    ("Who wrote the paper that introduced the Transformer model?", ["Vaswani"]),
    ("What year was the PostgreSQL project started?", ["1996"]),
    ("Who developed the C programming language?", ["Dennis Ritchie", "Ritchie"]),
    ("What year was the United Nations founded?", ["1945"]),
    ("What year did the first Star Wars film release?", ["1977"]),
    ("Who is credited with inventing the light bulb?", ["Thomas Edison", "Edison"]),
    ("What year was the first email sent?", ["1971"]),
    ("What year was the first modern Olympic Games held?", ["1896"]),
    ("Who wrote The Origin of Species?", ["Charles Darwin", "Darwin"]),
    ("What year did the Human Genome Project complete?", ["2003"]),
    ("What year was the first PlayStation released?", ["1994"]),
    ("Who discovered penicillin?", ["Alexander Fleming", "Fleming"]),
    ("What year was the first web browser released?", ["1990"]),
    ("Who founded Microsoft?", ["Bill Gates", "Paul Allen"]),
    ("What year was the first version of Linux released?", ["1991"]),
    ("Who discovered gravity according to popular history?", ["Isaac Newton", "Newton"]),
    ("What year was the first DVD format released?", ["1995"]),
    ("Who proposed the three laws of motion?", ["Isaac Newton", "Newton"]),
    ("What year was the first GPS satellite launched?", ["1978"]),
    ("Who created the Python programming language?", ["Guido van Rossum", "van Rossum"]),
    ("What year was the first Macintosh computer released?", ["1984"]),
    ("Who authored The Pragmatic Programmer?", ["Andrew Hunt", "David Thomas"]),
    ("What year was the first Raspberry Pi released?", ["2012"]),
    ("Who wrote the Unix operating system with Ken Thompson?", ["Dennis Ritchie", "Ritchie"]),
    ("What year was the first Slack release?", ["2013"]),
    ("Who founded SpaceX?", ["Elon Musk", "Musk"]),
    ("What year was the first Kindle released?", ["2007"]),
]

CODE_TASKS = [
    {
        "function_name": "is_even",
        "prompt": "Write a Python function is_even(n) that returns True if n is even.",
        "test_cases": [
            {"input": [2], "output": True},
            {"input": [7], "output": False},
        ],
    },
    {
        "function_name": "is_odd",
        "prompt": "Write a Python function is_odd(n) that returns True if n is odd.",
        "test_cases": [
            {"input": [2], "output": False},
            {"input": [7], "output": True},
        ],
    },
    {
        "function_name": "square",
        "prompt": "Write a Python function square(n) that returns n squared.",
        "test_cases": [
            {"input": [3], "output": 9},
            {"input": [-4], "output": 16},
        ],
    },
    {
        "function_name": "cube",
        "prompt": "Write a Python function cube(n) that returns n cubed.",
        "test_cases": [
            {"input": [2], "output": 8},
            {"input": [-3], "output": -27},
        ],
    },
    {
        "function_name": "abs_diff",
        "prompt": "Write a Python function abs_diff(a, b) that returns the absolute difference.",
        "test_cases": [
            {"input": [10, 3], "output": 7},
            {"input": [3, 10], "output": 7},
        ],
    },
    {
        "function_name": "max_of_two",
        "prompt": "Write a Python function max_of_two(a, b) that returns the larger value.",
        "test_cases": [
            {"input": [5, 9], "output": 9},
            {"input": [4, -1], "output": 4},
        ],
    },
    {
        "function_name": "min_of_three",
        "prompt": "Write a Python function min_of_three(a, b, c) that returns the smallest value.",
        "test_cases": [
            {"input": [3, 7, 1], "output": 1},
            {"input": [5, 2, 8], "output": 2},
        ],
    },
    {
        "function_name": "sum_list",
        "prompt": "Write a Python function sum_list(values) that returns the sum of a list of numbers.",
        "test_cases": [
            {"input": [[1, 2, 3]], "output": 6},
            {"input": [[-1, 5]], "output": 4},
        ],
    },
    {
        "function_name": "product_list",
        "prompt": "Write a Python function product_list(values) that returns the product of a list of numbers.",
        "test_cases": [
            {"input": [[2, 3, 4]], "output": 24},
            {"input": [[5, 0, 2]], "output": 0},
        ],
    },
    {
        "function_name": "reverse_string",
        "prompt": "Write a Python function reverse_string(text) that returns the reversed string.",
        "test_cases": [
            {"input": ["hello"], "output": "olleh"},
            {"input": ["abc"], "output": "cba"},
        ],
    },
    {
        "function_name": "count_vowels",
        "prompt": "Write a Python function count_vowels(text) that counts vowels in a string.",
        "test_cases": [
            {"input": ["hello"], "output": 2},
            {"input": ["rhythm"], "output": 0},
        ],
    },
    {
        "function_name": "factorial",
        "prompt": "Write a Python function factorial(n) that returns n factorial.",
        "test_cases": [
            {"input": [5], "output": 120},
            {"input": [0], "output": 1},
        ],
    },
    {
        "function_name": "fibonacci",
        "prompt": "Write a Python function fibonacci(n) that returns the nth Fibonacci number (0-indexed).",
        "test_cases": [
            {"input": [0], "output": 0},
            {"input": [6], "output": 8},
        ],
    },
    {
        "function_name": "is_prime",
        "prompt": "Write a Python function is_prime(n) that returns True if n is prime.",
        "test_cases": [
            {"input": [2], "output": True},
            {"input": [4], "output": False},
        ],
    },
    {
        "function_name": "gcd",
        "prompt": "Write a Python function gcd(a, b) that returns the greatest common divisor.",
        "test_cases": [
            {"input": [12, 18], "output": 6},
            {"input": [7, 3], "output": 1},
        ],
    },
    {
        "function_name": "lcm",
        "prompt": "Write a Python function lcm(a, b) that returns the least common multiple.",
        "test_cases": [
            {"input": [4, 6], "output": 12},
            {"input": [5, 7], "output": 35},
        ],
    },
    {
        "function_name": "is_palindrome",
        "prompt": "Write a Python function is_palindrome(text) that returns True if the string is a palindrome.",
        "test_cases": [
            {"input": ["racecar"], "output": True},
            {"input": ["hello"], "output": False},
        ],
    },
    {
        "function_name": "clamp",
        "prompt": "Write a Python function clamp(value, min_value, max_value) that clamps a number to the range.",
        "test_cases": [
            {"input": [5, 1, 10], "output": 5},
            {"input": [-2, 0, 3], "output": 0},
        ],
    },
    {
        "function_name": "average_list",
        "prompt": "Write a Python function average_list(values) that returns the average of numbers.",
        "test_cases": [
            {"input": [[2, 4, 6]], "output": 4},
            {"input": [[1, 2, 3, 4]], "output": 2.5},
        ],
    },
    {
        "function_name": "count_occurrences",
        "prompt": "Write a Python function count_occurrences(values, target) that counts a target in a list.",
        "test_cases": [
            {"input": [[1, 2, 2, 3], 2], "output": 2},
            {"input": [["a", "b", "a"], "a"], "output": 2},
        ],
    },
    {
        "function_name": "unique_list",
        "prompt": "Write a Python function unique_list(values) that returns unique values preserving order.",
        "test_cases": [
            {"input": [[1, 1, 2, 3, 2]], "output": [1, 2, 3]},
            {"input": [["a", "b", "a"]], "output": ["a", "b"]},
        ],
    },
    {
        "function_name": "last_element",
        "prompt": "Write a Python function last_element(values) that returns the last element.",
        "test_cases": [
            {"input": [[1, 2, 3]], "output": 3},
            {"input": [["x", "y"]], "output": "y"},
        ],
    },
    {
        "function_name": "first_element",
        "prompt": "Write a Python function first_element(values) that returns the first element.",
        "test_cases": [
            {"input": [[1, 2, 3]], "output": 1},
            {"input": [["x", "y"]], "output": "x"},
        ],
    },
    {
        "function_name": "to_celsius",
        "prompt": "Write a Python function to_celsius(fahrenheit) that converts Fahrenheit to Celsius.",
        "test_cases": [
            {"input": [32], "output": 0},
            {"input": [212], "output": 100},
        ],
    },
    {
        "function_name": "to_fahrenheit",
        "prompt": "Write a Python function to_fahrenheit(celsius) that converts Celsius to Fahrenheit.",
        "test_cases": [
            {"input": [0], "output": 32},
            {"input": [100], "output": 212},
        ],
    },
    {
        "function_name": "area_circle",
        "prompt": "Write a Python function area_circle(radius) that returns area using pi=3.14159.",
        "test_cases": [
            {"input": [1], "output": 3.14159},
            {"input": [2], "output": 12.56636},
        ],
    },
    {
        "function_name": "is_leap_year",
        "prompt": "Write a Python function is_leap_year(year) that returns True for leap years.",
        "test_cases": [
            {"input": [2000], "output": True},
            {"input": [1900], "output": False},
        ],
    },
    {
        "function_name": "sort_numbers",
        "prompt": "Write a Python function sort_numbers(values) that returns a sorted list.",
        "test_cases": [
            {"input": [[3, 1, 2]], "output": [1, 2, 3]},
            {"input": [[5, -1, 4]], "output": [-1, 4, 5]},
        ],
    },
    {
        "function_name": "remove_duplicates",
        "prompt": "Write a Python function remove_duplicates(values) that removes duplicates preserving order.",
        "test_cases": [
            {"input": [[1, 2, 2, 3]], "output": [1, 2, 3]},
            {"input": [["a", "a", "b"]], "output": ["a", "b"]},
        ],
    },
    {
        "function_name": "sum_digits",
        "prompt": "Write a Python function sum_digits(n) that returns the sum of digits.",
        "test_cases": [
            {"input": [123], "output": 6},
            {"input": [9005], "output": 14},
        ],
    },
    {
        "function_name": "is_anagram",
        "prompt": "Write a Python function is_anagram(a, b) that returns True if the strings are anagrams.",
        "test_cases": [
            {"input": ["listen", "silent"], "output": True},
            {"input": ["hello", "world"], "output": False},
        ],
    },
    {
        "function_name": "capitalize_words",
        "prompt": "Write a Python function capitalize_words(text) that capitalizes each word.",
        "test_cases": [
            {"input": ["hello world"], "output": "Hello World"},
            {"input": ["janus bench"], "output": "Janus Bench"},
        ],
    },
    {
        "function_name": "flatten_list",
        "prompt": "Write a Python function flatten_list(values) that flattens one level of nested lists.",
        "test_cases": [
            {"input": [[[1, 2], [3, 4]]], "output": [1, 2, 3, 4]},
            {"input": [[["a"], ["b", "c"]]], "output": ["a", "b", "c"]},
        ],
    },
    {
        "function_name": "invert_dict",
        "prompt": "Write a Python function invert_dict(mapping) that swaps keys and values.",
        "test_cases": [
            {"input": [{"a": 1, "b": 2}], "output": {1: "a", 2: "b"}},
            {"input": [{"x": "y"}], "output": {"y": "x"}},
        ],
    },
    {
        "function_name": "count_words",
        "prompt": "Write a Python function count_words(text) that returns the number of words.",
        "test_cases": [
            {"input": ["one two three"], "output": 3},
            {"input": ["hello"], "output": 1},
        ],
    },
    {
        "function_name": "median_list",
        "prompt": "Write a Python function median_list(values) that returns the median of a list of numbers.",
        "test_cases": [
            {"input": [[1, 3, 2]], "output": 2},
            {"input": [[4, 1, 7, 2]], "output": 3.0},
        ],
    },
]

MULTIMODAL_PROMPTS = [
    "What color is the pixel in this image?",
    "Describe the primary color you see in the image.",
    "Identify the dominant color in this image.",
    "What color is shown in the image?",
    "What is the main color in this image?",
    "Name the color displayed in this image.",
    "Is the pixel shown red, green, or blue?",
    "What color does the image show?",
    "Describe the color of the pixel.",
    "State the color visible in the image.",
    "What hue does the image contain?",
    "Identify the color of the single pixel.",
    "What color is the square pixel?",
    "Which color is displayed?",
    "What color tone is present?",
    "What is the color of the image background?",
    "What color appears in the image?",
    "Identify the color in the image.",
    "What is the image showing in terms of color?",
    "What color is represented by the pixel?",
    "Which color is this pixel?",
    "What color do you see here?",
    "What is the visible color?",
    "Name the dominant hue in this image.",
    "What color should this pixel be described as?",
    "What primary color is visible?",
    "Which color fills the image?",
]

TOOL_DEFINITIONS = {
    "get_weather": {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather for a location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "City name"},
                    "units": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                    },
                },
                "required": ["location"],
            },
        },
    },
    "calculator": {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "Evaluate a math expression",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "Math expression"},
                },
                "required": ["expression"],
            },
        },
    },
    "get_exchange_rate": {
        "type": "function",
        "function": {
            "name": "get_exchange_rate",
            "description": "Get exchange rate between currencies",
            "parameters": {
                "type": "object",
                "properties": {
                    "base_currency": {"type": "string"},
                    "target_currency": {"type": "string"},
                },
                "required": ["base_currency", "target_currency"],
            },
        },
    },
    "get_time": {
        "type": "function",
        "function": {
            "name": "get_time",
            "description": "Get the current time for a timezone",
            "parameters": {
                "type": "object",
                "properties": {
                    "timezone": {"type": "string"},
                },
                "required": ["timezone"],
            },
        },
    },
    "search": {
        "type": "function",
        "function": {
            "name": "search",
            "description": "Search the web",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                },
                "required": ["query"],
            },
        },
    },
}

TOOL_TASKS = [
    {
        "prompt": "Get the current weather in Tokyo.",
        "tool": "get_weather",
        "arguments": {"location": "Tokyo"},
    },
    {
        "prompt": "Get the current weather in Berlin.",
        "tool": "get_weather",
        "arguments": {"location": "Berlin"},
    },
    {
        "prompt": "Get the current weather in Sydney.",
        "tool": "get_weather",
        "arguments": {"location": "Sydney"},
    },
    {
        "prompt": "Calculate 15 * 7.",
        "tool": "calculator",
        "arguments": {"expression": "15*7"},
    },
    {
        "prompt": "Calculate (120 / 5) + 3.",
        "tool": "calculator",
        "arguments": {"expression": "(120/5)+3"},
    },
    {
        "prompt": "Convert from USD to EUR using the exchange rate tool.",
        "tool": "get_exchange_rate",
        "arguments": {"base_currency": "USD", "target_currency": "EUR"},
    },
    {
        "prompt": "Convert from GBP to JPY using the exchange rate tool.",
        "tool": "get_exchange_rate",
        "arguments": {"base_currency": "GBP", "target_currency": "JPY"},
    },
    {
        "prompt": "What is the current time in UTC?",
        "tool": "get_time",
        "arguments": {"timezone": "UTC"},
    },
    {
        "prompt": "What is the current time in America/New_York?",
        "tool": "get_time",
        "arguments": {"timezone": "America/New_York"},
    },
    {
        "prompt": "Search the web for the population of Canada.",
        "tool": "search",
        "arguments": {"query": "population of Canada"},
    },
    {
        "prompt": "Search the web for the tallest mountain in Europe.",
        "tool": "search",
        "arguments": {"query": "tallest mountain in Europe"},
    },
    {
        "prompt": "Search the web for the date of the next leap year after 2024.",
        "tool": "search",
        "arguments": {"query": "next leap year after 2024"},
    },
    {
        "prompt": "Get the weather in Toronto in Fahrenheit.",
        "tool": "get_weather",
        "arguments": {"location": "Toronto", "units": "fahrenheit"},
    },
    {
        "prompt": "Calculate 144 divided by 12.",
        "tool": "calculator",
        "arguments": {"expression": "144/12"},
    },
    {
        "prompt": "What time is it in Europe/London?",
        "tool": "get_time",
        "arguments": {"timezone": "Europe/London"},
    },
    {
        "prompt": "Search for the release year of the first Android phone.",
        "tool": "search",
        "arguments": {"query": "first Android phone release year"},
    },
    {
        "prompt": "Convert from AUD to USD using the exchange rate tool.",
        "tool": "get_exchange_rate",
        "arguments": {"base_currency": "AUD", "target_currency": "USD"},
    },
    {
        "prompt": "Calculate 7 * 9 + 4.",
        "tool": "calculator",
        "arguments": {"expression": "7*9+4"},
    },
    {
        "prompt": "Search for the capital of New Zealand.",
        "tool": "search",
        "arguments": {"query": "capital of New Zealand"},
    },
    {
        "prompt": "Get the weather in Madrid.",
        "tool": "get_weather",
        "arguments": {"location": "Madrid"},
    },
    {
        "prompt": "Calculate 64 / 8.",
        "tool": "calculator",
        "arguments": {"expression": "64/8"},
    },
    {
        "prompt": "What is the time in Asia/Singapore?",
        "tool": "get_time",
        "arguments": {"timezone": "Asia/Singapore"},
    },
    {
        "prompt": "Search for the largest lake in Africa.",
        "tool": "search",
        "arguments": {"query": "largest lake in Africa"},
    },
    {
        "prompt": "Convert from CAD to USD using the exchange rate tool.",
        "tool": "get_exchange_rate",
        "arguments": {"base_currency": "CAD", "target_currency": "USD"},
    },
    {
        "prompt": "Calculate 225 - 47.",
        "tool": "calculator",
        "arguments": {"expression": "225-47"},
    },
    {
        "prompt": "Get the weather in Cape Town.",
        "tool": "get_weather",
        "arguments": {"location": "Cape Town"},
    },
    {
        "prompt": "Search for the year the C++ language was created.",
        "tool": "search",
        "arguments": {"query": "year C++ language created"},
    },
]

DEEP_RESEARCH_TOPICS = [
    {
        "prompt": "Write a comprehensive analysis of the pros and cons of Rust vs Go for backend development.",
        "must_cover": ["performance", "safety", "ecosystem", "learning curve"],
    },
    {
        "prompt": "Provide a detailed comparison of SQL and NoSQL databases for analytics workloads.",
        "must_cover": ["scalability", "consistency", "querying", "use cases"],
    },
    {
        "prompt": "Analyze the trade-offs between monoliths and microservices for small teams.",
        "must_cover": ["deployment", "complexity", "scaling", "team size"],
    },
    {
        "prompt": "Write an in-depth overview of edge computing benefits and challenges.",
        "must_cover": ["latency", "privacy", "infrastructure", "cost"],
    },
    {
        "prompt": "Assess the impacts of AI automation on software testing practices.",
        "must_cover": ["coverage", "maintenance", "cost", "limitations"],
    },
    {
        "prompt": "Compare serverless functions with container-based deployments for APIs.",
        "must_cover": ["scaling", "cold starts", "cost", "operations"],
    },
    {
        "prompt": "Discuss data governance challenges in multi-tenant SaaS platforms.",
        "must_cover": ["privacy", "compliance", "access control", "auditing"],
    },
    {
        "prompt": "Evaluate the pros and cons of managed vs self-hosted Kubernetes.",
        "must_cover": ["operations", "cost", "control", "security"],
    },
    {
        "prompt": "Analyze the role of retrieval-augmented generation in enterprise search.",
        "must_cover": ["accuracy", "latency", "indexing", "grounding"],
    },
    {
        "prompt": "Provide a detailed overview of SOC 2 compliance for software teams.",
        "must_cover": ["security", "availability", "process", "audit"],
    },
    {
        "prompt": "Discuss the strengths and weaknesses of REST vs GraphQL for public APIs.",
        "must_cover": ["flexibility", "performance", "tooling", "complexity"],
    },
    {
        "prompt": "Write a deep dive on caching strategies for high-traffic web services.",
        "must_cover": ["cache invalidation", "ttl", "layers", "consistency"],
    },
    {
        "prompt": "Analyze the challenges of multi-region deployments for stateful systems.",
        "must_cover": ["latency", "replication", "failover", "consistency"],
    },
    {
        "prompt": "Provide an overview of privacy-preserving analytics techniques.",
        "must_cover": ["differential privacy", "aggregation", "anonymization", "trade-offs"],
    },
    {
        "prompt": "Compare event-driven architectures with batch processing for data pipelines.",
        "must_cover": ["latency", "complexity", "cost", "reliability"],
    },
    {
        "prompt": "Discuss best practices for incident response in SaaS operations.",
        "must_cover": ["detection", "communication", "mitigation", "postmortem"],
    },
    {
        "prompt": "Assess the impact of container security scanning in CI/CD.",
        "must_cover": ["vulnerabilities", "automation", "policy", "coverage"],
    },
    {
        "prompt": "Provide a long-form comparison of PostgreSQL and MySQL for OLTP workloads.",
        "must_cover": ["features", "performance", "replication", "ecosystem"],
    },
]


def write_jsonl(path: Path, items: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        for item in items:
            handle.write(json.dumps(item, ensure_ascii=True))
            handle.write("\n")


def build_chat_items(suite: str, pairs: list[tuple[str, list[str]]]) -> list[dict]:
    items = []
    for idx, (prompt, keywords) in enumerate(pairs, start=1):
        items.append(
            {
                "id": f"chat_{suite}_{idx:03d}",
                "category": "chat",
                "input": {"messages": [{"role": "user", "content": prompt}]},
                "expected": {
                    "type": "text",
                    "contains": keywords,
                    "max_latency_ms": 2000,
                },
            }
        )
    return items


def build_research_items(suite: str, pairs: list[tuple[str, list[str]]]) -> list[dict]:
    items = []
    for idx, (prompt, keywords) in enumerate(pairs, start=1):
        items.append(
            {
                "id": f"research_{suite}_{idx:03d}",
                "category": "research",
                "input": {"messages": [{"role": "user", "content": f"{prompt} Provide citations."}]},
                "expected": {
                    "type": "text",
                    "contains": keywords,
                    "requires_citations": True,
                    "min_sources": 2,
                },
            }
        )
    return items


def build_code_items(suite: str, specs: list[dict]) -> list[dict]:
    items = []
    for idx, spec in enumerate(specs, start=1):
        items.append(
            {
                "id": f"code_{suite}_{idx:03d}",
                "category": "code",
                "input": {"messages": [{"role": "user", "content": spec["prompt"]}]},
                "expected": {
                    "type": "code",
                    "language": "python",
                    "function_name": spec["function_name"],
                    "test_cases": spec["test_cases"],
                    "must_execute": True,
                },
            }
        )
    return items


def build_multimodal_items(suite: str, prompts: list[str]) -> list[dict]:
    items = []
    for idx, prompt in enumerate(prompts, start=1):
        items.append(
            {
                "id": f"multimodal_{suite}_{idx:03d}",
                "category": "multimodal",
                "input": {
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {"type": "image_url", "image_url": {"url": IMAGE_RED}},
                            ],
                        }
                    ]
                },
                "expected": {
                    "type": "text",
                    "contains": ["red"],
                },
            }
        )
    return items


def build_tool_items(suite: str, specs: list[dict]) -> list[dict]:
    items = []
    for idx, spec in enumerate(specs, start=1):
        tool_name = spec["tool"]
        items.append(
            {
                "id": f"agentic_{suite}_{idx:03d}",
                "category": "agentic",
                "input": {"messages": [{"role": "user", "content": spec["prompt"]}]},
                "available_tools": [
                    TOOL_DEFINITIONS[tool_name],
                    TOOL_DEFINITIONS["search"],
                ],
                "tool_use_task_type": "function_calling",
                "expected_call": {
                    "function": tool_name,
                    "arguments": spec["arguments"],
                },
                "expected": {
                    "type": "text",
                    "requires_tool_use": True,
                    "tools_expected": [tool_name],
                    "min_length": 40,
                },
            }
        )
    return items


def build_deep_research_items(suite: str, topics: list[dict], min_length: int) -> list[dict]:
    items = []
    for idx, spec in enumerate(topics, start=1):
        items.append(
            {
                "id": f"deep_research_{suite}_{idx:03d}",
                "category": "deep_research",
                "input": {"messages": [{"role": "user", "content": spec["prompt"]}]},
                "expected": {
                    "type": "text",
                    "must_cover": spec["must_cover"],
                    "min_length": min_length,
                },
            }
        )
    return items


def main() -> None:
    train_counts = {
        "chat": 24,
        "research": 24,
        "code": 24,
        "multimodal": 18,
        "agentic": 18,
        "deep_research": 12,
    }
    dev_counts = {
        "chat": 12,
        "research": 12,
        "code": 12,
        "multimodal": 9,
        "agentic": 9,
        "deep_research": 6,
    }

    assert len(CHAT_QA) >= train_counts["chat"] + dev_counts["chat"]
    assert len(RESEARCH_QA) >= train_counts["research"] + dev_counts["research"]
    assert len(CODE_TASKS) >= train_counts["code"] + dev_counts["code"]
    assert len(MULTIMODAL_PROMPTS) >= train_counts["multimodal"] + dev_counts["multimodal"]
    assert len(TOOL_TASKS) >= train_counts["agentic"] + dev_counts["agentic"]
    assert len(DEEP_RESEARCH_TOPICS) >= train_counts["deep_research"] + dev_counts["deep_research"]

    train_root = PUBLIC_ROOT / "train"
    dev_root = PUBLIC_ROOT / "dev"

    chat_train = build_chat_items("train", CHAT_QA[: train_counts["chat"]])
    chat_dev = build_chat_items(
        "dev",
        CHAT_QA[train_counts["chat"] : train_counts["chat"] + dev_counts["chat"]],
    )

    research_train = build_research_items(
        "train",
        RESEARCH_QA[: train_counts["research"]],
    )
    research_dev = build_research_items(
        "dev",
        RESEARCH_QA[
            train_counts["research"] : train_counts["research"] + dev_counts["research"]
        ],
    )

    code_train = build_code_items("train", CODE_TASKS[: train_counts["code"]])
    code_dev = build_code_items(
        "dev",
        CODE_TASKS[train_counts["code"] : train_counts["code"] + dev_counts["code"]],
    )

    multimodal_train = build_multimodal_items(
        "train",
        MULTIMODAL_PROMPTS[: train_counts["multimodal"]],
    )
    multimodal_dev = build_multimodal_items(
        "dev",
        MULTIMODAL_PROMPTS[
            train_counts["multimodal"] : train_counts["multimodal"]
            + dev_counts["multimodal"]
        ],
    )

    tool_train = build_tool_items("train", TOOL_TASKS[: train_counts["agentic"]])
    tool_dev = build_tool_items(
        "dev",
        TOOL_TASKS[train_counts["agentic"] : train_counts["agentic"] + dev_counts["agentic"]],
    )

    deep_train = build_deep_research_items(
        "train",
        DEEP_RESEARCH_TOPICS[: train_counts["deep_research"]],
        min_length=800,
    )
    deep_dev = build_deep_research_items(
        "dev",
        DEEP_RESEARCH_TOPICS[
            train_counts["deep_research"] : train_counts["deep_research"]
            + dev_counts["deep_research"]
        ],
        min_length=600,
    )

    write_jsonl(train_root / "chat.jsonl", chat_train)
    write_jsonl(dev_root / "chat.jsonl", chat_dev)

    write_jsonl(train_root / "research.jsonl", research_train)
    write_jsonl(dev_root / "research.jsonl", research_dev)

    write_jsonl(train_root / "code.jsonl", code_train)
    write_jsonl(dev_root / "code.jsonl", code_dev)

    write_jsonl(train_root / "multimodal.jsonl", multimodal_train)
    write_jsonl(dev_root / "multimodal.jsonl", multimodal_dev)

    write_jsonl(train_root / "agentic.jsonl", tool_train)
    write_jsonl(dev_root / "agentic.jsonl", tool_dev)

    write_jsonl(train_root / "deep_research.jsonl", deep_train)
    write_jsonl(dev_root / "deep_research.jsonl", deep_dev)


if __name__ == "__main__":
    main()
