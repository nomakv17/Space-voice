"""Tool format converter between OpenAI and Claude.

OpenAI and Claude use slightly different formats for function/tool calling.
This module handles bidirectional conversion to allow the existing ToolRegistry
(which uses OpenAI format) to work with Claude's API.

OpenAI Format:
{
    "type": "function",
    "name": "search_customer",
    "description": "Search for a customer...",
    "parameters": {"type": "object", "properties": {...}, "required": [...]}
}

Claude Format:
{
    "name": "search_customer",
    "description": "Search for a customer...",
    "input_schema": {"type": "object", "properties": {...}, "required": [...]}
}
"""

import json
from typing import Any


def openai_tools_to_claude(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert OpenAI function calling format to Claude tool format.

    Args:
        tools: List of OpenAI-format tool definitions

    Returns:
        List of Claude-format tool definitions
    """
    claude_tools: list[dict[str, Any]] = []

    for tool in tools:
        # Handle nested "function" format (some OpenAI tools use this)
        if tool.get("type") == "function" and "function" in tool:
            func = tool["function"]
            claude_tools.append(
                {
                    "name": func.get("name"),
                    "description": func.get("description", ""),
                    "input_schema": func.get("parameters", {"type": "object", "properties": {}}),
                }
            )
        # Handle flat format (name, description, parameters at top level)
        elif tool.get("type") == "function":
            claude_tools.append(
                {
                    "name": tool.get("name"),
                    "description": tool.get("description", ""),
                    "input_schema": tool.get("parameters", {"type": "object", "properties": {}}),
                }
            )
        # Handle already-Claude-format tools
        elif "input_schema" in tool:
            claude_tools.append(tool)
        # Fallback for any other format
        else:
            claude_tools.append(
                {
                    "name": tool.get("name", "unknown"),
                    "description": tool.get("description", ""),
                    "input_schema": tool.get("parameters")
                    or tool.get("input_schema")
                    or {
                        "type": "object",
                        "properties": {},
                    },
                }
            )

    return claude_tools


def claude_tools_to_openai(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert Claude tool format to OpenAI function calling format.

    Args:
        tools: List of Claude-format tool definitions

    Returns:
        List of OpenAI-format tool definitions
    """
    openai_tools: list[dict[str, Any]] = []

    for tool in tools:
        openai_tools.append(
            {
                "type": "function",
                "name": tool.get("name"),
                "description": tool.get("description", ""),
                "parameters": tool.get("input_schema", {"type": "object", "properties": {}}),
            }
        )

    return openai_tools


def format_tool_result_for_claude(
    tool_use_id: str,
    result: dict[str, Any] | str,
    is_error: bool = False,
) -> dict[str, Any]:
    """Format a tool execution result for Claude's expected format.

    Args:
        tool_use_id: The tool_use block ID from Claude's response
        result: The tool execution result (dict or string)
        is_error: Whether this is an error result

    Returns:
        Claude-format tool_result message content block
    """
    # Convert result to string if it's a dict
    content = json.dumps(result, default=str) if isinstance(result, dict) else str(result)

    return {
        "type": "tool_result",
        "tool_use_id": tool_use_id,
        "content": content,
        "is_error": is_error,
    }


def parse_tool_call_from_claude(content_block: dict[str, Any]) -> dict[str, Any] | None:
    """Parse a tool_use content block from Claude's response.

    Args:
        content_block: A content block from Claude's response

    Returns:
        Dict with tool call details or None if not a tool call
    """
    if content_block.get("type") != "tool_use":
        return None

    return {
        "tool_use_id": content_block.get("id"),
        "name": content_block.get("name"),
        "arguments": content_block.get("input", {}),
    }


def format_tool_call_for_retell(
    tool_use_id: str,
    tool_name: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Format a tool call for Retell's Custom LLM protocol.

    Args:
        tool_use_id: Unique ID for this tool call
        tool_name: Name of the tool being called
        arguments: Tool input arguments

    Returns:
        Retell-format tool call invocation message
    """
    return {
        "response_type": "tool_call_invocation",
        "tool_call_id": tool_use_id,
        "name": tool_name,
        "arguments": json.dumps(arguments) if isinstance(arguments, dict) else arguments,
    }


def format_tool_result_for_retell(
    tool_call_id: str,
    result: dict[str, Any] | str,
) -> dict[str, Any]:
    """Format a tool result for Retell's Custom LLM protocol.

    Args:
        tool_call_id: The tool call ID this result is for
        result: The tool execution result

    Returns:
        Retell-format tool call result message
    """
    content = json.dumps(result, default=str) if isinstance(result, dict) else str(result)

    return {
        "response_type": "tool_call_result",
        "tool_call_id": tool_call_id,
        "content": content,
    }
