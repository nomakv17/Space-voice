"""Retell Custom LLM WebSocket endpoint.

This endpoint receives WebSocket connections from Retell AI and routes
conversation turns to Claude for response generation.

When a Retell agent is configured with a Custom LLM, Retell will:
1. Connect to this WebSocket when a call starts
2. Send conversation transcripts as they happen
3. Expect streaming text responses for TTS synthesis

Reference: https://docs.retellai.com/api-references/llm-websocket
"""

import uuid
from typing import Any

import structlog
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.integrations import get_workspace_integrations
from app.core.config import settings
from app.db.session import get_db
from app.models.agent import Agent
from app.models.workspace import AgentWorkspace
from app.services.retell.claude_adapter import ClaudeAdapter
from app.services.retell.retell_llm_server import RetellLLMServer
from app.services.tools.registry import ToolRegistry

router = APIRouter(prefix="/ws/retell", tags=["retell-ws"])
logger = structlog.get_logger()


async def get_agent_workspace_id(agent_id: uuid.UUID, db: AsyncSession) -> uuid.UUID | None:
    """Get the primary workspace ID for an agent.

    Args:
        agent_id: Agent UUID
        db: Database session

    Returns:
        Workspace UUID or None if no workspace assigned
    """
    result = await db.execute(
        select(AgentWorkspace.workspace_id)
        .where(AgentWorkspace.agent_id == agent_id)
        .limit(1)
    )
    return result.scalar_one_or_none()


def build_retell_system_prompt(agent: Agent, timezone: str = "UTC") -> str:
    """Build system prompt optimized for Retell + Claude voice conversations.

    Wraps the agent's custom prompt with voice-specific rules that help
    Claude generate natural, conversational responses.

    Args:
        agent: Agent model with system_prompt
        timezone: Timezone for time context

    Returns:
        Complete voice-optimized system prompt
    """
    from datetime import datetime

    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo(timezone)
        now = datetime.now(tz)
        current_time = now.strftime("%A, %B %d, %Y at %I:%M %p")
    except Exception:
        current_time = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")

    base_prompt = agent.system_prompt or "You are a helpful voice assistant."

    return f"""You are a professional voice AI assistant currently on a phone call.

CRITICAL VOICE CONVERSATION RULES:
1. Keep responses SHORT and conversational (1-2 sentences max per turn)
2. Speak naturally as if on a phone call - no markdown, lists, or formatting
3. Never say "I cannot" or "I'm unable" - always offer helpful alternatives
4. Use natural filler phrases: "Let me check that for you...", "One moment...", "Alright..."
5. Confirm understanding before taking actions
6. Speak numbers naturally (say "five five five" not "555")
7. When using tools, explain what you're doing before and summarize results after

CONTEXT:
- Current time: {current_time} ({timezone})
- Language: {agent.language or 'en-US'}

YOUR ROLE AND INSTRUCTIONS:
{base_prompt}

IMPORTANT: You are in a voice conversation. Keep all responses brief and natural."""


