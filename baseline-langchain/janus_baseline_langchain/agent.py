"""LangChain agent setup for the baseline implementation."""

from typing import Any, Union, cast

from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from pydantic.v1 import SecretStr

from janus_baseline_langchain.config import Settings
from janus_baseline_langchain.router.chat_model import CompositeRoutingChatModel
from janus_baseline_langchain.tools import (
    code_execution_tool,
    image_generation_tool,
    InvestigateMemoryTool,
    music_generation_tool,
    text_to_speech_tool,
    web_search_tool,
)

SYSTEM_PROMPT = """You are Janus, an intelligent assistant competing in The Rodeo.

You have access to these tools:
- image_generation: Generate images using AI (Chutes API)
- text_to_speech: Convert text to audio (Kokoro TTS)
- music_generation: Generate full songs or instrumentals (DiffRhythm)
- web_search: Search the web for current information
- code_execution: Execute Python code safely

Always use the appropriate tool for the task. For image requests, use image_generation.
For audio/speech requests, use text_to_speech.
For music or song generation, use music_generation.
For questions about current events or real-time data, use web_search.
For calculations or data processing, use code_execution.
"""


def create_llm(settings: Settings) -> Union[CompositeRoutingChatModel, ChatOpenAI]:
    """Create the LLM instance based on settings."""
    api_key = settings.chutes_api_key or settings.openai_api_key or "dummy-key"

    if settings.use_model_router:
        return CompositeRoutingChatModel(
            api_key=api_key,
            base_url=settings.openai_base_url,
            default_temperature=settings.temperature,
        )

    return ChatOpenAI(
        model=settings.model,
        api_key=SecretStr(api_key),
        base_url=settings.openai_base_url,
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
) -> AgentExecutor:
    """Create a LangChain agent executor configured for Janus."""
    llm = create_llm(settings)

    tools = [
        image_generation_tool,
        text_to_speech_tool,
        music_generation_tool,
        web_search_tool,
        code_execution_tool,
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
        max_iterations=10,
        return_intermediate_steps=True,
    )
