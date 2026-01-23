"""Retell Custom LLM WebSocket Server.

This server implements Retell's Custom LLM WebSocket protocol, allowing
LLMs (Claude or GPT-4o) to power voice conversations while Retell handles:
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

import asyncio
import contextlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import structlog
from fastapi import WebSocket

from app.services.retell.claude_adapter import ClaudeAdapter
from app.services.retell.openai_adapter import OpenAIAdapter
from app.services.retell.tool_converter import (
    format_tool_result_for_claude,
)
from app.services.tools.registry import ToolRegistry

# Type alias for LLM adapters (both have same interface)
LLMAdapter = ClaudeAdapter | OpenAIAdapter

logger = structlog.get_logger()


@dataclass
class PendingToolExecution:
    """Tracks a background tool execution task."""

    response_id: int
    transcript: list[dict[str, Any]]
    tool_calls: list[dict[str, Any]]
    assistant_text: str
    task: asyncio.Task[None]


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
        llm_adapter: LLMAdapter,
        tool_registry: ToolRegistry,
        system_prompt: str,
        enabled_tools: list[str],
        enabled_tool_ids: dict[str, list[str]] | None = None,
        agent_config: dict[str, Any] | None = None,
    ) -> None:
        """Initialize the LLM server.

        Args:
            websocket: FastAPI WebSocket connection
            llm_adapter: LLM adapter (Claude or OpenAI) for generating responses
            tool_registry: Registry of available tools
            system_prompt: Agent's system prompt (already voice-optimized)
            enabled_tools: List of enabled tool integration IDs
            enabled_tool_ids: Granular tool selection per integration
            agent_config: Additional agent configuration (temperature, language, etc.)
        """
        self.websocket = websocket
        self.llm = llm_adapter
        self.tool_registry = tool_registry
        self.system_prompt = system_prompt
        self.enabled_tools = enabled_tools
        self.enabled_tool_ids = enabled_tool_ids
        self.agent_config = agent_config or {}

        self.session_id = str(uuid.uuid4())
        self.call_id: str | None = None
        self.caller_phone: str | None = None  # Stored when call_details received
        self.logger = logger.bind(
            component="retell_llm_server",
            session_id=self.session_id,
        )

        # Get tool definitions in OpenAI format (will be converted for Claude)
        self.openai_tools = tool_registry.get_all_tool_definitions(
            enabled_tools=enabled_tools,
            enabled_tool_ids=enabled_tool_ids,
        )

        # State for concurrent handling - allows tool execution without blocking WebSocket
        self._pending_tool_execution: PendingToolExecution | None = None
        self._response_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._shutdown: asyncio.Event = asyncio.Event()
        self._current_response_id: int = 0
        self._last_activity_time: float = 0.0  # Track last WebSocket activity

        # Session-level deduplication to prevent double SMS/calendar bookings
        self._sent_sms_numbers: set[str] = set()  # Track phone numbers we've sent SMS to
        self._booking_completed: bool = False  # Track if ANY booking has been made (one per call)

        # Prevent recursive tool call spam
        self._recursive_tool_depth: int = 0  # Track depth of recursive tool calls
        self._max_recursive_depth: int = 2  # Max 2 levels of recursive tools
        self._said_one_moment: bool = False  # Only say "one moment" once per turn
        self._said_goodbye: bool = False  # Track if we've already said goodbye
        self._current_turn_text: str = ""  # Accumulate text for goodbye detection

    def _is_goodbye_message(self, text: str) -> bool:
        """Check if text contains a goodbye/call-ending phrase.

        Used to auto-detect when to set end_call=True.
        IMPORTANT: Must NOT trigger on greetings like "Hello, thank you for calling"
        """
        if not text:
            return False
        text_lower = text.lower()

        # If it starts with a greeting, it's NOT a goodbye
        greeting_starts = [
            "hello",
            "hi ",
            "hi,",
            "hey",
            "good morning",
            "good afternoon",
            "good evening",
        ]
        if any(text_lower.strip().startswith(g) for g in greeting_starts):
            return False

        # Must have an EXPLICIT goodbye phrase (not just "thank you for calling")
        explicit_goodbye_patterns = [
            "goodbye",
            "good bye",
            "bye!",
            "bye.",
            "bye,",
            "have a great day",
            "have a good day",
            "have a nice day",
            "take care",
        ]
        return any(pattern in text_lower for pattern in explicit_goodbye_patterns)

    async def handle_connection(self) -> None:
        """Main WebSocket handler for Retell LLM communication.

        Uses concurrent architecture to prevent tool execution from blocking:
        - _message_receiver: Reads WebSocket messages, always responds to ping_pong
        - _response_sender: Sends queued responses from background tool execution
        - _connection_keepalive: Sends periodic keepalives to prevent Retell timeout

        This ensures ping_pong is always answered even during slow tool execution.
        """
        from starlette.websockets import WebSocketDisconnect

        print("[LLM SERVER] Connection started, sending config...", flush=True)
        self.logger.info("retell_llm_connection_started")
        self._last_activity_time = asyncio.get_event_loop().time()

        try:
            # Send initial configuration
            await self._send_config()
            print("[LLM SERVER] Config sent, starting message loop...", flush=True)

            # Run message receiver, response sender, and keepalive concurrently
            # The keepalive runs for the ENTIRE connection lifetime to prevent timeouts
            results = await asyncio.gather(
                self._message_receiver(),
                self._response_sender(),
                self._connection_keepalive(),
                return_exceptions=True,
            )

            # Check for exceptions that were silently caught
            task_names = ["message_receiver", "response_sender", "connection_keepalive"]
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    print(
                        f"[TASK ERROR] {task_names[i]} failed: {type(result).__name__}: {result}",
                        flush=True,
                    )
                    self.logger.error(
                        "task_failed",
                        task=task_names[i],
                        error=str(result),
                        error_type=type(result).__name__,
                    )

        except WebSocketDisconnect:
            self.logger.info("retell_closed_connection")
        except Exception as e:
            if "WebSocket" in str(e) or "disconnect" in str(e).lower():
                self.logger.info("connection_closed", reason=str(e))
            else:
                self.logger.exception("connection_error", error=str(e))
        finally:
            # Clean shutdown
            self._shutdown.set()
            await self._cancel_pending_tool_execution()
            self.logger.info("retell_llm_connection_closed")

    async def _connection_keepalive(self) -> None:
        """Send periodic keepalives to prevent Retell timeout.

        Retell disconnects after ~5-7 seconds of inactivity. This task runs
        for the entire connection lifetime, sending empty response chunks
        every 1.5 seconds if no other activity has occurred.

        This is SEPARATE from the response-level keepalives and ensures the
        connection stays alive even between conversation turns.
        """
        keepalive_interval = 1.5  # Send every 1.5 seconds (more aggressive)
        retry_count = 0
        max_retries = 5  # More retries before giving up

        self.logger.info("connection_keepalive_started", interval=keepalive_interval)

        while not self._shutdown.is_set():
            try:
                await asyncio.sleep(keepalive_interval)

                if self._shutdown.is_set():
                    break

                # Check time since last activity
                current_time = asyncio.get_event_loop().time()
                time_since_activity = current_time - self._last_activity_time

                # Only send keepalive if we haven't had recent activity
                if time_since_activity >= keepalive_interval - 0.3:
                    self.logger.debug(
                        "connection_keepalive_sending",
                        seconds_since_activity=round(time_since_activity, 1),
                    )
                    # Send empty response chunk as keepalive
                    await self._send_response(
                        response_id=self._current_response_id,
                        content="",
                        content_complete=False,
                    )
                    self._last_activity_time = current_time
                    retry_count = 0  # Reset retry count on success

            except asyncio.CancelledError:
                self.logger.debug("connection_keepalive_cancelled")
                break
            except Exception as e:
                retry_count += 1
                self.logger.warning(
                    "connection_keepalive_failed",
                    error=str(e),
                    retry_count=retry_count,
                )
                if retry_count >= max_retries:
                    self.logger.error("connection_keepalive_max_retries_exceeded")
                    break
                # Very short delay before retry
                await asyncio.sleep(0.2)

        self.logger.info("connection_keepalive_stopped")

    async def _message_receiver(self) -> None:
        """Read WebSocket messages and route to handlers.

        CRITICAL: This method NEVER blocks on tool execution.
        Tools are spawned as background tasks so ping_pong always gets answered.
        """
        import sys

        from starlette.websockets import WebSocketDisconnect

        try:
            async for message in self.websocket.iter_text():
                if self._shutdown.is_set():
                    break

                # LOG RAW MESSAGE - Critical for debugging
                # Show first 300 chars to catch response_required
                print(f"[WS RAW] <<< {message[:300]}", flush=True)
                sys.stdout.flush()
                sys.stderr.flush()

                # Update activity time on every received message
                self._last_activity_time = asyncio.get_event_loop().time()

                try:
                    data = json.loads(message)
                    interaction_type = data.get("interaction_type", "unknown")
                    print(f"[LLM SERVER] Received: {interaction_type}", flush=True)
                    sys.stdout.flush()
                    await self._handle_message(data)
                except json.JSONDecodeError as e:
                    self.logger.warning("invalid_json", error=str(e))
                except WebSocketDisconnect:
                    self.logger.info("websocket_disconnected_during_handling")
                    break
                except Exception as e:
                    if "WebSocket" in str(e) or "disconnect" in str(e).lower():
                        self.logger.info("websocket_closed", reason=str(e))
                    else:
                        self.logger.exception("message_handler_error", error=str(e))

        except WebSocketDisconnect:
            print("[LLM SERVER] WebSocket disconnected!", flush=True)
        finally:
            print("[LLM SERVER] Message receiver stopped", flush=True)
            self._shutdown.set()

    async def _response_sender(self) -> None:
        """Process queued responses from background tool execution.

        Runs concurrently with _message_receiver, checking the queue for
        tool results that need to be sent back to Retell.
        """
        while not self._shutdown.is_set():
            try:
                # Short timeout to check shutdown flag frequently
                item = await asyncio.wait_for(self._response_queue.get(), timeout=0.1)
            except TimeoutError:
                continue

            try:
                if item["type"] == "tool_results":
                    await self._continue_after_tools_from_queue(item)
                elif item["type"] == "special_action":
                    await self._handle_special_action_from_queue(item)
                elif item["type"] == "error":
                    await self._send_error_response(item["response_id"])
            except Exception as e:
                self.logger.exception("response_sender_error", error=str(e))

    async def _cancel_pending_tool_execution(self) -> None:
        """Cancel any pending tool execution on shutdown or interruption."""
        if self._pending_tool_execution:
            self._pending_tool_execution.task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._pending_tool_execution.task
            self._pending_tool_execution = None
            self.logger.info("tool_execution_cancelled")

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
            print("[LLM SERVER] *** RESPONSE REQUIRED - User spoke! ***", flush=True)
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
        print("[CALL DETAILS] Processing call details...", flush=True)
        call = data.get("call", {})
        self.call_id = call.get("call_id")
        self.caller_phone = call.get("from_number")  # Store caller's phone number

        self.logger = self.logger.bind(call_id=self.call_id)
        self.logger.info(
            "call_details_received",
            from_number=self.caller_phone,
            to_number=call.get("to_number"),
            metadata=call.get("metadata"),
        )

        # Inject current date/time so the agent knows what day it is
        # This allows correct date calculation when users say "Tuesday" or "tomorrow"
        # Using Saskatchewan timezone for Yorkton, Canada (no DST)
        central_tz = ZoneInfo("America/Regina")
        now = datetime.now(central_tz)
        from datetime import timedelta

        # Build explicit day-to-date mapping for the next 7 days
        day_mapping = []
        for i in range(7):
            future_date = now + timedelta(days=i)
            day_name = future_date.strftime("%A")
            date_str = future_date.strftime("%B %d, %Y")
            if i == 0:
                day_mapping.append(f"- TODAY ({day_name}) = {date_str}")
            elif i == 1:
                day_mapping.append(f"- TOMORROW ({day_name}) = {date_str}")
            else:
                day_mapping.append(f"- {day_name} = {date_str}")
        day_mapping_str = "\n".join(day_mapping)

        # Log the actual date being injected for debugging
        self.logger.info(
            "date_injection",
            today=now.strftime("%A, %B %d, %Y"),
            time=now.strftime("%I:%M %p %Z"),
            iso=now.isoformat(),
        )

        date_info = f"""

