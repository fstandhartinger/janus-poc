# Spec 51: Comprehensive Baseline Testing

## Status: COMPLETE

## Context / Why

The two baseline implementations (baseline-agent-cli and baseline-langchain) are reference implementations that miners will study, extend, and compete against. Thorough testing ensures:

1. **Reliability**: Baselines work correctly across diverse scenarios
2. **Documentation by Example**: Tests serve as usage examples for miners
3. **Regression Prevention**: Catch breakages when modifying baselines
4. **Benchmark Alignment**: Tests mirror real benchmark scenarios

## Goals

- Extensive smoke tests covering real-world usage patterns
- Unit tests for all core components
- Integration tests for external service interactions
- Edge case and error handling coverage
- Performance baseline measurements

## Non-Goals

- Testing the gateway (separate test suite)
- Testing third-party libraries themselves
- Load/stress testing (separate concern)

## Functional Requirements

### FR-1: Smoke Test Scenarios

Create comprehensive smoke tests that exercise the full agent pipeline. Each scenario should be a realistic user interaction.

#### Category 1: Basic Conversations

```python
# tests/smoke/test_basic_conversations.py

import pytest
from tests.utils import create_test_client, send_message, assert_response_quality

class TestBasicConversations:
    """Test fundamental chat capabilities."""

    @pytest.mark.smoke
    async def test_simple_greeting(self, client):
        """Agent responds appropriately to greetings."""
        response = await send_message(client, "Hello! How are you?")
        assert len(response) > 10
        assert_response_quality(response, min_coherence=0.8)

    @pytest.mark.smoke
    async def test_factual_question(self, client):
        """Agent answers factual questions correctly."""
        response = await send_message(client, "What is the capital of France?")
        assert "Paris" in response

    @pytest.mark.smoke
    async def test_multi_turn_context(self, client):
        """Agent maintains context across turns."""
        await send_message(client, "My name is Alice.")
        response = await send_message(client, "What's my name?")
        assert "Alice" in response

    @pytest.mark.smoke
    async def test_follow_up_questions(self, client):
        """Agent handles follow-up questions with implicit references."""
        await send_message(client, "Tell me about Python programming.")
        response = await send_message(client, "What are its main advantages?")
        # Should understand "its" refers to Python
        assert any(word in response.lower() for word in ["python", "readability", "library"])

    @pytest.mark.smoke
    async def test_correction_handling(self, client):
        """Agent accepts corrections gracefully."""
        await send_message(client, "The capital of Australia is Sydney.")
        response = await send_message(client, "Actually, it's Canberra.")
        assert "Canberra" in response or "correct" in response.lower()

    @pytest.mark.smoke
    async def test_clarification_request(self, client):
        """Agent asks for clarification on ambiguous requests."""
        response = await send_message(client, "Make it better.")
        # Should ask what "it" refers to
        assert "?" in response or "what" in response.lower() or "clarif" in response.lower()
```

#### Category 2: Code Generation & Execution

