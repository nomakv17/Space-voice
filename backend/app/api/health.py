"""Health check endpoints."""

import logging
from typing import Any

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.redis import get_redis
from app.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


@router.get("/health/db")
async def health_check_db(response: Response, db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    """Database health check endpoint."""
    try:
        result = await db.execute(text("SELECT 1"))
        result.scalar()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.exception("Database health check failed")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "unhealthy", "database": str(e)}


@router.get("/health/redis")
async def health_check_redis(response: Response) -> dict[str, str]:
    """Redis health check endpoint."""
    try:
        redis = await get_redis()
        await redis.ping()
        return {"status": "healthy", "redis": "connected"}
    except Exception as e:
        logger.exception("Redis health check failed")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "unhealthy", "redis": str(e)}


@router.get("/test-llm")
async def test_llm(response: Response) -> dict[str, str]:
    """Test LLM API connectivity (Claude or OpenAI).

    This endpoint verifies the configured LLM provider is working.
    Useful for debugging voice agent issues.
    """
    result: dict[str, str] = {"llm_provider": settings.LLM_PROVIDER}

    try:
        if settings.LLM_PROVIDER.lower() == "claude":
            from anthropic import Anthropic

            if not settings.ANTHROPIC_API_KEY:
                response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
                return {"status": "error", "error": "ANTHROPIC_API_KEY not set"}

            anthropic_client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
            claude_response = anthropic_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=20,
                messages=[
                    {
                        "role": "user",
                        "content": "Say 'Hello, I am working!' in exactly those words.",
                    }
                ],
            )
            result["status"] = "ok"
            # Get text from the first text block
            content_block = claude_response.content[0]
            result["response"] = getattr(content_block, "text", str(content_block))
        else:
            from openai import OpenAI

            if not settings.OPENAI_API_KEY:
                response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
                return {"status": "error", "error": "OPENAI_API_KEY not set"}

            openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
            openai_response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                max_tokens=20,
                messages=[
                    {
                        "role": "user",
                        "content": "Say 'Hello, I am working!' in exactly those words.",
                    }
                ],
            )
            result["status"] = "ok"
            result["response"] = openai_response.choices[0].message.content or ""

        return result

    except Exception as e:
        logger.exception("LLM test failed")
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {"status": "error", "error": f"{type(e).__name__}: {e!s}"}


@router.get("/test-voice-claude")
async def test_voice_claude(response: Response) -> dict[str, Any]:
    """Test Claude with EXACT voice call parameters.

    Simulates what happens when a user speaks during a voice call.
    Returns detailed error info if Claude rejects the request.
    """
    from anthropic import AsyncAnthropic

    result: dict[str, Any] = {"test": "voice_claude_simulation"}

    if not settings.ANTHROPIC_API_KEY:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {"status": "error", "error": "ANTHROPIC_API_KEY not set"}

    # Simulate EXACT voice call scenario
    system_prompt = """You are a professional voice AI assistant currently on a phone call.

CRITICAL VOICE RULES:
1. Keep responses SHORT - 1-2 sentences maximum per turn
2. Speak naturally as if on a phone call - no lists, bullets, or markdown
3. Never say "I cannot" or "I'm unable" - find helpful alternatives

CONTEXT:
- Current time: Friday, January 23, 2026 at 10:05 AM (CST)
- Language: en-US

YOUR INSTRUCTIONS:
You are Sarah, a friendly receptionist for Jobber HVAC. Help customers with HVAC issues."""

    # Exact message format from voice call
    messages = [
        {"role": "user", "content": "[Call connected]"},
        {
            "role": "assistant",
            "content": "Hello, thank you for calling Jobber HVAC. My name is Sarah. How can I help you today?",
        },
        {"role": "user", "content": "My cooling system isn't working."},
    ]

    # No tools in this test (matches real scenario where agent has no tools enabled)
    tools: list[dict[str, Any]] = []

    try:
        client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

        result["system_prompt_len"] = len(system_prompt)
        result["message_count"] = len(messages)
        result["tool_count"] = len(tools)

        # Build kwargs - only include tools if we have them (Claude rejects tools=None or tools=[])
        stream_kwargs: dict[str, Any] = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 1024,
            "system": system_prompt,
            "messages": messages,
            "temperature": 0.7,
        }
        if tools:
            stream_kwargs["tools"] = tools

        # Call Claude with streaming (like voice does)
        collected_text = ""
        async with client.messages.stream(**stream_kwargs) as stream:
            async for event in stream:
                if event.type == "content_block_delta":
                    if hasattr(event.delta, "text"):
                        collected_text += event.delta.text

        result["status"] = "ok"
        result["response"] = collected_text
        return result

    except Exception as e:
        # Capture FULL error details
        error_info: dict[str, Any] = {
            "status": "error",
            "error_type": type(e).__name__,
            "error_message": str(e),
        }

        # Extract Anthropic-specific error details
        if hasattr(e, "status_code"):
            error_info["status_code"] = e.status_code
        if hasattr(e, "body"):
            error_info["api_body"] = e.body
        if hasattr(e, "response"):
            try:
                resp = e.response
                error_info["response_status"] = resp.status_code
                error_info["response_text"] = resp.text[:500]
            except Exception:
                pass

        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return error_info


