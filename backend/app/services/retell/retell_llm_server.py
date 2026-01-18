"""Retell Custom LLM WebSocket Server using Claude 4.5 Sonnet.

This server implements Retell's Custom LLM WebSocket protocol, allowing
Claude to power voice conversations while Retell handles:
- Speech-to-Text (STT)
- Text-to-Speech (TTS)
- Barge-in detection
- Turn-taking logic

Protocol flow:
1. Retell connects to our WebSocket
2. We send config message
3. Retell sends call_details with metadata
4. For each user utterance, Retell sends response_required
5. We stream Claude's response back
6. If tools are called, we execute them and continue

Reference: https://docs.retellai.com/api-references/llm-websocket
"""

import json
import uuid
from typing import Any

import structlog
from fastapi import WebSocket

from app.services.retell.claude_adapter import ClaudeAdapter
from app.services.retell.tool_converter import (
    format_tool_call_for_retell,
    format_tool_result_for_claude,
    format_tool_result_for_retell,
)
from app.services.tools.registry import ToolRegistry

logger = structlog.get_logger()


class RetellLLMServer:
    """WebSocket server that bridges Retell to Claude with tool calling.

    Handles the Retell Custom LLM protocol:
    - Receives conversation updates from Retell
    - Generates responses using Claude
    - Executes tools and returns results
    - Streams responses back to Retell for TTS
    """

    def __init__(
        self,
        websocket: WebSocket,
        claude_adapter: ClaudeAdapter,
        tool_registry: ToolRegistry,
        system_prompt: str,
        enabled_tools: list[str],
        enabled_tool_ids: dict[str, list[str]] | None = None,
        agent_config: dict[str, Any] | None = None,
    ) -> None:
        """Initialize the LLM server.

        Args:
            websocket: FastAPI WebSocket connection
            claude_adapter: Claude API adapter for generating responses
            tool_registry: Registry of available tools
            system_prompt: Agent's system prompt (already voice-optimized)
            enabled_tools: List of enabled tool integration IDs
            enabled_tool_ids: Granular tool selection per integration
            agent_config: Additional agent configuration (temperature, language, etc.)
        """
        self.websocket = websocket
        self.claude = claude_adapter
        self.tool_registry = tool_registry
        self.system_prompt = system_prompt
        self.enabled_tools = enabled_tools
        self.enabled_tool_ids = enabled_tool_ids
        self.agent_config = agent_config or {}

        self.session_id = str(uuid.uuid4())
        self.call_id: str | None = None
        self.logger = logger.bind(
            component="retell_llm_server",
            session_id=self.session_id,
        )

        # Get tool definitions in OpenAI format (will be converted for Claude)
        self.openai_tools = tool_registry.get_all_tool_definitions(
            enabled_tools=enabled_tools,
            enabled_tool_ids=enabled_tool_ids,
        )

    async def handle_connection(self) -> None:
        """Main WebSocket handler for Retell LLM communication.

        Processes incoming messages and routes them to appropriate handlers.
        Runs until the connection is closed.
        """
        from starlette.websockets import WebSocketDisconnect

        self.logger.info("retell_llm_connection_started")

        try:
            # Send initial configuration
            await self._send_config()

            # Process incoming messages
            async for message in self.websocket.iter_text():
                try:
                    data = json.loads(message)
                    await self._handle_message(data)
                except json.JSONDecodeError as e:
                    self.logger.warning("invalid_json", error=str(e))
                except WebSocketDisconnect:
                    # Normal disconnection during message handling - don't log as error
                    self.logger.info("websocket_disconnected_during_handling")
                    break
                except Exception as e:
                    # Only log as error if it's not a normal disconnect
                    if "WebSocket" in str(e) or "disconnect" in str(e).lower():
                        self.logger.info("websocket_closed", reason=str(e))
                    else:
                        self.logger.exception("message_handler_error", error=str(e))

        except WebSocketDisconnect:
            # Normal disconnection - Retell closed the connection
            self.logger.info("retell_closed_connection")
        except Exception as e:
            # Only log unexpected errors
            if "WebSocket" in str(e) or "disconnect" in str(e).lower():
                self.logger.info("connection_closed", reason=str(e))
            else:
                self.logger.exception("connection_error", error=str(e))
        finally:
            self.logger.info("retell_llm_connection_closed")

    async def _send_config(self) -> None:
        """Send initial configuration to Retell.

        Configures the LLM connection with options like:
        - auto_reconnect: Whether Retell should reconnect on disconnect
        - call_details: Request call metadata
        """
        config = {
            "response_type": "config",
            "config": {
                "auto_reconnect": True,
                "call_details": True,
            },
        }
        await self._send(config)
        self.logger.debug("config_sent")

    async def _handle_message(self, data: dict[str, Any]) -> None:
        """Route incoming message to appropriate handler.

        Args:
            data: Parsed JSON message from Retell
        """
        interaction_type = data.get("interaction_type")

        if interaction_type == "ping_pong":
            await self._handle_ping_pong(data)

        elif interaction_type == "call_details":
            await self._handle_call_details(data)

        elif interaction_type == "update_only":
            # Transcript update, no response needed
            self.logger.debug(
                "transcript_update", transcript_length=len(data.get("transcript", []))
            )

        elif interaction_type == "response_required":
            await self._handle_response_required(data)

        elif interaction_type == "reminder_required":
            # User has been silent, may need to prompt them
            await self._handle_reminder_required(data)

        else:
            self.logger.warning("unknown_interaction_type", type=interaction_type)

    async def _handle_ping_pong(self, data: dict[str, Any]) -> None:
        """Respond to ping with pong to keep connection alive.

        Args:
            data: Ping message with timestamp
        """
        await self._send(
            {
                "response_type": "ping_pong",
                "timestamp": data.get("timestamp"),
            }
        )

    async def _handle_call_details(self, data: dict[str, Any]) -> None:
        """Process call details when call starts.

        After receiving call details, we proactively send an initial greeting.
        This is required because Retell's Custom LLM protocol expects the agent
        to speak first - Retell won't send response_required until after we greet.

        Args:
            data: Call details including call_id, metadata, etc.
        """
        call = data.get("call", {})
        self.call_id = call.get("call_id")

        self.logger = self.logger.bind(call_id=self.call_id)
        self.logger.info(
            "call_details_received",
            from_number=call.get("from_number"),
            to_number=call.get("to_number"),
            metadata=call.get("metadata"),
        )

        # Send initial greeting - the agent must speak first in Custom LLM mode
        await self._send_initial_greeting()

    async def _send_initial_greeting(self) -> None:
        """Send initial greeting when call starts.

        Custom LLM agents must proactively greet the caller. We use a static
        greeting for minimal latency - voice conversations are very sensitive
        to delays, and generating with Claude would add 1-3 seconds.

        Uses the agent's configured initial_greeting if set, otherwise a default.
        """
        self.logger.info("sending_initial_greeting")

        # Use custom greeting from agent config (initial_greeting field)
        greeting = self.agent_config.get("greeting")
        if not greeting:
            # Default greeting if none configured
            greeting = "Hello, thanks for calling! How can I help you today?"

        await self._send_response(
            response_id=0,
            content=greeting,
            content_complete=True,
        )
        self.logger.info("initial_greeting_sent", greeting_length=len(greeting))

    async def _handle_response_required(self, data: dict[str, Any]) -> None:
        """Generate and stream response when Retell needs one.

        This is the main response generation flow:
        1. Get transcript from Retell
        2. Generate streaming response from Claude
        3. If Claude calls tools, execute them
        4. Stream final response back to Retell

        Args:
            data: Request data including transcript and response_id
        """
        response_id = data.get("response_id", 0)
        transcript = data.get("transcript", [])

        self.logger.info(
            "generating_response",
            response_id=response_id,
            transcript_turns=len(transcript),
        )

        # Stream response from Claude
        accumulated_content = ""
        pending_tool_calls: list[dict[str, Any]] = []

        async for event in self.claude.generate_response(
            transcript=transcript,
            system_prompt=self.system_prompt,
            tools=self.openai_tools,
            temperature=self.agent_config.get("temperature", 0.7),
            max_tokens=self.agent_config.get("max_tokens", 1024),
        ):
            event_type = event.get("type")

            if event_type == "text_delta":
                # Stream text content to Retell
                delta = event.get("delta", "")
                accumulated_content += delta
                await self._send_response(
                    response_id=response_id,
                    content=delta,
                    content_complete=False,
                )

            elif event_type == "tool_use":
                # Tool call detected
                tool_call = event.get("tool_call", {})
                pending_tool_calls.append(tool_call)

            elif event_type == "error":
                self.logger.error("claude_error", error=event.get("error"))
                await self._send_response(
                    response_id=response_id,
                    content="I apologize, I'm having trouble processing that. Could you repeat?",
                    content_complete=True,
                )
                return

        # Execute any pending tool calls
        if pending_tool_calls:
            # CRITICAL: Mark the text response complete BEFORE executing tools
            # Retell has a short timeout - if we don't send content_complete=True,
            # Retell will disconnect and reconnect thinking we've stalled
            if accumulated_content:
                await self._send_response(
                    response_id=response_id,
                    content="",
                    content_complete=True,
                )

            # Pass the accumulated text that Claude said BEFORE the tool calls
            # This is critical - Claude's API needs both text and tool_use in the same message
            await self._execute_tool_calls(
                response_id, transcript, pending_tool_calls, accumulated_content
            )
        else:
            # No tools - mark response complete
            await self._send_response(
                response_id=response_id,
                content="",
                content_complete=True,
            )

    async def _handle_reminder_required(self, data: dict[str, Any]) -> None:
        """Handle reminder when user has been silent.

        Retell sends this when the user hasn't spoken for a while.
        We generate a gentle prompt to re-engage them.

        Args:
            data: Reminder request with transcript
        """
        response_id = data.get("response_id", 0)
        transcript = data.get("transcript", [])

        self.logger.info("reminder_required", response_id=response_id)

        # Add context that this is a reminder
        reminder_transcript = [
            *transcript,
            {
                "role": "system",
                "content": "[The user has been silent. Gently check if they're still there or need help.]",
            },
        ]

        # Generate a brief reminder response
        async for event in self.claude.generate_response(
            transcript=reminder_transcript,
            system_prompt=self.system_prompt,
            tools=[],  # No tools for reminders
            temperature=0.7,
            max_tokens=100,  # Keep reminders short
        ):
            if event.get("type") == "text_delta":
                await self._send_response(
                    response_id=response_id,
                    content=event.get("delta", ""),
                    content_complete=False,
                )

        await self._send_response(
            response_id=response_id,
            content="",
            content_complete=True,
        )

    async def _execute_tool_calls(
        self,
        response_id: int,
        transcript: list[dict[str, Any]],
        tool_calls: list[dict[str, Any]],
        assistant_text: str = "",
    ) -> None:
        """Execute tool calls and continue the conversation.

        Args:
            response_id: Retell response ID
            transcript: Current conversation transcript
            tool_calls: List of tool calls to execute
            assistant_text: Text Claude said BEFORE the tool calls (e.g., "Let me check...")
        """
        tool_results: list[dict[str, Any]] = []

        for tool_call in tool_calls:
            tool_name = tool_call.get("name", "")
            tool_use_id = tool_call.get("tool_use_id", str(uuid.uuid4()))
            arguments = tool_call.get("arguments", {})

            self.logger.info(
                "executing_tool",
                tool_name=tool_name,
                tool_use_id=tool_use_id,
            )

            # Notify Retell about tool invocation
            await self._send(
                format_tool_call_for_retell(
                    tool_use_id=tool_use_id,
                    tool_name=tool_name,
                    arguments=arguments,
                )
            )

            # Execute the tool
            try:
                result = await self.tool_registry.execute_tool(tool_name, arguments)
                is_error = False
            except Exception as e:
                self.logger.exception("tool_execution_error", tool_name=tool_name, error=str(e))
                result = {"error": str(e)}
                is_error = True

            # Send tool result to Retell
            await self._send(
                format_tool_result_for_retell(
                    tool_call_id=tool_use_id,
                    result=result,
                )
            )

            # Collect result for Claude
            tool_results.append(
                format_tool_result_for_claude(
                    tool_use_id=tool_use_id,
                    result=result,
                    is_error=is_error,
                )
            )

            # Check for special actions
            if isinstance(result, dict):
                if result.get("action") == "end_call":
                    await self._send_response(
                        response_id=response_id,
                        content=result.get("message", "Goodbye!"),
                        content_complete=True,
                        end_call=True,
                    )
                    return

                if result.get("action") == "transfer_call":
                    await self._send_response(
                        response_id=response_id,
                        content=result.get("message", "Transferring you now."),
                        content_complete=True,
                        transfer_number=result.get("transfer_number"),
                    )
                    return

        # Continue conversation with tool results
        # Pass tool_calls, tool_results, AND the assistant's text before tool calls
        # Claude's API requires the assistant message to have BOTH text and tool_use blocks
        self.logger.info(
            "continuing_after_tools",
            tool_call_count=len(tool_calls),
            tool_result_count=len(tool_results),
            has_assistant_text=bool(assistant_text),
        )

        has_response = False
        async for event in self.claude.generate_with_tool_results(
            transcript=transcript,
            system_prompt=self.system_prompt,
            tools=self.openai_tools,
            tool_calls=tool_calls,
            tool_results=tool_results,
            assistant_text_before_tools=assistant_text,
            temperature=self.agent_config.get("temperature", 0.7),
        ):
            event_type = event.get("type")

            if event_type == "text_delta":
                has_response = True
                await self._send_response(
                    response_id=response_id,
                    content=event.get("delta", ""),
                    content_complete=False,
                )

            elif event_type == "error":
                # Claude API error - send fallback response
                self.logger.error(
                    "claude_error_after_tools",
                    error=event.get("error"),
                )
                await self._send_response(
                    response_id=response_id,
                    content="I apologize, I'm having trouble processing that. Could you repeat?",
                    content_complete=True,
                )
                return

        # Mark response complete
        if not has_response:
            self.logger.warning("no_response_after_tools")

        await self._send_response(
            response_id=response_id,
            content="",
            content_complete=True,
        )

    async def _send_response(
        self,
        response_id: int,
        content: str,
        content_complete: bool,
        end_call: bool = False,
        transfer_number: str | None = None,
    ) -> None:
        """Send response chunk to Retell.

        Args:
            response_id: Retell's response ID for this turn
            content: Text content to speak
            content_complete: Whether this is the final chunk
            end_call: Whether to end the call after this response
            transfer_number: Phone number to transfer the call to
        """
        response: dict[str, Any] = {
            "response_type": "response",
            "response_id": response_id,
            "content": content,
            "content_complete": content_complete,
        }

        if end_call:
            response["end_call"] = True

        if transfer_number:
            response["transfer_number"] = transfer_number

        await self._send(response)

    async def _send(self, data: dict[str, Any]) -> None:
        """Send JSON message to Retell.

        Args:
            data: Message to send
        """
        await self.websocket.send_text(json.dumps(data))
