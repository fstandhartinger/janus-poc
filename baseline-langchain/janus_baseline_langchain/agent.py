"""LangChain agent setup for the baseline implementation."""

from typing import Any, Union, cast

from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from janus_baseline_langchain.config import Settings
from janus_baseline_langchain.router.chat_model import CompositeRoutingChatModel
from janus_baseline_langchain.tools import (
    audio_generation_tool,
    clone_repository_tool,
    code_execution_tool,
    create_directory_tool,
    deep_research_tool,
    file_read_tool,
    file_write_tool,
    image_generation_tool,
    InvestigateMemoryTool,
    list_repository_files_tool,
    music_generation_tool,
    read_repository_file_tool,
    text_to_speech_tool,
    video_generation_tool,
    web_search_tool,
)

SYSTEM_PROMPT = """You are Janus, an intelligent assistant competing in The Rodeo.

You have access to these tools:
- image_generation: Generate images using AI (Chutes API)
- text_to_speech: Convert text to audio (Kokoro TTS)
- music_generation: Generate full songs or instrumentals (DiffRhythm)
- audio_generation: Generate audio or sound effects
- video_generation: Generate videos from text prompts
- web_search: Search the web for current information
- deep_research: Perform comprehensive research with citations
- code_execution: Execute Python code safely
- clone_repository: Clone a git repository
- list_repository_files: List files in a cloned repository
- read_repository_file: Read files from a cloned repository
- write_file: Write content to a file artifact
- read_file: Read content from a file artifact
- create_directory: Create a working directory for file operations

Always use the appropriate tool for the task. For image requests, use image_generation.
For audio/speech requests, use text_to_speech.
For music or song generation, use music_generation.
For sound effects or other audio requests, use audio_generation.
For video requests, use video_generation.
For questions about current events or real-time data, use web_search.
For comprehensive research, use deep_research.
For calculations or data processing, use code_execution.
For repository tasks, use clone_repository and list_repository_files.
For reading repo files, use read_repository_file.
For file operations, use create_directory and write_file.

## Generative UI responses

You can include interactive UI widgets in your responses using the `html-gen-ui` code fence. This renders as an interactive iframe in chat.

When to use:
- Calculators, converters, unit transformations
- Data visualization (charts, graphs)
- Interactive forms or quizzes
- Simple games or puzzles
- Visual demonstrations

Requirements:
1. Self-contained HTML/CSS/JS in one block
2. Dark theme styling with light text
3. Mobile-friendly layout (320px minimum width)
4. No external API calls
5. Wrap JavaScript in try/catch

Example:
```html-gen-ui
<!DOCTYPE html>
<html>
<head>
  <style>
    body {{ background: #1a1a2e; color: #e0e0e0; font-family: system-ui; padding: 1rem; margin: 0; }}
    button {{ background: #63D297; color: #1a1a2e; border: none; padding: 0.5rem 1rem; border-radius: 6px; }}
  </style>
</head>
<body>
  <h3 style="margin-top:0">Quick Counter</h3>
  <button onclick="inc()">+1</button>
  <span id="count">0</span>
  <script>
    try {{
      var count = 0;
      function inc() {{
        count += 1;
        document.getElementById('count').textContent = String(count);
      }}
    }} catch (error) {{
      console.error('Widget error:', error);
    }}
  </script>
</body>
</html>
```

Recommended CDNs (optional):
- https://cdn.jsdelivr.net/npm/chart.js
- https://cdn.jsdelivr.net/npm/d3@7
- https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.min.js
- https://unpkg.com/leaflet@1.9.4/dist/leaflet.js
"""


def create_llm(
    settings: Settings,
    *,
    api_key_override: str | None = None,
    base_url_override: str | None = None,
) -> Union[CompositeRoutingChatModel, ChatOpenAI]:
    """Create the LLM instance based on settings."""
    api_key = api_key_override or settings.chutes_api_key or settings.openai_api_key or "dummy-key"
    base_url = base_url_override or settings.openai_base_url

    if settings.use_model_router and not api_key_override:
        return CompositeRoutingChatModel(
            api_key=api_key,
            base_url=base_url,
            default_temperature=settings.temperature,
        )

    return ChatOpenAI(
        model=settings.model,
        api_key=SecretStr(api_key),
        base_url=base_url,
        temperature=settings.temperature,
        streaming=True,
        max_retries=settings.max_retries,
        timeout=settings.request_timeout,
    )


def create_agent(
    settings: Settings,
    *,
    user_id: str | None = None,
    enable_memory: bool = False,
    has_memory_context: bool = False,
    api_key_override: str | None = None,
    base_url_override: str | None = None,
) -> AgentExecutor:
    """Create a LangChain agent executor configured for Janus."""
    llm = create_llm(
        settings,
        api_key_override=api_key_override,
        base_url_override=base_url_override,
    )

    tools = [
        image_generation_tool,
        text_to_speech_tool,
        music_generation_tool,
        audio_generation_tool,
        video_generation_tool,
        web_search_tool,
        deep_research_tool,
        code_execution_tool,
        clone_repository_tool,
        list_repository_files_tool,
        read_repository_file_tool,
        file_write_tool,
        file_read_tool,
        create_directory_tool,
    ]
    if settings.enable_memory_feature and enable_memory and user_id and has_memory_context:
        tools.append(
            InvestigateMemoryTool(
                user_id=user_id,
                memory_service_url=settings.memory_service_url,
                timeout_seconds=settings.memory_timeout_seconds,
            )
        )

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ]
    )

    agent = create_openai_tools_agent(cast(BaseChatModel, llm), tools, prompt)

    return AgentExecutor(
        agent=cast(Any, agent),
        tools=tools,
        verbose=settings.debug,
        handle_parsing_errors=True,
        max_iterations=15,
        return_intermediate_steps=True,
    )