@router.websocket("/llm/{agent_id}")
async def retell_llm_websocket(
    websocket: WebSocket,
    agent_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """WebSocket endpoint for Retell Custom LLM integration.

    This endpoint receives conversation requests from Retell and generates
    responses using Claude 4.5 Sonnet with tool calling support.

    The flow:
    1. Retell connects when a call starts
    2. We send configuration (auto_reconnect, call_details)
    3. Retell sends call_details with metadata
    4. For each user turn, Retell sends response_required
    5. We stream Claude's response back for TTS
    6. If tools are called, we execute them and continue

    Args:
        websocket: FastAPI WebSocket connection
        agent_id: UUID of the agent to use
        db: Database session
    """
    session_id = str(uuid.uuid4())
    log = logger.bind(
        endpoint="retell_llm",
        agent_id=agent_id,
        session_id=session_id,
    )

    # Accept the WebSocket connection
    await websocket.accept()
    log.info("retell_llm_websocket_connected")

    try:
        # Validate agent_id format
        try:
            agent_uuid = uuid.UUID(agent_id)
        except ValueError:
            log.warning("invalid_agent_id_format")
            await websocket.close(code=4000, reason="Invalid agent ID format")
            return

        # Load agent from database
        result = await db.execute(
            select(Agent).where(Agent.id == agent_uuid)
        )
        agent = result.scalar_one_or_none()

        if not agent:
            log.error("agent_not_found")
            await websocket.close(code=4004, reason="Agent not found")
            return

        if not agent.is_active:
            log.error("agent_not_active")
            await websocket.close(code=4003, reason="Agent is not active")
            return

        # Verify Anthropic API key is configured
        if not settings.ANTHROPIC_API_KEY:
            log.error("anthropic_api_key_not_configured")
            await websocket.close(code=5000, reason="Claude API not configured")
            return

        log = log.bind(
            agent_name=agent.name,
            user_id=agent.user_id,
        )

        # Get workspace for this agent
        workspace_id = await get_agent_workspace_id(agent.id, db)
        log = log.bind(workspace_id=str(workspace_id) if workspace_id else None)

        # Load workspace integrations for tools
        # Note: Agent.user_id is int, but UserIntegration uses UUID format
        # Convert int user_id to UUID for compatibility
        user_id_uuid = uuid.UUID(int=agent.user_id)
        integrations: dict[str, dict[str, Any]] = {}
        if workspace_id:
            integrations = await get_workspace_integrations(user_id_uuid, workspace_id, db)

        # Initialize Claude adapter
        claude_adapter = ClaudeAdapter(
            api_key=settings.ANTHROPIC_API_KEY,
            timeout=settings.ANTHROPIC_TIMEOUT,
        )

        # Initialize tool registry
        tool_registry = ToolRegistry(
            db=db,
            user_id=agent.user_id,
            integrations=integrations,
            workspace_id=workspace_id,
        )

        # Build voice-optimized system prompt
        system_prompt = build_retell_system_prompt(agent)

        # Get enabled tools from agent config
        enabled_tools = agent.enabled_tools or []
        enabled_tool_ids = agent.enabled_tool_ids

        log.info(
            "initializing_llm_server",
            enabled_tools=enabled_tools,
            tool_count=len(tool_registry.get_all_tool_definitions(enabled_tools, enabled_tool_ids)),
        )

        # Create and run the LLM server
        llm_server = RetellLLMServer(
            websocket=websocket,
            claude_adapter=claude_adapter,
            tool_registry=tool_registry,
            system_prompt=system_prompt,
            enabled_tools=enabled_tools,
            enabled_tool_ids=enabled_tool_ids,
            agent_config={
                "temperature": agent.temperature or 0.7,
                "max_tokens": agent.max_tokens or 1024,
                "language": agent.language or "en-US",
            },
        )

        # Handle the connection (runs until disconnect)
        await llm_server.handle_connection()

    except WebSocketDisconnect:
        log.info("retell_llm_websocket_disconnected")
    except Exception as e:
        log.exception("retell_llm_websocket_error", error=str(e))
    finally:
        log.info("retell_llm_websocket_closed")


@router.websocket("/llm/test")
async def retell_llm_test_websocket(
    websocket: WebSocket,
) -> None:
    """Test endpoint for Retell Custom LLM WebSocket.

    Use this endpoint to test connectivity without requiring an agent.
    It echoes back messages and responds to ping_pong.

    This is useful for:
    - Verifying WebSocket connectivity
    - Testing from Retell dashboard
    - Development/debugging
    """
    session_id = str(uuid.uuid4())
    log = logger.bind(endpoint="retell_llm_test", session_id=session_id)

    await websocket.accept()
    log.info("test_websocket_connected")

    try:
        # Send config
        import json
        await websocket.send_text(json.dumps({
            "response_type": "config",
            "config": {
                "auto_reconnect": True,
                "call_details": True,
            },
        }))

        async for message in websocket.iter_text():
            data = json.loads(message)
            interaction_type = data.get("interaction_type")

            if interaction_type == "ping_pong":
                await websocket.send_text(json.dumps({
                    "response_type": "ping_pong",
                    "timestamp": data.get("timestamp"),
                }))

            elif interaction_type == "response_required":
                response_id = data.get("response_id", 0)
                # Send a test response
                await websocket.send_text(json.dumps({
                    "response_type": "response",
                    "response_id": response_id,
                    "content": "This is a test response from the SpaceVoice Custom LLM endpoint. ",
                    "content_complete": False,
                }))
                await websocket.send_text(json.dumps({
                    "response_type": "response",
                    "response_id": response_id,
                    "content": "The connection is working correctly.",
                    "content_complete": True,
                }))

            log.debug("test_message_handled", type=interaction_type)

    except WebSocketDisconnect:
        log.info("test_websocket_disconnected")
    except Exception as e:
        log.exception("test_websocket_error", error=str(e))