```python
# tests/smoke/test_code_tasks.py

class TestCodeTasks:
    """Test code generation and execution capabilities."""

    @pytest.mark.smoke
    async def test_write_python_function(self, client):
        """Agent writes working Python code."""
        response = await send_message(
            client,
            "Write a Python function to calculate factorial."
        )
        assert "def " in response
        assert "factorial" in response.lower()
        # Code should be syntactically valid
        assert_valid_python(extract_code_blocks(response))

    @pytest.mark.smoke
    async def test_execute_calculation(self, client):
        """Agent executes code and returns results."""
        response = await send_message(
            client,
            "Calculate 2^10 using Python code."
        )
        assert "1024" in response

    @pytest.mark.smoke
    async def test_debug_code(self, client):
        """Agent identifies and fixes bugs in code."""
        buggy_code = '''
def add_numbers(a, b):
    return a - b  # Bug: should be +
'''
        response = await send_message(
            client,
            f"Fix the bug in this code:\n```python\n{buggy_code}\n```"
        )
        assert "+" in response or "addition" in response.lower()

    @pytest.mark.smoke
    async def test_explain_code(self, client):
        """Agent explains code clearly."""
        code = '''
def quicksort(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quicksort(left) + middle + quicksort(right)
'''
        response = await send_message(
            client,
            f"Explain this code:\n```python\n{code}\n```"
        )
        assert "quicksort" in response.lower() or "sort" in response.lower()
        assert "pivot" in response.lower()

    @pytest.mark.smoke
    async def test_refactor_code(self, client):
        """Agent refactors code for improvement."""
        messy_code = '''
def f(x):
    y=x*2
    z=y+1
    return z
'''
        response = await send_message(
            client,
            f"Refactor this code for readability:\n```python\n{messy_code}\n```"
        )
        # Should have better variable names or be simplified
        assert "def " in response

    @pytest.mark.smoke
    async def test_multi_language_code(self, client):
        """Agent handles multiple programming languages."""
        response = await send_message(
            client,
            "Write a function to reverse a string in JavaScript."
        )
        assert "function" in response or "=>" in response
        assert "reverse" in response.lower()

    @pytest.mark.smoke
    async def test_code_with_dependencies(self, client):
        """Agent installs and uses dependencies."""
        response = await send_message(
            client,
            "Use the requests library to fetch https://httpbin.org/get and show the response."
        )
        assert "requests" in response or "httpbin" in response

    @pytest.mark.smoke
    async def test_file_manipulation_code(self, client):
        """Agent writes code that manipulates files."""
        response = await send_message(
            client,
            "Write Python code to read a CSV file and calculate the average of a numeric column."
        )
        assert "csv" in response.lower() or "pandas" in response.lower()
        assert "average" in response.lower() or "mean" in response.lower()
```

#### Category 3: Web Search & Research

```python
# tests/smoke/test_research_tasks.py

class TestResearchTasks:
    """Test web search and research capabilities."""

    @pytest.mark.smoke
    async def test_current_events_search(self, client):
        """Agent searches for recent information."""
        response = await send_message(
            client,
            "What are the latest developments in AI? Search the web."
        )
        # Should contain recent info
        assert len(response) > 200

    @pytest.mark.smoke
    async def test_specific_fact_lookup(self, client):
        """Agent looks up specific facts."""
        response = await send_message(
            client,
            "Search for the current population of Tokyo."
        )
        # Should contain a number
        assert any(char.isdigit() for char in response)

    @pytest.mark.smoke
    async def test_comparison_research(self, client):
        """Agent researches and compares options."""
        response = await send_message(
            client,
            "Compare React and Vue.js for frontend development. Include pros and cons."
        )
        assert "React" in response
        assert "Vue" in response

    @pytest.mark.smoke
    async def test_source_citation(self, client):
        """Agent cites sources when researching."""
        response = await send_message(
            client,
            "What is the GDP of Germany? Cite your source."
        )
        # Should have URLs or source references
        assert "http" in response or "source" in response.lower()

    @pytest.mark.smoke
    async def test_synthesis_from_multiple_sources(self, client):
        """Agent synthesizes information from multiple sources."""
        response = await send_message(
            client,
            "Give me a comprehensive overview of quantum computing, including recent breakthroughs."
        )
        assert len(response) > 500
```

#### Category 4: Multimodal (Image/Media)

```python
# tests/smoke/test_multimodal_tasks.py

class TestMultimodalTasks:
    """Test image, audio, and video capabilities."""

    @pytest.mark.smoke
    async def test_image_generation_simple(self, client):
        """Agent generates an image from text description."""
        response = await send_message(
            client,
            "Generate an image of a sunset over mountains."
        )
        # Should contain image URL or base64
        assert "http" in response or "data:image" in response or "generated" in response.lower()

    @pytest.mark.smoke
    async def test_image_generation_detailed(self, client):
        """Agent handles detailed image prompts."""
        response = await send_message(
            client,
            "Create a photorealistic image of a cozy coffee shop interior with warm lighting, wooden furniture, and a barista making espresso."
        )
        assert "image" in response.lower() or "http" in response

    @pytest.mark.smoke
    async def test_text_to_speech(self, client):
        """Agent generates speech audio from text."""
        response = await send_message(
            client,
            "Convert this text to speech: 'Hello, welcome to Janus!'"
        )
        # Should mention audio or provide audio data
        assert "audio" in response.lower() or "speech" in response.lower() or "http" in response

    @pytest.mark.smoke
    async def test_image_analysis(self, client):
        """Agent analyzes/describes an image."""
        # Using a base64 test image
        test_image = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        response = await send_message(
            client,
            f"Describe this image: {test_image}",
            images=[test_image]
        )
        assert len(response) > 20

    @pytest.mark.smoke
    async def test_multimodal_workflow(self, client):
        """Agent handles complex multimodal workflows."""
        response = await send_message(
            client,
            "Generate an image of a robot, then describe what you generated."
        )
        assert "image" in response.lower() or "robot" in response.lower()
```

