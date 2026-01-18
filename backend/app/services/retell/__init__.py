"""Retell AI integration for voice orchestration with Claude LLM backend.

This module provides:
- RetellService: Manages Retell agents, phone numbers, and calls via the Retell SDK
- ClaudeAdapter: Adapts Claude API for Retell's streaming response format
- RetellLLMServer: Custom LLM WebSocket server that bridges Retell to Claude
- Tool converters: Convert between OpenAI and Claude tool formats
"""

from app.services.retell.claude_adapter import ClaudeAdapter
from app.services.retell.retell_llm_server import RetellLLMServer
from app.services.retell.retell_service import RetellService
from app.services.retell.tool_converter import (
    claude_tools_to_openai,
    format_tool_call_for_retell,
    format_tool_result_for_claude,
    format_tool_result_for_retell,
    openai_tools_to_claude,
    parse_tool_call_from_claude,
)

__all__ = [
    "ClaudeAdapter",
    "RetellLLMServer",
    "RetellService",
    "claude_tools_to_openai",
    "format_tool_call_for_retell",
    "format_tool_result_for_claude",
    "format_tool_result_for_retell",
    "openai_tools_to_claude",
    "parse_tool_call_from_claude",
]