CURRENT DATE & TIME (USE THESE EXACT DATES - DO NOT CALCULATE):
{day_mapping_str}

Current time: {now.strftime("%I:%M %p")} Saskatchewan Time

CRITICAL: When customer says a day name (Monday, Tuesday, etc.), use the EXACT date from the list above. DO NOT add or subtract days. Confirm the full date with the customer before booking."""
        self.system_prompt += date_info

        # Append caller phone info to system prompt so agent can use it for SMS/booking
        if self.caller_phone:
            self.system_prompt += f"\n\nCALLER INFORMATION:\n- Caller Phone: {self.caller_phone}\n- Use this phone number for SMS confirmations and include in booking descriptions."

        # Send initial greeting - the agent must speak first in Custom LLM mode
        await self._send_initial_greeting()

    async def _send_initial_greeting(self) -> None:
        """Send initial greeting when call starts.

        Custom LLM agents must proactively greet the caller. We use a static
        greeting for minimal latency - voice conversations are very sensitive
        to delays, and generating with Claude would add 1-3 seconds.

        Uses the agent's configured initial_greeting if set, otherwise a default.
        """
        print("[GREETING] Sending initial greeting...", flush=True)
        self.logger.info("sending_initial_greeting")

        # Use custom greeting from agent config (initial_greeting field)
        greeting = self.agent_config.get("greeting")
        if not greeting:
            # Default greeting if none configured
            greeting = "Hello, thanks for calling! How can I help you today?"

        print(f"[GREETING] Greeting text: {greeting[:50]}...", flush=True)

        await self._send_response(
            response_id=0,
            content=greeting,
            content_complete=True,
        )
        print("[GREETING] Greeting sent successfully!", flush=True)
        self.logger.info("initial_greeting_sent", greeting_length=len(greeting))

    async def _handle_response_required(self, data: dict[str, Any]) -> None:
        """Generate and stream response when Retell needs one.

        This is the main response generation flow:
        1. Get transcript from Retell
        2. Generate streaming response from Claude
        3. If Claude calls tools, spawn BACKGROUND task (don't block!)
        4. Return immediately so we can handle ping_pong while tools run

        Args:
            data: Request data including transcript and response_id
        """
        import sys

        print("[LLM] *** _handle_response_required ENTERED ***", flush=True)
        sys.stdout.flush()
        sys.stderr.flush()

        response_id = data.get("response_id", 0)
        transcript = data.get("transcript", [])

        # Track current response_id for stale response detection
        self._current_response_id = response_id

        # Reset per-turn state for new user turn
        self._recursive_tool_depth = 0
        self._said_one_moment = False

        # If user interrupted during tool execution, cancel it
        if self._pending_tool_execution:
            self.logger.info("user_interrupted_tool_execution")
            await self._cancel_pending_tool_execution()

        self.logger.info(
            "generating_response",
            response_id=response_id,
            transcript_turns=len(transcript),
        )

        # Log user's message for debugging
        if transcript:
            last_utterance = transcript[-1] if transcript else {}
            print(f"[LLM] User said: {last_utterance.get('content', '')[:100]}", flush=True)

        # Stream response from Claude/OpenAI
        accumulated_content = ""
        pending_tool_calls: list[dict[str, Any]] = []

        # Keepalive mechanism: Track last activity time
        # Retell times out after ~5-7 seconds of inactivity
        last_activity_time = [asyncio.get_event_loop().time()]
        keepalive_interval = 1.5

        async def send_keepalives() -> None:
            """Background task to send keepalives during Claude's thinking time."""
            while True:
                await asyncio.sleep(keepalive_interval)
                time_since_activity = asyncio.get_event_loop().time() - last_activity_time[0]
                if time_since_activity >= keepalive_interval:
                    self.logger.debug(
                        "sending_keepalive_initial", seconds_since_activity=time_since_activity
                    )
                    await self._send_response(
                        response_id=response_id,
                        content="",
                        content_complete=False,
                    )
                    last_activity_time[0] = asyncio.get_event_loop().time()

        keepalive_task = asyncio.create_task(send_keepalives())

        print("[LLM] Starting response generation...", flush=True)

        try:
            async for event in self.llm.generate_response(
                transcript=transcript,
                system_prompt=self.system_prompt,
                tools=self.openai_tools,
                temperature=self.agent_config.get("temperature", 0.7),
                max_tokens=self.agent_config.get("max_tokens", 1024),
            ):
                last_activity_time[0] = asyncio.get_event_loop().time()
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
                    error_msg = event.get("error", "unknown error")
                    print(f"[LLM ERROR] Generation error: {error_msg}", flush=True)
                    print(f"[LLM ERROR] Full event: {event}", flush=True)
                    self.logger.error("llm_generation_error", error=error_msg, full_event=event)
                    await self._send_response(
                        response_id=response_id,
                        content="I apologize, I'm having trouble processing that. Could you repeat?",
                        content_complete=True,
                    )
                    return
        finally:
            keepalive_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await keepalive_task

        # Execute any pending tool calls
        if pending_tool_calls:
            self.logger.info(
                "initial_tool_calls_detected",
                tool_count=len(pending_tool_calls),
                tool_names=[t.get("name") for t in pending_tool_calls],
            )

            # Send "thinking" message if Claude didn't say anything
            if not accumulated_content:
                accumulated_content = "One moment please."
                await self._send_response(
                    response_id=response_id,
                    content=accumulated_content,
                    content_complete=False,
                )

            # DO NOT mark response complete yet!
            # We'll send content_complete=True after the confirmation message
            # The connection keepalive will keep Retell connected

            # CRITICAL: Spawn background task - DON'T AWAIT!
            # This returns immediately so we can handle ping_pong while tools run
            task = asyncio.create_task(
                self._execute_tools_background(
                    response_id=response_id,
                    transcript=transcript,
                    tool_calls=pending_tool_calls,
                    assistant_text=accumulated_content,
                )
            )
            self._pending_tool_execution = PendingToolExecution(
                response_id=response_id,
                transcript=transcript,
                tool_calls=pending_tool_calls,
                assistant_text=accumulated_content,
                task=task,
            )
            self.logger.info(
                "tool_execution_spawned_background",
                tool_count=len(pending_tool_calls),
            )

            # CRITICAL: Check for goodbye BEFORE returning for tool execution
            # Otherwise goodbye detection never fires (it only runs on content_complete=True)
            if self._is_goodbye_message(accumulated_content):
                self._said_goodbye = True
                print(f"[GOODBYE DETECTED BEFORE TOOLS] {accumulated_content[:60]}...", flush=True)

            # Return immediately - don't block!
            return

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

        try:
            # Add context that this is a reminder
            reminder_transcript = [
                *transcript,
                {
                    "role": "system",
                    "content": "[The user has been silent. Gently check if they're still there or need help.]",
                },
            ]

            # Generate a brief reminder response
            async for event in self.llm.generate_response(
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
                elif event.get("type") == "error":
                    print(f"[REMINDER LLM ERROR] {event.get('error')}", flush=True)

            await self._send_response(
                response_id=response_id,
                content="",
                content_complete=True,
            )
        except Exception as e:
            print(f"[REMINDER ERROR] {type(e).__name__}: {e}", flush=True)
            # Send a safe fallback response - suppress errors if connection is dead
            with contextlib.suppress(Exception):
                await self._send_response(
                    response_id=response_id,
                    content="Are you still there?",
                    content_complete=True,
                )

    async def _execute_tools_background(
        self,
        response_id: int,
        transcript: list[dict[str, Any]],
        tool_calls: list[dict[str, Any]],
        assistant_text: str = "",
    ) -> None:
        """Execute tools in background and queue results for sending.

        This runs as a background task so it doesn't block the WebSocket handler.
        Results are put in the response queue for _response_sender to process.

        Args:
            response_id: Retell response ID
            transcript: Current conversation transcript
            tool_calls: List of tool calls to execute
            assistant_text: Text Claude said BEFORE the tool calls
        """
        try:
            tool_results: list[dict[str, Any]] = []

            for tool_call in tool_calls:
                tool_name = tool_call.get("name", "")
                tool_use_id = tool_call.get("tool_use_id", str(uuid.uuid4()))
                arguments = tool_call.get("arguments", {})

                self.logger.info(
                    "executing_tool_background",
                    tool_name=tool_name,
                    tool_use_id=tool_use_id,
                )

                # DEDUPLICATION: Prevent double SMS sends in same session
                if tool_name in ("telnyx_send_sms", "twilio_send_sms"):
                    to_number = arguments.get("to", "")
                    if to_number in self._sent_sms_numbers:
                        print(f"[SMS DEDUP] Blocked duplicate to {to_number}", flush=True)
                        self.logger.warning(
                            "duplicate_sms_blocked",
                            tool_name=tool_name,
                            to_number=to_number,
                        )
                        result = {
                            "success": True,
                            "message": f"SMS already sent to {to_number} in this session (duplicate blocked)",
                            "deduplicated": True,
                        }
                        tool_results.append(
                            format_tool_result_for_claude(
                                tool_use_id=tool_use_id,
                                result=result,
                                is_error=False,
                            )
                        )
                        continue  # Skip to next tool call

                # DEDUPLICATION: Only ONE booking per call - block all subsequent attempts
                if tool_name == "google_calendar_create_event":
                    if self._booking_completed:
                        self.logger.warning(
                            "duplicate_booking_blocked",
                            tool_name=tool_name,
                            reason="booking_already_completed_this_session",
                        )
                        print("[CALENDAR DEDUP] Blocked - already booked this call!", flush=True)
                        result = {
                            "success": True,
                            "message": "Appointment already booked in this call. No additional booking needed.",
                            "deduplicated": True,
                        }
                        tool_results.append(
                            format_tool_result_for_claude(
                                tool_use_id=tool_use_id,
                                result=result,
                                is_error=False,
                            )
                        )
                        continue  # Skip to next tool call
                    # Set flag BEFORE execution to prevent race condition
                    self._booking_completed = True
                    print("[CALENDAR] Blocking future bookings NOW (before execution)", flush=True)

                # Execute the tool
                # Debug print for SMS tools to diagnose sending issues
                if tool_name in ("telnyx_send_sms", "twilio_send_sms"):
                    print(
                        f"[SMS] Executing {tool_name} to {arguments.get('to', 'unknown')}",
                        flush=True,
                    )

                try:
                    result = await self.tool_registry.execute_tool(tool_name, arguments)
                    is_error = False

                    # Track successful SMS sends for deduplication
                    if tool_name in ("telnyx_send_sms", "twilio_send_sms"):
                        to_number = arguments.get("to", "")
                        if result.get("success"):
                            self._sent_sms_numbers.add(to_number)
                            print(f"[SMS] Sent successfully to {to_number}", flush=True)
                            self.logger.info("sms_sent_tracked", to_number=to_number)
                        else:
                            print(
                                f"[SMS ERROR] Failed to send to {to_number}: {result.get('error', 'unknown')}",
                                flush=True,
                            )

                    # Note: Calendar booking tracking now happens BEFORE execution (race condition fix)

                except Exception as e:
                    self.logger.exception("tool_execution_error", tool_name=tool_name, error=str(e))
                    result = {"error": str(e)}
                    is_error = True

                # Check for special actions
                if isinstance(result, dict):
                    if result.get("action") == "end_call":
                        await self._response_queue.put(
                            {
                                "type": "special_action",
                                "action": "end_call",
                                "response_id": response_id,
                                "message": result.get("message", "Goodbye!"),
                            }
                        )
                        return

                    if result.get("action") == "transfer_call":
                        await self._response_queue.put(
                            {
                                "type": "special_action",
                                "action": "transfer_call",
                                "response_id": response_id,
                                "message": result.get("message", "Transferring you now."),
                                "transfer_number": result.get("transfer_number"),
                            }
                        )
                        return

                # Collect result for Claude
                tool_results.append(
                    format_tool_result_for_claude(
                        tool_use_id=tool_use_id,
                        result=result,
                        is_error=is_error,
                    )
                )

            # Queue results for continuation
            await self._response_queue.put(
                {
                    "type": "tool_results",
                    "response_id": response_id,
                    "transcript": transcript,
                    "tool_calls": tool_calls,
                    "tool_results": tool_results,
                    "assistant_text": assistant_text,
                }
            )
            self.logger.info(
                "tool_results_queued",
                tool_count=len(tool_calls),
                result_count=len(tool_results),
            )

        except asyncio.CancelledError:
            self.logger.info("tool_execution_cancelled")
            raise
        except Exception as e:
            self.logger.exception("tool_execution_background_error", error=str(e))
            await self._response_queue.put(
                {
                    "type": "error",
                    "response_id": response_id,
                    "error": str(e),
                }
            )
        finally:
            self._pending_tool_execution = None

    async def _continue_after_tools_from_queue(self, item: dict[str, Any]) -> None:
        """Continue conversation after tools complete (called from response sender).

        Args:
            item: Queued item with tool results
        """
        original_response_id = item["response_id"]
        transcript = item["transcript"]
        tool_calls = item["tool_calls"]
        tool_results = item["tool_results"]
        assistant_text = item["assistant_text"]

        # CRITICAL: Always use the ORIGINAL response_id from when tools started
        # Using _current_response_id causes race condition - if user speaks while
        # tools execute, _current_response_id changes but Retell still expects
        # response for the original turn. Using wrong response_id = connection drop.
        response_id = original_response_id
        if self._current_response_id != original_response_id:
            self.logger.info(
                "response_id_changed_during_tool_execution",
                original_id=original_response_id,
                current_id=self._current_response_id,
                using_id=response_id,
            )

        self.logger.info(
            "continuing_after_tools",
            tool_call_count=len(tool_calls),
            tool_result_count=len(tool_results),
        )

        # Continue conversation with Claude using tool results
        accumulated_text = ""
        new_tool_calls: list[dict[str, Any]] = []

        # Keepalive mechanism: Track last activity time
        # Retell times out after ~5-7 seconds of inactivity
        last_activity_time = [asyncio.get_event_loop().time()]  # Use list for mutability
        keepalive_interval = 1.5  # Send keepalive every 2 seconds

        async def send_keepalives() -> None:
            """Background task to send keepalives during Claude's thinking time."""
            try:
                self.logger.debug("keepalive_task_started_continuation")
                while True:
                    await asyncio.sleep(keepalive_interval)
                    time_since_activity = asyncio.get_event_loop().time() - last_activity_time[0]
                    if time_since_activity >= keepalive_interval:
                        self.logger.debug(
                            "sending_keepalive", seconds_since_activity=time_since_activity
                        )
                        try:
                            await self._send_response(
                                response_id=response_id,
                                content="",  # Empty content = keepalive
                                content_complete=False,
                            )
                        except Exception as e:
                            self.logger.error("keepalive_send_failed", error=str(e))
                            break
                        last_activity_time[0] = asyncio.get_event_loop().time()
            except asyncio.CancelledError:
                self.logger.debug("keepalive_task_cancelled")
                raise
            except Exception as e:
                self.logger.exception("keepalive_task_error", error=str(e))

        # Start keepalive task
        keepalive_task = asyncio.create_task(send_keepalives())
        self.logger.debug("keepalive_task_created_for_tool_continuation")

        try:
            async for event in self.llm.generate_with_tool_results(
                transcript=transcript,
                system_prompt=self.system_prompt,
                tools=self.openai_tools,
                tool_calls=tool_calls,
                tool_results=tool_results,
                assistant_text_before_tools=assistant_text,
                temperature=self.agent_config.get("temperature", 0.7),
            ):
                # Update activity time on any event
                last_activity_time[0] = asyncio.get_event_loop().time()
                event_type = event.get("type")

                if event_type == "text_delta":
                    delta = event.get("delta", "")
                    accumulated_text += delta
                    await self._send_response(
                        response_id=response_id,
                        content=delta,
                        content_complete=False,
                    )

                elif event_type == "tool_use":
                    # Claude wants another tool - collect for recursive execution
                    new_tool_call = event.get("tool_call", {})
                    new_tool_calls.append(new_tool_call)
                    self.logger.info(
                        "recursive_tool_call_detected",
                        tool_name=new_tool_call.get("name"),
                    )

                elif event_type == "error":
                    error_msg = event.get("error", "unknown error")
                    print(f"[LLM ERROR] Error after tools: {error_msg}", flush=True)
                    self.logger.error("claude_error_after_tools", error=error_msg)
                    await self._send_response(
                        response_id=response_id,
                        content="I apologize, I'm having trouble. Could you repeat?",
                        content_complete=True,
                    )
                    return
        finally:
            # Always cancel keepalive task when done
            keepalive_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await keepalive_task

        # Handle recursive tool calls (with depth limit to prevent spam)
        if new_tool_calls:
            self._recursive_tool_depth += 1
            self.logger.info(
                "recursive_tool_calls_detected",
                tool_count=len(new_tool_calls),
                tool_names=[t.get("name") for t in new_tool_calls],
                depth=self._recursive_tool_depth,
            )

            # Limit recursive depth to prevent infinite loops
            if self._recursive_tool_depth > self._max_recursive_depth:
                self.logger.warning(
                    "max_recursive_depth_exceeded",
                    depth=self._recursive_tool_depth,
                    skipping_tools=[t.get("name") for t in new_tool_calls],
                )
                # Skip these tools and proceed to confirmation
                new_tool_calls = []
            else:
                # Only say "one moment" if we haven't said goodbye and haven't said it this turn
                if not self._said_goodbye and not self._said_one_moment and not accumulated_text:
                    self._said_one_moment = True
                    accumulated_text = "One moment please..."
                    await self._send_response(
                        response_id=response_id,
                        content=accumulated_text,
                        content_complete=False,  # Keep response OPEN
                    )

                # Spawn another background task for recursive tools
                updated_transcript = list(transcript)
                updated_transcript.append({"role": "agent", "content": accumulated_text})

                task = asyncio.create_task(
                    self._execute_tools_background(
                        response_id=response_id,
                        transcript=updated_transcript,
                        tool_calls=new_tool_calls,
                        assistant_text=accumulated_text,
                    )
                )
                self._pending_tool_execution = PendingToolExecution(
                    response_id=response_id,
                    transcript=updated_transcript,
                    tool_calls=new_tool_calls,
                    assistant_text=accumulated_text,
                    task=task,
                )
                return

        # Mark response complete
        # Check if Claude generated meaningful text (not just whitespace/punctuation)
        meaningful_text = accumulated_text.strip() if accumulated_text else ""
        has_meaningful_content = len(meaningful_text) > 10  # At least a short sentence

        self.logger.info(
            "tool_continuation_complete",
            accumulated_text_length=len(accumulated_text),
            meaningful_text_length=len(meaningful_text),
            has_meaningful_content=has_meaningful_content,
            first_50_chars=meaningful_text[:50] if meaningful_text else "(empty)",
        )

        # If Claude didn't generate meaningful text, send a fallback confirmation
        # This ensures we ALWAYS speak the confirmation before ending the turn
        if not has_meaningful_content:
            self.logger.info("sending_fallback_confirmation_after_tools")
            fallback = "Your appointment has been booked and you'll receive a text confirmation shortly. Is there anything else I can help you with?"
            await self._send_response(
                response_id=response_id,
                content=fallback,
                content_complete=True,
            )
        else:
            self.logger.info("claude_generated_confirmation", text=meaningful_text[:100])
            await self._send_response(
                response_id=response_id,
                content="",
                content_complete=True,
            )

    async def _handle_special_action_from_queue(self, item: dict[str, Any]) -> None:
        """Handle special actions (end_call, transfer_call) from queue.

        Args:
            item: Queued special action item
        """
        response_id = item["response_id"]
        action = item["action"]
        message = item.get("message", "")

        if action == "end_call":
            await self._send_response(
                response_id=response_id,
                content=message,
                content_complete=True,
                end_call=True,
            )
        elif action == "transfer_call":
            await self._send_response(
                response_id=response_id,
                content=message,
                content_complete=True,
                transfer_number=item.get("transfer_number"),
            )

    async def _send_error_response(self, response_id: int) -> None:
        """Send error response when tool execution fails.

        Args:
            response_id: Retell response ID
        """
        await self._send_response(
            response_id=response_id,
            content="I apologize, I encountered an issue. How else can I help?",
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

            # NOTE: We do NOT notify Retell about tool execution
            # Retell's Custom LLM protocol doesn't support tool_call_invocation messages
            # Tool execution is invisible to Retell - we just execute and continue

            # DEDUPLICATION: Prevent double SMS sends in same session
            if tool_name in ("telnyx_send_sms", "twilio_send_sms"):
                to_number = arguments.get("to", "")
                if to_number in self._sent_sms_numbers:
                    print(f"[SMS DEDUP] Blocked duplicate to {to_number}", flush=True)
                    self.logger.warning(
                        "duplicate_sms_blocked",
                        tool_name=tool_name,
                        to_number=to_number,
                    )
                    result = {
                        "success": True,
                        "message": f"SMS already sent to {to_number} in this session (duplicate blocked)",
                        "deduplicated": True,
                    }
                    tool_results.append(
                        format_tool_result_for_claude(
                            tool_use_id=tool_use_id,
                            result=result,
                            is_error=False,
                        )
                    )
                    continue  # Skip to next tool call

            # DEDUPLICATION: Only ONE booking per call - block all subsequent attempts
            if tool_name == "google_calendar_create_event":
                if self._booking_completed:
                    self.logger.warning(
                        "duplicate_booking_blocked",
                        tool_name=tool_name,
                        reason="booking_already_completed_this_session",
                    )
                    print("[CALENDAR DEDUP] Blocked - already booked this call!", flush=True)
                    result = {
                        "success": True,
                        "message": "Appointment already booked in this call. No additional booking needed.",
                        "deduplicated": True,
                    }
                    tool_results.append(
                        format_tool_result_for_claude(
                            tool_use_id=tool_use_id,
                            result=result,
                            is_error=False,
                        )
                    )
                    continue  # Skip to next tool call
                # Set flag BEFORE execution to prevent race condition
                self._booking_completed = True
                print("[CALENDAR] Blocking future bookings NOW (before execution)", flush=True)

            # Execute the tool
            # Debug print for SMS tools to diagnose sending issues
            if tool_name in ("telnyx_send_sms", "twilio_send_sms"):
                print(
                    f"[SMS] Executing {tool_name} to {arguments.get('to', 'unknown')}", flush=True
                )

            try:
                result = await self.tool_registry.execute_tool(tool_name, arguments)
                is_error = False

                # Track successful SMS sends for deduplication
                if tool_name in ("telnyx_send_sms", "twilio_send_sms"):
                    to_number = arguments.get("to", "")
                    if result.get("success"):
                        self._sent_sms_numbers.add(to_number)
                        print(f"[SMS] Sent successfully to {to_number}", flush=True)
                        self.logger.info("sms_sent_tracked", to_number=to_number)
                    else:
                        print(
                            f"[SMS ERROR] Failed to send to {to_number}: {result.get('error', 'unknown')}",
                            flush=True,
                        )

                # Note: Calendar booking tracking now happens BEFORE execution (race condition fix)

            except Exception as e:
                self.logger.exception("tool_execution_error", tool_name=tool_name, error=str(e))
                result = {"error": str(e)}
                is_error = True

            # NOTE: We do NOT send tool results to Retell
            # Retell's Custom LLM protocol doesn't support tool_call_result messages
            # Results are only sent to Claude for continuing the conversation

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
                        content=str(result.get("message", "Goodbye!")),
                        content_complete=True,
                        end_call=True,
                    )
                    return

                if result.get("action") == "transfer_call":
                    transfer_num = result.get("transfer_number")
                    await self._send_response(
                        response_id=response_id,
                        content=str(result.get("message", "Transferring you now.")),
                        content_complete=True,
                        transfer_number=str(transfer_num) if transfer_num else None,
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
        accumulated_text = ""
        new_tool_calls: list[dict[str, Any]] = []

        async for event in self.llm.generate_with_tool_results(
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
                delta = event.get("delta", "")
                accumulated_text += delta
                await self._send_response(
                    response_id=response_id,
                    content=delta,
                    content_complete=False,
                )

            elif event_type == "tool_use":
                # Claude wants to call another tool - collect it for recursive execution
                new_tool_call = event.get("tool_call", {})
                new_tool_calls.append(new_tool_call)
                self.logger.info(
                    "recursive_tool_call_detected",
                    tool_name=new_tool_call.get("name"),
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

        # If Claude called more tools, execute them recursively
        if new_tool_calls:
            # CRITICAL: ALWAYS mark response complete before executing more tools
            # If Claude didn't say anything, send a brief "thinking" message
            if not accumulated_text:
                accumulated_text = "Let me check on that..."
                await self._send_response(
                    response_id=response_id,
                    content=accumulated_text,
                    content_complete=False,
                )

            # Mark response complete - tells Retell we're done speaking
            await self._send_response(
                response_id=response_id,
                content="",
                content_complete=True,
            )

            # Build updated transcript with the current exchange
            updated_transcript: list[dict[str, Any]] = list(transcript)
            updated_transcript.append({"role": "agent", "content": accumulated_text})

            # Recursively execute the new tools
            await self._execute_tool_calls(
                response_id=response_id,
                transcript=updated_transcript,
                tool_calls=new_tool_calls,
                assistant_text=accumulated_text,
            )
            return

        # Mark response complete
        # If Claude didn't generate any text, send a fallback confirmation
        if not has_response:
            self.logger.info("sending_fallback_confirmation_sync")
            await self._send_response(
                response_id=response_id,
                content="Your appointment has been booked and you'll receive a text confirmation shortly. Is there anything else I can help you with?",
                content_complete=True,
            )
        else:
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
        # Track accumulated text for goodbye detection (streaming comes in chunks)
        if content:
            self._current_turn_text += content

        # If we've already said goodbye, ALWAYS end the call on any content_complete
        if self._said_goodbye and content_complete:
            end_call = True
            print("[END CALL] Forcing end_call - goodbye already said", flush=True)

        # Auto-detect goodbye phrases and set end_call=True when turn completes
        # This ensures the call ends when the agent says goodbye
        elif content_complete:
            # Check accumulated text from this turn for goodbye phrases
            if self._is_goodbye_message(self._current_turn_text):
                self._said_goodbye = True
                end_call = True
                print(
                    f"[GOODBYE DETECTED] Auto-ending call after: {self._current_turn_text[:60]}...",
                    flush=True,
                )
                self.logger.info(
                    "auto_end_call_goodbye_detected", content_preview=self._current_turn_text[:50]
                )

        # Reset accumulated text for next turn when complete
        if content_complete:
            self._current_turn_text = ""

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

        Raises:
            Exception: Re-raised to signal connection is dead
        """
        # Don't send if shutdown is in progress (connection already closed)
        if self._shutdown.is_set():
            self.logger.debug("skipping_send_shutdown", data_type=data.get("response_type"))
            return

        try:
            await self.websocket.send_text(json.dumps(data))
            # Update activity time to prevent redundant keepalives
            self._last_activity_time = asyncio.get_event_loop().time()
        except Exception as e:
            # Mark shutdown to prevent further send attempts
            self._shutdown.set()
            print(f"[WEBSOCKET ERROR] Send failed: {type(e).__name__}: {e}", flush=True)
            # Don't raise - just log and return, connection is dead