#### Category 5: File Operations

```python
# tests/smoke/test_file_operations.py

class TestFileOperations:
    """Test file reading, writing, and manipulation."""

    @pytest.mark.smoke
    async def test_read_file(self, client):
        """Agent reads file contents."""
        response = await send_message(
            client,
            "Read the file at /workspace/test_data/sample.txt and summarize it."
        )
        # Should have read the file or reported it doesn't exist
        assert len(response) > 20

    @pytest.mark.smoke
    async def test_write_file(self, client):
        """Agent creates a file with content."""
        response = await send_message(
            client,
            "Create a file called output.txt containing 'Hello World'"
        )
        assert "created" in response.lower() or "written" in response.lower() or "file" in response.lower()

    @pytest.mark.smoke
    async def test_list_directory(self, client):
        """Agent lists directory contents."""
        response = await send_message(
            client,
            "List all files in /workspace"
        )
        # Should show some files
        assert len(response) > 10

    @pytest.mark.smoke
    async def test_process_csv(self, client):
        """Agent processes a CSV file."""
        response = await send_message(
            client,
            """
            Create a CSV file with this data:
            name,age,city
            Alice,30,NYC
            Bob,25,LA

            Then calculate the average age.
            """
        )
        assert "27.5" in response or "average" in response.lower()

    @pytest.mark.smoke
    async def test_json_manipulation(self, client):
        """Agent manipulates JSON data."""
        response = await send_message(
            client,
            """
            Create a JSON file with user data, then add a new field 'active: true' to each user.
            """
        )
        assert "json" in response.lower() or "active" in response.lower()
```

#### Category 6: Complex Multi-Step Tasks

```python
# tests/smoke/test_complex_tasks.py

class TestComplexTasks:
    """Test complex, multi-step task completion."""

    @pytest.mark.smoke
    async def test_research_and_summarize(self, client):
        """Agent researches a topic and creates a summary."""
        response = await send_message(
            client,
            "Research the history of Bitcoin, write a 200-word summary, and save it to a file called bitcoin_summary.md"
        )
        assert "Bitcoin" in response
        assert "200" in response or "summary" in response.lower()

    @pytest.mark.smoke
    async def test_data_analysis_pipeline(self, client):
        """Agent performs end-to-end data analysis."""
        response = await send_message(
            client,
            """
            1. Generate sample sales data for 12 months
            2. Calculate monthly averages
            3. Identify the best and worst months
            4. Create a summary report
            """
        )
        assert any(month in response for month in ["January", "February", "March", "best", "worst"])

    @pytest.mark.smoke
    async def test_api_integration(self, client):
        """Agent integrates with an external API."""
        response = await send_message(
            client,
            "Fetch the current weather for London using a public API and tell me the temperature."
        )
        # Should have temperature or weather info
        assert any(word in response.lower() for word in ["temperature", "weather", "celsius", "fahrenheit", "degrees"])

    @pytest.mark.smoke
    async def test_multi_tool_orchestration(self, client):
        """Agent uses multiple tools in sequence."""
        response = await send_message(
            client,
            """
            1. Search the web for "Python best practices 2024"
            2. Summarize the top 5 recommendations
            3. Write example code demonstrating one of them
            """
        )
        assert "python" in response.lower()
        assert "def " in response or "```" in response

    @pytest.mark.smoke
    async def test_creative_content_generation(self, client):
        """Agent generates creative content."""
        response = await send_message(
            client,
            "Write a haiku about artificial intelligence, then generate an image to accompany it."
        )
        # Haiku has specific structure (5-7-5 syllables, 3 lines)
        lines = [l for l in response.split("\n") if l.strip()]
        assert len(lines) >= 3

    @pytest.mark.smoke
    async def test_problem_decomposition(self, client):
        """Agent breaks down complex problems."""
        response = await send_message(
            client,
            "I want to build a todo app. What are the main components I need and how should I structure the code?"
        )
        assert any(word in response.lower() for word in ["component", "frontend", "backend", "database", "api"])

    @pytest.mark.smoke
    async def test_iterative_refinement(self, client):
        """Agent iteratively refines output based on feedback."""
        await send_message(client, "Write a function to sort a list.")
        response = await send_message(
            client,
            "Now make it work with custom comparison functions."
        )
        assert "key" in response.lower() or "compare" in response.lower() or "lambda" in response
