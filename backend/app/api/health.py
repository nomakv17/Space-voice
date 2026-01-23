"""Health check endpoints."""

import logging

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
