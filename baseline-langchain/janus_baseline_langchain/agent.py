"""LangChain agent setup for the baseline implementation."""

from typing import Any, cast

from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from pydantic.v1 import SecretStr

from janus_baseline_langchain.config import Settings
from janus_baseline_langchain.tools import (
    code_execution_tool,
    image_generation_tool,
    text_to_speech_tool,
    web_search_tool,
)

SYSTEM_PROMPT = """You are Janus, an intelligent assistant competing in The Rodeo.

You have access to these tools:
- image_generation: Generate images using AI (Chutes API)
- text_to_speech: Convert text to audio (Kokoro TTS)
- web_search: Search the web for current information
- code_execution: Execute Python code safely

Always use the appropriate tool for the task. For image requests, use image_generation.
For audio/speech requests, use text_to_speech.
For questions about current events or real-time data, use web_search.
For calculations or data processing, use code_execution.
"""


def create_agent(settings: Settings) -> AgentExecutor:
    """Create a LangChain agent executor configured for Janus."""
    api_key = (
        SecretStr(settings.openai_api_key)
        if settings.openai_api_key
        else SecretStr("dummy-key")
    )
    llm = ChatOpenAI(
        model=settings.model,
        api_key=api_key,
        base_url=settings.openai_base_url,
        temperature=settings.temperature,
        streaming=True,
        max_retries=settings.max_retries,
        timeout=settings.request_timeout,
    )

    tools = [
        image_generation_tool,
        text_to_speech_tool,
        web_search_tool,
        code_execution_tool,
    ]

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ]
    )

    agent = create_openai_tools_agent(llm, tools, prompt)

    return AgentExecutor(
        agent=cast(Any, agent),
        tools=tools,
        verbose=settings.debug,
        max_iterations=10,
        return_intermediate_steps=True,
    )