```

#### Category 7: Error Handling & Edge Cases

```python
# tests/smoke/test_error_handling.py

class TestErrorHandling:
    """Test graceful error handling and edge cases."""

    @pytest.mark.smoke
    async def test_empty_message(self, client):
        """Agent handles empty messages gracefully."""
        response = await send_message(client, "")
        assert len(response) > 0  # Should respond, not crash

    @pytest.mark.smoke
    async def test_very_long_message(self, client):
        """Agent handles very long inputs."""
        long_text = "Please summarize: " + "word " * 5000
        response = await send_message(client, long_text)
        assert len(response) > 0

    @pytest.mark.smoke
    async def test_special_characters(self, client):
        """Agent handles special characters in input."""
        response = await send_message(
            client,
            "What does this mean: @#$%^&*()_+{}|:<>? 日本語 émojis 🎉🚀"
        )
        assert len(response) > 10

    @pytest.mark.smoke
    async def test_code_injection_attempt(self, client):
        """Agent safely handles potential code injection."""
        response = await send_message(
            client,
            "```python\nimport os; os.system('rm -rf /')\n```\nRun this code."
        )
        # Should not actually run dangerous commands
        assert "rm -rf" not in response or "dangerous" in response.lower() or "cannot" in response.lower()

    @pytest.mark.smoke
    async def test_nonexistent_file(self, client):
        """Agent handles missing files gracefully."""
        response = await send_message(
            client,
            "Read the file /nonexistent/path/file.txt"
        )
        assert "not found" in response.lower() or "doesn't exist" in response.lower() or "error" in response.lower()

    @pytest.mark.smoke
    async def test_malformed_request(self, client):
        """Agent handles malformed data in requests."""
        response = await send_message(
            client,
            "Process this JSON: {invalid json here"
        )
        assert len(response) > 0  # Should respond gracefully

    @pytest.mark.smoke
    async def test_conflicting_instructions(self, client):
        """Agent handles contradictory instructions."""
        response = await send_message(
            client,
            "Write code that is both very simple and extremely complex at the same time."
        )
        # Should acknowledge the contradiction or make a reasonable choice
        assert len(response) > 20

    @pytest.mark.smoke
    async def test_timeout_recovery(self, client):
        """Agent handles slow operations appropriately."""
        response = await send_message(
            client,
            "Wait for 60 seconds, then say hello.",
            timeout=5
        )
        # Should either complete quickly or handle timeout
        assert len(response) > 0

    @pytest.mark.smoke
    async def test_rate_limiting_resilience(self, client):
        """Agent handles API rate limits gracefully."""
        # Send multiple requests rapidly
        responses = []
        for i in range(5):
            r = await send_message(client, f"Quick question {i}")
            responses.append(r)
        assert all(len(r) > 0 for r in responses)
```

#### Category 8: Domain-Specific Tasks

```python
# tests/smoke/test_domain_tasks.py