@router.post("/admin/enable-agent-tools/{agent_id}")
async def enable_agent_tools(
    agent_id: str,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Admin endpoint to enable tools on an agent.

    WARNING: This is a temporary admin endpoint. Remove after use.
    """
    from sqlalchemy import text

    try:
        # Check current state
        result = await db.execute(
            text("SELECT id, name, enabled_tools, enabled_tool_ids, user_id FROM agents WHERE id = :agent_id"),
            {"agent_id": agent_id},
        )
        row = result.fetchone()

        if not row:
            response.status_code = 404
            return {"error": f"Agent {agent_id} not found"}

        before_state = {
            "id": str(row[0]),
            "name": row[1],
            "enabled_tools": row[2],
            "enabled_tool_ids": row[3],
        }

        # Check integrations
        result = await db.execute(
            text("""
                SELECT integration_id, is_active, credentials IS NOT NULL as has_credentials
                FROM user_integrations
                WHERE user_id = :user_id AND is_active = true
            """),
            {"user_id": row[4]},
        )
        integrations = [
            {"id": r[0], "active": r[1], "has_creds": r[2]}
            for r in result.fetchall()
        ]

        # Update the agent with tools enabled
        import json

        enabled_tools = ["google-calendar", "telnyx-sms"]
        enabled_tool_ids = {
            "google-calendar": ["google_calendar_create_event", "google_calendar_check_availability"],
            "telnyx-sms": ["telnyx_send_sms"],
        }

        await db.execute(
            text("""
                UPDATE agents
                SET enabled_tools = CAST(:enabled_tools AS jsonb),
                    enabled_tool_ids = CAST(:enabled_tool_ids AS jsonb)
                WHERE id = :agent_id
            """),
            {
                "agent_id": agent_id,
                "enabled_tools": json.dumps(enabled_tools),
                "enabled_tool_ids": json.dumps(enabled_tool_ids),
            },
        )
        await db.commit()

        # Verify update
        result = await db.execute(
            text("SELECT enabled_tools, enabled_tool_ids FROM agents WHERE id = :agent_id"),
            {"agent_id": agent_id},
        )
        updated_row = result.fetchone()

        return {
            "status": "success",
            "agent_id": agent_id,
            "before": before_state,
            "after": {
                "enabled_tools": updated_row[0] if updated_row else None,
                "enabled_tool_ids": updated_row[1] if updated_row else None,
            },
            "integrations_available": integrations,
            "message": "Agent tools enabled. Make a test call to verify.",
        }

    except Exception as e:
        logger.exception("Failed to enable agent tools")
        response.status_code = 500
        return {"error": f"{type(e).__name__}: {e}"}
