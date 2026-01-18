"""OpenAI API adapter for Retell LLM integration.

This adapter handles:
- Converting Retell transcript format to OpenAI messages
- Streaming responses from GPT-4o mini
- Parsing tool calls from OpenAI's response
- Formatting responses for Retell's Custom LLM protocol

GPT-4o mini provides fast responses ideal for voice applications,
with excellent tool-calling capabilities.
"""

from collections.abc import AsyncGenerator
from typing import Any

import structlog
from openai import AsyncOpenAI

logger = structlog.get_logger()

# Default model for voice conversations
# GPT-4o mini provides fast responses with good quality
DEFAULT_MODEL = "gpt-4o-mini"


class OpenAIAdapter:
    """Adapts OpenAI API for Retell's streaming response format.

    Handles the bridge between Retell's Custom LLM WebSocket protocol
    and OpenAI's Chat Completions API with streaming.
    """

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_MODEL,
        timeout: float = 60.0,
    ) -> None:
        """Initialize OpenAI client.

        Args:
            api_key: OpenAI API key
            model: Model to use (default: gpt-4o-mini)
            timeout: Request timeout in seconds
        """
        self.client = AsyncOpenAI(api_key=api_key, timeout=timeout)
        self.model = model
        self.logger = logger.bind(component="openai_adapter")

    async def generate_response(
        self,
        transcript: list[dict[str, Any]],
        system_prompt: str,
        tools: list[dict[str, Any]],
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Generate streaming response from OpenAI.

        Converts Retell transcript to OpenAI messages, streams the response,
        and yields events compatible with Retell's Custom LLM protocol.

        Args:
            transcript: Retell conversation transcript
            system_prompt: Agent system prompt
            tools: Tool definitions (OpenAI format)
            temperature: Response creativity (0.0-1.0)
            max_tokens: Maximum response tokens

        Yields:
            Retell-compatible response events:
            - {"type": "text_delta", "delta": "..."}
            - {"type": "tool_use", "tool_call": {...}}
            - {"type": "message_end"}
        """
        # Convert transcript to OpenAI messages
        messages = self._convert_transcript_to_messages(transcript, system_prompt)

        self.logger.debug(
            "generating_response",
            model=self.model,
            message_count=len(messages),
            tool_count=len(tools) if tools else 0,
        )

        try:
            # Prepare API call parameters
            params: dict[str, Any] = {
                "model": self.model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "stream": True,
            }

            # Add tools if available
            if tools:
                params["tools"] = tools
                params["tool_choice"] = "auto"

            # Stream response from OpenAI
            stream = await self.client.chat.completions.create(**params)

            # Track tool calls being built (OpenAI sends them incrementally)
            current_tool_calls: dict[int, dict[str, Any]] = {}

            async for chunk in stream:
                choice = chunk.choices[0] if chunk.choices else None
                if not choice:
                    continue

                delta = choice.delta

                # Handle text content
                if delta.content:
                    yield {
                        "type": "text_delta",
                        "delta": delta.content,
                    }

                # Handle tool calls (OpenAI sends them incrementally)
                if delta.tool_calls:
                    for tool_call in delta.tool_calls:
                        idx = tool_call.index

                        # Initialize or update tool call
                        if idx not in current_tool_calls:
                            current_tool_calls[idx] = {
                                "id": tool_call.id or "",
                                "name": "",
                                "arguments": "",
                            }

                        # Update with new data
                        if tool_call.id:
                            current_tool_calls[idx]["id"] = tool_call.id
                        if tool_call.function:
                            if tool_call.function.name:
                                current_tool_calls[idx]["name"] = tool_call.function.name
                            if tool_call.function.arguments:
                                current_tool_calls[idx]["arguments"] += tool_call.function.arguments

                # Check for finish reason
                if choice.finish_reason:
                    # If we have tool calls, yield them now
                    if choice.finish_reason == "tool_calls" or current_tool_calls:
                        for _idx, tc in sorted(current_tool_calls.items()):
                            # Parse arguments JSON
                            import json

                            try:
                                args = json.loads(tc["arguments"]) if tc["arguments"] else {}
                            except json.JSONDecodeError:
                                args = {}

                            yield {
                                "type": "tool_use",
                                "tool_call": {
                                    "tool_use_id": tc["id"],
                                    "name": tc["name"],
                                    "arguments": args,
                                },
                            }

                    # Message complete
                    yield {"type": "message_end"}

        except Exception as e:
            self.logger.exception("openai_generation_error", error=str(e))
            yield {
                "type": "error",
                "error": str(e),
            }

    async def generate_with_tool_results(
        self,
        transcript: list[dict[str, Any]],
        system_prompt: str,
        tools: list[dict[str, Any]],
        tool_calls: list[dict[str, Any]],
        tool_results: list[dict[str, Any]],
        assistant_text_before_tools: str = "",
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Continue generation after tool execution.

        After a tool is executed, this method continues the conversation
        with the tool results included.

        OpenAI's API requires:
        1. Assistant message with text (if any) AND tool_calls
        2. Tool messages with results for each tool call

        Args:
            transcript: Retell conversation transcript
            system_prompt: Agent system prompt
            tools: Tool definitions (OpenAI format)
            tool_calls: The original tool calls made
            tool_results: Results from executed tools (Claude format - will convert)
            assistant_text_before_tools: Text said before making tool calls
            temperature: Response creativity
            max_tokens: Maximum response tokens

        Yields:
            Retell-compatible response events
        """
        messages = self._convert_transcript_to_messages(transcript, system_prompt)

        # Add assistant message with tool calls
        if tool_calls:
            assistant_message: dict[str, Any] = {
                "role": "assistant",
                "content": assistant_text_before_tools.strip() if assistant_text_before_tools else None,
                "tool_calls": [],
            }

            # Convert tool calls to OpenAI format
            for tc in tool_calls:
                import json

                assistant_message["tool_calls"].append(
                    {
                        "id": tc.get("tool_use_id"),
                        "type": "function",
                        "function": {
                            "name": tc.get("name"),
                            "arguments": json.dumps(tc.get("arguments", {})),
                        },
                    }
                )

            messages.append(assistant_message)

            # Add tool result messages (OpenAI uses separate messages per tool)
            for result in tool_results:
                # Convert from Claude tool_result format to OpenAI tool message
                tool_use_id = result.get("tool_use_id")
                content = result.get("content", "")
                is_error = result.get("is_error", False)

                # If content is not a string, serialize it
                if not isinstance(content, str):
                    import json

                    content = json.dumps(content)

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_use_id,
                        "content": f"Error: {content}" if is_error else content,
                    }
                )

        self.logger.debug(
            "continuing_with_tool_results",
            tool_result_count=len(tool_results),
            message_count=len(messages),
        )

        try:
            self.logger.debug("starting_openai_stream_for_tool_results")

            # Prepare API call parameters
            params: dict[str, Any] = {
                "model": self.model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "stream": True,
            }

            if tools:
                params["tools"] = tools
                params["tool_choice"] = "auto"

            stream = await self.client.chat.completions.create(**params)

            event_count = 0
            current_tool_calls: dict[int, dict[str, Any]] = {}

            async for chunk in stream:
                event_count += 1
                choice = chunk.choices[0] if chunk.choices else None
                if not choice:
                    continue

                delta = choice.delta

                # Handle text content
                if delta.content:
                    yield {
                        "type": "text_delta",
                        "delta": delta.content,
                    }

                # Handle tool calls
                if delta.tool_calls:
                    for tool_call in delta.tool_calls:
                        idx = tool_call.index

                        if idx not in current_tool_calls:
                            current_tool_calls[idx] = {
                                "id": tool_call.id or "",
                                "name": "",
                                "arguments": "",
                            }

                        if tool_call.id:
                            current_tool_calls[idx]["id"] = tool_call.id
                        if tool_call.function:
                            if tool_call.function.name:
                                current_tool_calls[idx]["name"] = tool_call.function.name
                            if tool_call.function.arguments:
                                current_tool_calls[idx]["arguments"] += tool_call.function.arguments

                # Check for finish reason
                if choice.finish_reason:
                    # Yield any tool calls
                    if choice.finish_reason == "tool_calls" or current_tool_calls:
                        for _idx, tc in sorted(current_tool_calls.items()):
                            import json

                            try:
                                args = json.loads(tc["arguments"]) if tc["arguments"] else {}
                            except json.JSONDecodeError:
                                args = {}

                            yield {
                                "type": "tool_use",
                                "tool_call": {
                                    "tool_use_id": tc["id"],
                                    "name": tc["name"],
                                    "arguments": args,
                                },
                            }

                    self.logger.debug("openai_stream_complete", total_events=event_count)
                    yield {"type": "message_end"}

            if event_count == 0:
                self.logger.warning("openai_stream_no_events")

        except Exception as e:
            self.logger.exception("openai_continuation_error", error=str(e))
            yield {
                "type": "error",
                "error": str(e),
            }

    def _convert_transcript_to_messages(
        self,
        transcript: list[dict[str, Any]],
        system_prompt: str,
    ) -> list[dict[str, Any]]:
        """Convert Retell transcript format to OpenAI messages.

        Retell transcript format:
        [
            {"role": "agent", "content": "Hello, how can I help?"},
            {"role": "user", "content": "I need to book an appointment"},
            ...
        ]

        OpenAI messages format:
        [
            {"role": "system", "content": "System prompt..."},
            {"role": "assistant", "content": "Hello, how can I help?"},
            {"role": "user", "content": "I need to book an appointment"},
            ...
        ]

        Args:
            transcript: Retell conversation transcript
            system_prompt: System prompt for the conversation

        Returns:
            OpenAI-format messages list
        """
        # Start with system message
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt}
        ]

        for utterance in transcript:
            role = utterance.get("role", "")
            # Strip whitespace from content - speech-to-text often includes trailing spaces
            content = utterance.get("content", "").strip()

            # Skip empty content
            if not content:
                continue

            # Map Retell roles to OpenAI roles
            if role == "agent":
                openai_role = "assistant"
            elif role == "user":
                openai_role = "user"
            else:
                self.logger.warning("unknown_role", role=role)
                continue

            # OpenAI allows consecutive messages of the same role
            # but for consistency, merge them like Claude adapter does
            if len(messages) > 1 and messages[-1]["role"] == openai_role:
                messages[-1]["content"] += f"\n{content}"
            else:
                messages.append(
                    {
                        "role": openai_role,
                        "content": content,
                    }
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
        the model generate natural, conversational responses suitable for
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