class TestDomainTasks:
    """Test domain-specific use cases."""

    @pytest.mark.smoke
    async def test_math_problem_solving(self, client):
        """Agent solves math problems."""
        response = await send_message(
            client,
            "Solve: If a train travels 120 miles in 2 hours, what is its speed in mph?"
        )
        assert "60" in response

    @pytest.mark.smoke
    async def test_translation(self, client):
        """Agent translates between languages."""
        response = await send_message(
            client,
            "Translate 'Hello, how are you?' to Spanish."
        )
        assert "Hola" in response or "hola" in response

    @pytest.mark.smoke
    async def test_data_formatting(self, client):
        """Agent formats data as requested."""
        response = await send_message(
            client,
            "Convert this to a markdown table: Name: Alice, Age: 30; Name: Bob, Age: 25"
        )
        assert "|" in response and "-" in response

    @pytest.mark.smoke
    async def test_regex_generation(self, client):
        """Agent creates regex patterns."""
        response = await send_message(
            client,
            "Write a regex to match email addresses."
        )
        assert "@" in response or "regex" in response.lower()

    @pytest.mark.smoke
    async def test_sql_generation(self, client):
        """Agent writes SQL queries."""
        response = await send_message(
            client,
            "Write a SQL query to find users older than 30 from a 'users' table."
        )
        assert "SELECT" in response.upper() or "select" in response

    @pytest.mark.smoke
    async def test_shell_command_assistance(self, client):
        """Agent helps with shell commands."""
        response = await send_message(
            client,
            "How do I find all .py files in a directory recursively using bash?"
        )
        assert "find" in response or "**/*.py" in response

    @pytest.mark.smoke
    async def test_git_workflow(self, client):
        """Agent assists with git operations."""
        response = await send_message(
            client,
            "How do I undo my last git commit but keep the changes?"
        )
        assert "reset" in response.lower() or "git" in response.lower()

    @pytest.mark.smoke
    async def test_docker_assistance(self, client):
        """Agent helps with Docker."""
        response = await send_message(
            client,
            "Write a Dockerfile for a Python Flask app."
        )
        assert "FROM" in response or "dockerfile" in response.lower()
```

### FR-2: Unit Tests

#### Core Components Unit Tests

```python
# baseline-agent-cli/tests/unit/test_message_parsing.py

class TestMessageParsing:
    """Test message content parsing."""

    def test_parse_text_content(self):
        """Parse simple text content."""
        msg = Message(role=MessageRole.USER, content="Hello")
        assert msg.content == "Hello"

    def test_parse_multimodal_content(self):
        """Parse multimodal content array."""
        content = [
            {"type": "text", "text": "What's this?"},
            {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}}
        ]
        msg = Message(role=MessageRole.USER, content=content)
        assert len(msg.content) == 2

    def test_extract_text_from_multimodal(self):
        """Extract text from multimodal message."""
        content = [
            {"type": "text", "text": "Describe this"},
            {"type": "image_url", "image_url": {"url": "..."}}
        ]
        text = extract_text_content(content)
        assert text == "Describe this"

    def test_extract_images_from_multimodal(self):
        """Extract images from multimodal message."""
        content = [
            {"type": "text", "text": "Describe this"},
            {"type": "image_url", "image_url": {"url": "data:image/png;base64,abc123"}}
        ]
        images = extract_images(content)
        assert len(images) == 1
        assert images[0] == "data:image/png;base64,abc123"
```

```python
# baseline-agent-cli/tests/unit/test_tool_registration.py

class TestToolRegistration:
    """Test tool registration and discovery."""

    def test_default_tools_registered(self):
        """Default tools are available."""
        tools = get_registered_tools()
        assert "web_search" in tools
        assert "code_execution" in tools

    def test_tool_schema_valid(self):
        """Tool schemas are valid JSON Schema."""
        for tool in get_registered_tools().values():
            assert "name" in tool
            assert "description" in tool
            assert "parameters" in tool

    def test_disable_tools(self):
        """Tools can be disabled via config."""
        settings = Settings(enable_web_search=False)
        tools = get_registered_tools(settings)
        assert "web_search" not in tools
```

```python
# baseline-agent-cli/tests/unit/test_response_formatting.py

class TestResponseFormatting:
    """Test response formatting utilities."""

    def test_format_streaming_chunk(self):
        """Format SSE streaming chunk."""
        chunk = format_sse_chunk({"content": "Hello"})
        assert chunk.startswith("data: ")
        assert "Hello" in chunk

    def test_format_completion_response(self):
        """Format complete response."""
        response = format_completion({
            "content": "Response text",
            "model": "test-model",
        })
        assert response["choices"][0]["message"]["content"] == "Response text"

    def test_format_tool_call_response(self):
        """Format tool call in response."""
        tool_call = format_tool_call(
            name="web_search",
            arguments={"query": "test"},
            id="call_123"
        )
        assert tool_call["function"]["name"] == "web_search"
