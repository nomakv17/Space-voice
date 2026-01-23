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

    # Include tools to match real scenario (empty list like in logs)
    tools: list[dict[str, Any]] = []

    try:
        client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

        result["system_prompt_len"] = len(system_prompt)
        result["message_count"] = len(messages)
        result["tool_count"] = len(tools)

        # Call Claude with streaming (like voice does)
        collected_text = ""
        async with client.messages.stream(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=system_prompt,
            messages=messages,  # type: ignore[arg-type]
            tools=tools if tools else None,  # type: ignore[arg-type]
            temperature=0.7,
        ) as stream:
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
