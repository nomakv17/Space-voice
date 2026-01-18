"""Claude API adapter for Retell LLM integration.

This adapter handles:
- Converting Retell transcript format to Claude messages
- Streaming responses from Claude
- Parsing tool calls from Claude's response
- Formatting responses for Retell's Custom LLM protocol

The adapter enables Claude 4.5 Sonnet to power Retell voice agents,
providing superior reasoning and tool-calling capabilities.
"""

from collections.abc import AsyncGenerator
from typing import Any

import structlog
from anthropic import AsyncAnthropic

from app.services.retell.tool_converter import (
    openai_tools_to_claude,
)

logger = structlog.get_logger()

# Claude model for voice conversations
# Using Claude 4.5 Sonnet for best balance of speed and capability
CLAUDE_MODEL = "claude-sonnet-4-5-20250514"


class ClaudeAdapter:
    """Adapts Claude API for Retell's streaming response format.

    Handles the bridge between Retell's Custom LLM WebSocket protocol
    and Claude's Messages API with streaming.
    """

    def __init__(self, api_key: str, timeout: float = 60.0) -> None:
        """Initialize Claude client.

        Args:
            api_key: Anthropic API key
            timeout: Request timeout in seconds
        """
        self.client = AsyncAnthropic(api_key=api_key, timeout=timeout)
        self.logger = logger.bind(component="claude_adapter")

    async def generate_response(
        self,
        transcript: list[dict[str, Any]],
        system_prompt: str,
        tools: list[dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Generate streaming response from Claude.

        Converts Retell transcript to Claude messages, streams the response,
        and yields events compatible with Retell's Custom LLM protocol.

        Args:
            transcript: Retell conversation transcript
            system_prompt: Agent system prompt
            tools: Tool definitions (OpenAI format - will be converted)
            temperature: Response creativity (0.0-1.0)
            max_tokens: Maximum response tokens

        Yields:
            Retell-compatible response events:
            - {"type": "text_delta", "delta": "..."}
            - {"type": "tool_use", "tool_call": {...}}
            - {"type": "message_end"}
        """
        # Convert transcript to Claude messages
        messages = self._convert_transcript_to_messages(transcript)

        # Convert tools to Claude format
        claude_tools = openai_tools_to_claude(tools) if tools else None

        self.logger.debug(
            "generating_response",
            message_count=len(messages),
            tool_count=len(claude_tools) if claude_tools else 0,
        )

        try:
            # Stream response from Claude
            # Note: type ignores are needed because we dynamically construct messages/tools
            async with self.client.messages.stream(
                model=CLAUDE_MODEL,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=messages,  # type: ignore[arg-type]
                tools=claude_tools,  # type: ignore[arg-type]
                temperature=temperature,
            ) as stream:
                current_tool_use: dict[str, Any] | None = None
                current_tool_input = ""

                async for event in stream:
                    # Handle different event types
                    if event.type == "content_block_start":
                        block = event.content_block
                        if block.type == "tool_use":
                            # Starting a tool call
                            current_tool_use = {
                                "id": block.id,
                                "name": block.name,
                            }
                            current_tool_input = ""

                    elif event.type == "content_block_delta":
                        delta = event.delta

                        if delta.type == "text_delta":
                            # Text content - yield for streaming to Retell
                            yield {
                                "type": "text_delta",
                                "delta": delta.text,
                            }

                        elif delta.type == "input_json_delta":
                            # Tool input being streamed
                            current_tool_input += delta.partial_json

                    elif event.type == "content_block_stop":
                        # Content block finished
                        if current_tool_use:
                            # Parse the accumulated tool input
                            import json

                            try:
                                tool_input = (
                                    json.loads(current_tool_input) if current_tool_input else {}
                                )
                            except json.JSONDecodeError:
                                tool_input = {}

                            # Yield complete tool call
                            yield {
                                "type": "tool_use",
                                "tool_call": {
                                    "tool_use_id": current_tool_use["id"],
                                    "name": current_tool_use["name"],
                                    "arguments": tool_input,
                                },
                            }
                            current_tool_use = None
                            current_tool_input = ""

                    elif event.type == "message_stop":
                        # Message complete
                        yield {"type": "message_end"}

        except Exception as e:
            self.logger.exception("claude_generation_error", error=str(e))
            yield {
                "type": "error",
                "error": str(e),
            }

    async def generate_with_tool_results(
        self,
        transcript: list[dict[str, Any]],
        system_prompt: str,
        tools: list[dict[str, Any]],
        tool_results: list[dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Continue generation after tool execution.

        After a tool is executed, this method continues the conversation
        with the tool results included.

        Args:
            transcript: Retell conversation transcript
            system_prompt: Agent system prompt
            tools: Tool definitions (OpenAI format)
            tool_results: Results from executed tools
            temperature: Response creativity
            max_tokens: Maximum response tokens

        Yields:
            Retell-compatible response events
        """
        messages = self._convert_transcript_to_messages(transcript)

        # Add tool results to messages
        if tool_results:
            messages.append(
                {
                    "role": "user",
                    "content": tool_results,
                }
            )

        claude_tools = openai_tools_to_claude(tools) if tools else None

        self.logger.debug(
            "continuing_with_tool_results",
            tool_result_count=len(tool_results),
        )

        try:
            # Note: type ignores are needed because we dynamically construct messages/tools
            async with self.client.messages.stream(
                model=CLAUDE_MODEL,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=messages,  # type: ignore[arg-type]
                tools=claude_tools,  # type: ignore[arg-type]
                temperature=temperature,
            ) as stream:
                async for event in stream:
                    if event.type == "content_block_delta":
                        delta = event.delta
                        if delta.type == "text_delta":
                            yield {
                                "type": "text_delta",
                                "delta": delta.text,
                            }

                    elif event.type == "message_stop":
                        yield {"type": "message_end"}

        except Exception as e:
            self.logger.exception("claude_continuation_error", error=str(e))
            yield {
                "type": "error",
                "error": str(e),
            }

    def _convert_transcript_to_messages(
        self,
        transcript: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Convert Retell transcript format to Claude messages.

        Retell transcript format:
        [
            {"role": "agent", "content": "Hello, how can I help?"},
            {"role": "user", "content": "I need to book an appointment"},
            ...
        ]

        Claude messages format:
        [
            {"role": "assistant", "content": "Hello, how can I help?"},
            {"role": "user", "content": "I need to book an appointment"},
            ...
        ]

        Args:
            transcript: Retell conversation transcript

        Returns:
            Claude-format messages list
        """
        messages: list[dict[str, Any]] = []

        for utterance in transcript:
            role = utterance.get("role", "")
            content = utterance.get("content", "")

            # Skip empty content
            if not content or not content.strip():
                continue

            # Map Retell roles to Claude roles
            # In Retell: "agent" = our AI, "user" = the caller
            if role == "agent":
                claude_role = "assistant"
            elif role == "user":
                claude_role = "user"
            else:
                # Skip unknown roles
                self.logger.warning("unknown_role", role=role)
                continue

            # Claude requires alternating roles
            # If same role as previous, merge content
            if messages and messages[-1]["role"] == claude_role:
                messages[-1]["content"] += f"\n{content}"
            else:
                messages.append(
                    {
                        "role": claude_role,
                        "content": content,
                    }
                )

        # Ensure conversation starts with user message (Claude requirement)
        if messages and messages[0]["role"] == "assistant":
            # Prepend a placeholder user message
            messages.insert(
                0,
                {
                    "role": "user",
                    "content": "[Call connected]",
                },
            )

        return messages

    def build_voice_system_prompt(
        self,
        base_prompt: str,
        language: str = "en-US",
        timezone: str = "UTC",
    ) -> str:
        """Build a system prompt optimized for voice conversations.

        Wraps the base prompt with voice-specific instructions that help
        Claude generate natural, conversational responses suitable for
        text-to-speech synthesis.

        Args:
            base_prompt: The agent's custom system prompt
            language: Language code (e.g., "en-US")
            timezone: Timezone for time-based operations

        Returns:
            Complete system prompt for voice conversations
        """
        from datetime import datetime

        try:
            from zoneinfo import ZoneInfo

            tz = ZoneInfo(timezone)
            now = datetime.now(tz)
            current_time = now.strftime("%A, %B %d, %Y at %I:%M %p")
        except Exception:
            current_time = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")

        return f"""You are a professional voice AI assistant currently on a phone call.

CRITICAL VOICE RULES:
1. Keep responses SHORT - 1-2 sentences maximum per turn
2. Speak naturally as if on a phone call - no lists, bullets, or markdown
3. Never say "I cannot" or "I'm unable" - find helpful alternatives
4. Use conversational filler words naturally: "Let me check...", "One moment...", "Alright..."
5. Confirm understanding before taking actions
6. For numbers, speak them naturally (say "five five five" not "555")
7. Spell out abbreviations that might confuse speech synthesis

CONTEXT:
- Current time: {current_time} ({timezone})
- Language: {language}

YOUR INSTRUCTIONS:
{base_prompt}

TOOL USAGE:
- When using tools, first tell the user what you're doing
- After getting results, summarize them naturally in speech
- Never read raw data - always interpret and explain"""