```

### FR-3: Integration Tests

```python
# baseline-agent-cli/tests/integration/test_sandy_integration.py

class TestSandyIntegration:
    """Test Sandy sandbox integration."""

    @pytest.mark.integration
    async def test_create_sandbox(self, sandy_client):
        """Create and destroy a sandbox."""
        sandbox_id = await sandy_client.create_sandbox()
        assert sandbox_id.startswith("sbx_")
        await sandy_client.terminate(sandbox_id)

    @pytest.mark.integration
    async def test_execute_command(self, sandy_client):
        """Execute a command in sandbox."""
        sandbox_id = await sandy_client.create_sandbox()
        result = await sandy_client.exec(sandbox_id, "echo 'hello'")
        assert "hello" in result.stdout
        await sandy_client.terminate(sandbox_id)

    @pytest.mark.integration
    async def test_write_and_read_file(self, sandy_client):
        """Write and read file in sandbox."""
        sandbox_id = await sandy_client.create_sandbox()
        await sandy_client.write_file(sandbox_id, "/workspace/test.txt", "content")
        content = await sandy_client.read_file(sandbox_id, "/workspace/test.txt")
        assert content == "content"
        await sandy_client.terminate(sandbox_id)

    @pytest.mark.integration
    async def test_install_package(self, sandy_client):
        """Install a pip package in sandbox."""
        sandbox_id = await sandy_client.create_sandbox()
        result = await sandy_client.exec(sandbox_id, "pip install requests")
        assert result.exit_code == 0
        await sandy_client.terminate(sandbox_id)
```

```python
# baseline-langchain/tests/integration/test_tool_execution.py

class TestToolExecution:
    """Test actual tool execution."""

    @pytest.mark.integration
    async def test_web_search_returns_results(self):
        """Web search tool returns actual results."""
        tool = web_search_tool
        result = await tool.ainvoke({"query": "Python programming"})
        assert len(result) > 0
        assert "Python" in result

    @pytest.mark.integration
    async def test_image_generation_returns_url(self):
        """Image generation returns a valid URL."""
        tool = image_generation_tool
        result = await tool.ainvoke({"prompt": "A red circle"})
        assert "http" in result or "data:image" in result

    @pytest.mark.integration
    async def test_code_execution_runs_safely(self):
        """Code execution runs in sandbox."""
        tool = code_execution_tool
        result = await tool.ainvoke({"code": "print(2 + 2)"})
        assert "4" in result
```

### FR-4: Test Utilities

```python
# tests/utils/__init__.py

import asyncio
from typing import AsyncIterator
import httpx

async def create_test_client(base_url: str) -> httpx.AsyncClient:
    """Create configured test client."""
    return httpx.AsyncClient(
        base_url=base_url,
        timeout=60.0,
        headers={"Content-Type": "application/json"}
    )

async def send_message(
    client: httpx.AsyncClient,
    content: str,
    images: list[str] | None = None,
    timeout: float = 30.0
) -> str:
    """Send a chat message and return response."""
    messages = [{"role": "user", "content": content}]
    if images:
        messages[0]["content"] = [
            {"type": "text", "text": content},
            *[{"type": "image_url", "image_url": {"url": img}} for img in images]
        ]

    response = await client.post(
        "/v1/chat/completions",
        json={"model": "baseline", "messages": messages},
        timeout=timeout
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]

def assert_response_quality(response: str, min_coherence: float = 0.7):
    """Assert response meets quality threshold."""
    # Basic checks
    assert len(response) > 10, "Response too short"
    assert not response.startswith("Error"), "Response is an error"
    # Could add LLM-based coherence scoring here

def extract_code_blocks(text: str) -> list[str]:
    """Extract code blocks from markdown text."""
    import re
    pattern = r'```(?:\w+)?\n(.*?)```'
    return re.findall(pattern, text, re.DOTALL)

def assert_valid_python(code_blocks: list[str]):
    """Assert code blocks are valid Python syntax."""
    import ast
    for code in code_blocks:
        try:
            ast.parse(code)
        except SyntaxError as e:
            raise AssertionError(f"Invalid Python syntax: {e}")
```

### FR-5: Test Configuration

```python
# tests/conftest.py

import pytest
import pytest_asyncio
import httpx

