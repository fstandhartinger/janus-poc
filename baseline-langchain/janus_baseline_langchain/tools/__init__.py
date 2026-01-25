"""Tool registry for the LangChain baseline."""

from janus_baseline_langchain.tools.audio import audio_generation_tool
from janus_baseline_langchain.tools.code_exec import code_execution_tool
from janus_baseline_langchain.tools.deep_research import deep_research_tool
from janus_baseline_langchain.tools.files import file_read_tool, file_write_tool
from janus_baseline_langchain.tools.image_gen import image_generation_tool
from janus_baseline_langchain.tools.memory import InvestigateMemoryTool
from janus_baseline_langchain.tools.music_gen import music_generation_tool
from janus_baseline_langchain.tools.tts import text_to_speech_tool, tts_tool
from janus_baseline_langchain.tools.video import video_generation_tool
from janus_baseline_langchain.tools.web_search import web_search_tool

__all__ = [
    "code_execution_tool",
    "audio_generation_tool",
    "deep_research_tool",
    "file_read_tool",
    "file_write_tool",
    "image_generation_tool",
    "InvestigateMemoryTool",
    "music_generation_tool",
    "text_to_speech_tool",
    "tts_tool",
    "video_generation_tool",
    "web_search_tool",
]
