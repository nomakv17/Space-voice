"""Public demo API for landing page demo calls.

This module provides unauthenticated endpoints for:
- Demo call initiation (visitors can request a call without signing up)
- Rate limited to prevent abuse (3 calls per IP per hour)
"""

import re
import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.limiter import limiter
from app.db.session import get_db
from app.models.agent import Agent
from app.models.call_record import CallDirection, CallRecord, CallStatus
from app.models.workspace import AgentWorkspace
from app.services.telephony.telnyx_service import TelnyxService

router = APIRouter(prefix="/api/v1/public", tags=["public-demo"])
logger = structlog.get_logger()

# Phone number validation regex (E.164 format)
E164_PATTERN = re.compile(r"^\+?[1-9]\d{6,14}$")


class DemoCallRequest(BaseModel):
    """Request to initiate a demo call."""

    phone_number: str

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        """Validate and normalize phone number to E.164 format."""
        # Remove spaces, dashes, parentheses
        cleaned = re.sub(r"[\s\-\(\)]", "", v)

        # Add + prefix if not present
        if not cleaned.startswith("+"):
            # Assume US number if no country code
            if len(cleaned) == 10:
                cleaned = "+1" + cleaned
            elif len(cleaned) == 11 and cleaned.startswith("1"):
                cleaned = "+" + cleaned
            else:
                cleaned = "+" + cleaned

        # Validate format
        if not E164_PATTERN.match(cleaned):
            raise ValueError(
                "Invalid phone number format. Please use format: +1XXXXXXXXXX"
            )

        return cleaned


class DemoCallResponse(BaseModel):
    """Response for demo call request."""

    success: bool
    message: str
    call_id: str | None = None


async def get_demo_agent(db: AsyncSession) -> Agent | None:
    """Get the configured demo agent."""
    if not settings.DEMO_AGENT_ID:
        return None

    try:
        agent_uuid = uuid.UUID(settings.DEMO_AGENT_ID)
    except ValueError:
        logger.error("Invalid DEMO_AGENT_ID format", agent_id=settings.DEMO_AGENT_ID)
        return None

    result = await db.execute(select(Agent).where(Agent.id == agent_uuid))
    return result.scalar_one_or_none()


async def get_agent_workspace_id(agent_id: uuid.UUID, db: AsyncSession) -> uuid.UUID | None:
    """Get the workspace ID for an agent."""
    result = await db.execute(
        select(AgentWorkspace.workspace_id).where(AgentWorkspace.agent_id == agent_id).limit(1)
    )
    return result.scalar_one_or_none()


@router.post("/demo-call", response_model=DemoCallResponse)
@limiter.limit("3/hour")  # Strict rate limit: 3 demo calls per IP per hour
async def initiate_demo_call(
    request: Request,
    call_request: DemoCallRequest,
    db: AsyncSession = Depends(get_db),
) -> DemoCallResponse:
    """Initiate a demo call to a visitor's phone number.

    This is a public endpoint that allows landing page visitors to
    experience SpaceVoice without signing up. The call uses a
    pre-configured demo agent.

    Rate limited to 3 calls per IP address per hour to prevent abuse.
    """
    log = logger.bind(
        endpoint="demo_call",
        phone_number=call_request.phone_number[:6] + "****",  # Partial logging for privacy
    )
    log.info("demo_call_requested")

    # Check if demo is configured
    if not settings.DEMO_AGENT_ID:
        log.warning("demo_not_configured", reason="DEMO_AGENT_ID not set")
        raise HTTPException(
            status_code=503,
            detail="Demo calls are not currently available. Please contact us directly.",
        )

    if not settings.DEMO_FROM_NUMBER:
        log.warning("demo_not_configured", reason="DEMO_FROM_NUMBER not set")
        raise HTTPException(
            status_code=503,
            detail="Demo calls are not currently available. Please contact us directly.",
        )

    if not settings.TELNYX_API_KEY:
        log.warning("demo_not_configured", reason="TELNYX_API_KEY not set")
        raise HTTPException(
            status_code=503,
            detail="Demo calls are not currently available. Please contact us directly.",
        )

    # Get demo agent
    agent = await get_demo_agent(db)
    if not agent:
        log.error("demo_agent_not_found", agent_id=settings.DEMO_AGENT_ID)
        raise HTTPException(
            status_code=503,
            detail="Demo agent is not configured. Please contact us directly.",
        )

    # Initialize Telnyx service with system credentials
    telnyx_service = TelnyxService(
        api_key=settings.TELNYX_API_KEY,
        public_key=settings.TELNYX_PUBLIC_KEY,
    )

    # Build webhook URL for when the call is answered
    public_url = settings.PUBLIC_URL
    if not public_url:
        log.error("PUBLIC_URL not configured for demo calls")
        raise HTTPException(
            status_code=503,
            detail="Demo calls are not currently available. Please try again later.",
        )

    webhook_url = f"{public_url}/webhooks/telnyx/answer?agent_id={agent.id}"

    try:
        # Initiate the outbound call
        call_info = await telnyx_service.initiate_call(
            to_number=call_request.phone_number,
            from_number=settings.DEMO_FROM_NUMBER,
            webhook_url=webhook_url,
            agent_id=str(agent.id),
        )

        log.info(
            "demo_call_initiated",
            call_id=call_info.call_id,
            to_number=call_request.phone_number[:6] + "****",
        )

        # Get workspace ID for the agent
        workspace_id = await get_agent_workspace_id(agent.id, db)

        # Create call record for tracking
        call_record = CallRecord(
            user_id=agent.user_id,
            workspace_id=workspace_id,
            provider="telnyx",
            provider_call_id=call_info.call_id,
            agent_id=agent.id,
            direction=CallDirection.OUTBOUND.value,
            status=CallStatus.INITIATED.value,
            from_number=settings.DEMO_FROM_NUMBER,
            to_number=call_request.phone_number,
            metadata={"source": "landing_page_demo"},
        )
        db.add(call_record)
        await db.commit()

        return DemoCallResponse(
            success=True,
            message="Calling you now! Please answer your phone.",
            call_id=call_info.call_id,
        )

    except Exception as e:
        log.exception("demo_call_failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to initiate demo call. Please try again or contact us directly.",
        ) from e


@router.get("/demo-status")
async def get_demo_status() -> dict[str, bool]:
    """Check if demo calls are available.

    Returns whether all required configuration is in place for demo calls.
    """
    is_available = all([
        settings.DEMO_AGENT_ID,
        settings.DEMO_FROM_NUMBER,
        settings.TELNYX_API_KEY,
        settings.PUBLIC_URL,
    ])

    return {
        "demo_available": is_available,
    }