@pytest.fixture(scope="session")
def baseline_cli_url():
    """URL for baseline-agent-cli service."""
    return "http://localhost:8000"

@pytest.fixture(scope="session")
def baseline_langchain_url():
    """URL for baseline-langchain service."""
    return "http://localhost:8001"

@pytest_asyncio.fixture
async def cli_client(baseline_cli_url):
    """Client for baseline-agent-cli."""
    async with httpx.AsyncClient(base_url=baseline_cli_url, timeout=60) as client:
        yield client

@pytest_asyncio.fixture
async def langchain_client(baseline_langchain_url):
    """Client for baseline-langchain."""
    async with httpx.AsyncClient(base_url=baseline_langchain_url, timeout=60) as client:
        yield client

@pytest.fixture(params=["cli", "langchain"])
def client(request, cli_client, langchain_client):
    """Parameterized client for testing both baselines."""
    if request.param == "cli":
        return cli_client
    return langchain_client

def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "smoke: smoke tests")
    config.addinivalue_line("markers", "integration: integration tests")
    config.addinivalue_line("markers", "slow: slow tests")
```

### FR-6: CI Configuration

```yaml
# .github/workflows/baseline-tests.yml

name: Baseline Tests

on:
  push:
    paths:
      - 'baseline-agent-cli/**'
      - 'baseline-langchain/**'
      - 'tests/**'
  pull_request:
    paths:
      - 'baseline-agent-cli/**'
      - 'baseline-langchain/**'
      - 'tests/**'

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          cd baseline-agent-cli && pip install -e ".[dev]"
          cd ../baseline-langchain && pip install -e ".[dev]"

      - name: Run unit tests
        run: |
          cd baseline-agent-cli && pytest tests/unit -v
          cd ../baseline-langchain && pytest tests/unit -v

  smoke-tests:
    runs-on: ubuntu-latest
    needs: unit-tests
    steps:
      - uses: actions/checkout@v4

      - name: Start services
        run: docker-compose up -d

      - name: Wait for services
        run: sleep 30

      - name: Run smoke tests
        run: pytest tests/smoke -v -m smoke

      - name: Stop services
        run: docker-compose down
```

## Non-Functional Requirements

### NFR-1: Test Performance

- Unit tests complete in < 30 seconds
- Smoke tests complete in < 10 minutes
- Integration tests complete in < 5 minutes

### NFR-2: Test Isolation

- Tests are independent and can run in any order
- No shared state between tests
- Sandboxes cleaned up after each test

### NFR-3: Reproducibility

- Tests produce consistent results
- Random elements are seeded
- Network calls mocked where appropriate

## Acceptance Criteria

- [ ] 50+ smoke test scenarios covering all major capabilities
- [ ] Unit tests for all core components (80%+ coverage)
- [ ] Integration tests for external services
- [ ] Test utilities documented and reusable
- [ ] CI pipeline configured and passing
- [ ] Both baseline implementations tested with same scenarios
- [ ] Error handling tests included
- [ ] Documentation on running tests locally

## Files to Create

```
tests/
├── smoke/
│   ├── test_basic_conversations.py
│   ├── test_code_tasks.py
│   ├── test_research_tasks.py
│   ├── test_multimodal_tasks.py
│   ├── test_file_operations.py
│   ├── test_complex_tasks.py
│   ├── test_error_handling.py
│   └── test_domain_tasks.py
├── utils/
│   └── __init__.py
├── conftest.py
└── README.md

baseline-agent-cli/tests/
├── unit/
│   ├── test_message_parsing.py
│   ├── test_tool_registration.py
│   └── test_response_formatting.py
└── integration/
    └── test_sandy_integration.py

baseline-langchain/tests/
├── unit/
│   └── test_tool_schemas.py
└── integration/
    └── test_tool_execution.py

.github/workflows/
└── baseline-tests.yml
```

## Dependencies

```
# test requirements
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-cov>=4.1.0
httpx>=0.25.0
pytest-timeout>=2.2.0
```

## Related Specs

- `specs/21_enhanced_baseline.md` - Baseline implementation
- `specs/27_baseline_langchain.md` - LangChain baseline
- `specs/30_janus_benchmark_infrastructure.md` - Benchmark system

NR_OF_TRIES: 1
