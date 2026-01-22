"""Retell AI webhook handlers.

This module handles webhooks from Retell AI for call lifecycle events:
- call_started: When a call begins (create call record)
- call_ended: When a call ends (save transcript, update metrics)
- call_analyzed: Post-call analysis results
- inbound: Inbound call routing (determine which agent handles the call)

Retell sends webhooks to these endpoints when events occur in their system.
We use these to maintain call history and enable outcome-based reporting.

Reference: https://docs.retellai.com/features/post-call-webhook
"""

import hashlib
import hmac
import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.models.agent import Agent
from app.models.call_record import CallDirection, CallRecord, CallStatus
from app.models.contact import Contact
from app.models.phone_number import PhoneNumber

router = APIRouter(prefix="/webhooks/retell", tags=["retell-webhooks"])
logger = structlog.get_logger()


# =============================================================================
# Pydantic Models for Retell Webhooks
# =============================================================================


class RetellCallData(BaseModel):
    """Retell call data from webhooks."""

    call_id: str
    agent_id: str | None = None
    call_status: str | None = None
    start_timestamp: int | None = None  # Unix timestamp ms
    end_timestamp: int | None = None  # Unix timestamp ms
    duration_ms: int | None = None
    from_number: str | None = None
    to_number: str | None = None
    direction: str | None = None  # "inbound" or "outbound"
    transcript: str | None = None
    transcript_object: list[dict[str, Any]] | None = None
    recording_url: str | None = None
    public_log_url: str | None = None
    disconnection_reason: str | None = None
    call_analysis: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None


class RetellWebhookPayload(BaseModel):
    """Retell webhook payload."""

    event: str  # "call_started", "call_ended", "call_analyzed"
    call: RetellCallData


class InboundCallRequest(BaseModel):
    """Inbound call request from Retell."""

    from_number: str
    to_number: str
    call_id: str | None = None
    metadata: dict[str, Any] | None = None


class InboundCallResponse(BaseModel):
    """Response for inbound call routing."""

    agent_id: str
    metadata: dict[str, Any] | None = None


# =============================================================================
# Webhook Verification
# =============================================================================


async def verify_retell_signature(request: Request) -> None:
    """Verify Retell webhook signature.

    Retell signs webhooks using HMAC-SHA256 with your API key.
    The signature is in the x-retell-signature header.

    Args:
        request: FastAPI request object

    Raises:
        HTTPException: If signature verification fails
    """
    # Require API key configuration - fail secure
    if not settings.RETELL_API_KEY:
        logger.error("retell_api_key_not_configured")
        raise HTTPException(
            status_code=500,
            detail="Retell API key not configured",
        )

    signature = request.headers.get("x-retell-signature")
    if not signature:
        logger.warning("retell_webhook_no_signature")
        raise HTTPException(
            status_code=401,
            detail="Missing webhook signature",
        )

    body = await request.body()

    expected = hmac.new(
        settings.RETELL_API_KEY.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(signature, expected):
        logger.warning("retell_webhook_signature_mismatch")
        raise HTTPException(
            status_code=401,
            detail="Invalid webhook signature",
        )


# =============================================================================
# Helper Functions
# =============================================================================


def convert_retell_status(status: str | None) -> CallStatus:
    """Convert Retell call status to our CallStatus enum.

    Args:
        status: Retell call status string

    Returns:
        CallStatus enum value
    """
    status_map = {
        "registered": CallStatus.INITIATED,
        "ongoing": CallStatus.IN_PROGRESS,
        "ended": CallStatus.COMPLETED,
        "error": CallStatus.FAILED,
    }
    return status_map.get(status or "", CallStatus.INITIATED)


def convert_retell_direction(direction: str | None) -> CallDirection:
    """Convert Retell direction to our CallDirection enum.

    Args:
        direction: Retell direction string

    Returns:
        CallDirection enum value
    """
    if direction == "outbound":
        return CallDirection.OUTBOUND
    return CallDirection.INBOUND


def format_transcript(transcript_object: list[dict[str, Any]] | None) -> str:
    """Format Retell transcript object to readable text.

    Args:
        transcript_object: List of transcript entries from Retell

    Returns:
        Formatted transcript string
    """
    if not transcript_object:
        return ""

    lines = []
    for entry in transcript_object:
        role = entry.get("role", "unknown")
        content = entry.get("content", "")
        # Capitalize role for readability
        speaker = "Agent" if role == "agent" else "Customer"
        lines.append(f"{speaker}: {content}")

    return "\n".join(lines)


async def get_or_create_contact(
    db: AsyncSession,
    phone_number: str,
    user_id: int,
    log: structlog.BoundLogger,
) -> Contact | None:
    """Find or create a CRM contact from a phone number.

    When someone calls, we automatically create a contact record if one
    doesn't exist. This enables call history tracking per contact.

    Args:
        db: Database session
        phone_number: Caller's phone number (E.164 format)
        user_id: Owner user ID
        log: Logger instance

    Returns:
        Contact instance or None if creation fails
    """
    if not phone_number or not user_id:
        return None

    # Normalize phone number (remove spaces, ensure + prefix)
    normalized = phone_number.strip().replace(" ", "")
    if not normalized.startswith("+"):
        normalized = f"+{normalized}"

    # Check if contact already exists
    result = await db.execute(
        select(Contact).where(
            Contact.phone_number == normalized,
            Contact.user_id == user_id,
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        log.info("contact_found", contact_id=existing.id, phone=normalized)
        return existing

    # Create new contact from caller ID
    # Extract area code for a basic first name (E.164 format: +1AAANNNNNNN)
    min_phone_length = 5  # Minimum length to extract area code
    area_code = normalized[2:5] if len(normalized) > min_phone_length else "Unknown"
    contact = Contact(
        user_id=user_id,
        first_name=f"Caller ({area_code})",
        last_name=None,
        phone_number=normalized,
        status="new",
        tags="auto-created,inbound-call",
        notes=f"Auto-created from inbound call on {datetime.now(UTC).strftime('%Y-%m-%d %H:%M')} UTC",
    )

    db.add(contact)
    await db.flush()  # Get the ID without committing

    log.info("contact_created", contact_id=contact.id, phone=normalized)
    return contact


# =============================================================================
# Webhook Endpoints
# =============================================================================


@router.post("")
@router.post("/")
async def retell_unified_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Unified webhook endpoint for all Retell events.

    Retell sends all webhook events to a SINGLE URL. This endpoint
    receives all events and routes them to the appropriate handler
    based on the 'event' field in the payload.

    Configure this URL in Retell Dashboard:
    https://your-domain.com/webhooks/retell

    Args:
        request: FastAPI request
        db: Database session

    Returns:
        Acknowledgment response
    """
    await verify_retell_signature(request)

    body = await request.json()
    log = logger.bind(endpoint="retell_unified_webhook")

    event_type = body.get("event", "unknown")
    log.info("retell_webhook_received", event_type=event_type)

    # Route to appropriate handler based on event type
    if event_type == "call_started":
        return await _handle_call_started(body, db, log)
    if event_type == "call_ended":
        return await _handle_call_ended(body, db, log)
    if event_type == "call_analyzed":
        return await _handle_call_analyzed(body, db, log)
    log.warning("unknown_event_type", event_type=event_type)
    return {"status": "ignored", "event": event_type}


async def _handle_call_started(
    body: dict[str, Any],
    db: AsyncSession,
    log: structlog.BoundLogger,
) -> dict[str, str]:
    """Internal handler for call_started events."""
    try:
        payload = RetellWebhookPayload(**body)
        call = payload.call

        log = log.bind(
            call_id=call.call_id,
            agent_id=call.agent_id,
            direction=call.direction,
        )
        log.info("processing_call_started")

        # Look up our internal agent by Retell agent_id
        agent = None
        user_id = None

        if call.agent_id:
            result = await db.execute(select(Agent).where(Agent.retell_agent_id == call.agent_id))
            agent = result.scalar_one_or_none()

            if not agent and call.metadata and call.metadata.get("internal_agent_id"):
                agent_id_str = call.metadata.get("internal_agent_id")
                try:
                    result = await db.execute(
                        select(Agent).where(Agent.id == uuid.UUID(agent_id_str))
                    )
                    agent = result.scalar_one_or_none()
                except (ValueError, TypeError):
                    pass

            if agent:
                user_id = agent.user_id

        # Auto-create contact from caller ID for inbound calls
        contact = None
        if user_id and call.from_number and call.direction == "inbound":
            contact = await get_or_create_contact(
                db=db,
                phone_number=call.from_number,
                user_id=user_id,
                log=log,
            )

        # Create call record
        call_record = CallRecord(
            user_id=user_id,
            provider="retell",
            provider_call_id=call.call_id,
            agent_id=agent.id if agent else None,
            contact_id=contact.id if contact else None,
            from_number=call.from_number or "",
            to_number=call.to_number or "",
            direction=convert_retell_direction(call.direction),
            status=CallStatus.IN_PROGRESS,
            started_at=datetime.fromtimestamp(call.start_timestamp / 1000, tz=UTC)
            if call.start_timestamp
            else datetime.now(UTC),
        )

        db.add(call_record)
        await db.commit()

        log.info(
            "call_record_created",
            record_id=str(call_record.id),
            contact_id=contact.id if contact else None,
        )
        return {"status": "received", "call_record_id": str(call_record.id)}

    except Exception as e:
        log.exception("call_started_error", error=str(e))
        return {"status": "error", "message": str(e)}


async def _handle_call_ended(
    body: dict[str, Any],
    db: AsyncSession,
    log: structlog.BoundLogger,
) -> dict[str, str]:
    """Internal handler for call_ended events."""
    try:
        payload = RetellWebhookPayload(**body)
        call = payload.call

        log = log.bind(
            call_id=call.call_id,
            duration_ms=call.duration_ms,
            disconnection_reason=call.disconnection_reason,
        )
        log.info("processing_call_ended")

        # Find existing call record
        result = await db.execute(
            select(CallRecord).where(CallRecord.provider_call_id == call.call_id)
        )
        call_record = result.scalar_one_or_none()

        # If no call record exists (call_started wasn't received), create one now
        if not call_record:
            log.warning("call_record_not_found_creating", call_id=call.call_id)

            # Look up agent
            agent: Agent | None = None
            user_id: int | None = None
            if call.agent_id:
                agent_result = await db.execute(
                    select(Agent).where(Agent.retell_agent_id == call.agent_id)
                )
                agent = agent_result.scalar_one_or_none()
                if agent:
                    user_id = agent.user_id

            # Auto-create contact
            contact = None
            if user_id and call.from_number and call.direction == "inbound":
                contact = await get_or_create_contact(
                    db=db,
                    phone_number=call.from_number,
                    user_id=user_id,
                    log=log,
                )

            call_record = CallRecord(
                user_id=user_id,
                provider="retell",
                provider_call_id=call.call_id,
                agent_id=agent.id if agent else None,
                contact_id=contact.id if contact else None,
                from_number=call.from_number or "",
                to_number=call.to_number or "",
                direction=convert_retell_direction(call.direction),
                status=CallStatus.COMPLETED,
                started_at=datetime.fromtimestamp(call.start_timestamp / 1000, tz=UTC)
                if call.start_timestamp
                else datetime.now(UTC),
            )
            db.add(call_record)

        # Update call record with end data
        call_record.status = CallStatus.COMPLETED
        call_record.ended_at = (
            datetime.fromtimestamp(call.end_timestamp / 1000, tz=UTC)
            if call.end_timestamp
            else datetime.now(UTC)
        )
        call_record.duration_seconds = (call.duration_ms or 0) // 1000

        # Save transcript
        if call.transcript:
            call_record.transcript = call.transcript
        elif call.transcript_object:
            call_record.transcript = format_transcript(call.transcript_object)

        # Save recording URL if available
        if call.recording_url:
            call_record.recording_url = call.recording_url

        await db.commit()

        # Update agent metrics
        if call_record.agent_id:
            await db.execute(
                update(Agent)
                .where(Agent.id == call_record.agent_id)
                .values(
                    total_calls=Agent.total_calls + 1,
                    total_duration_seconds=Agent.total_duration_seconds
                    + (call_record.duration_seconds or 0),
                    last_call_at=datetime.now(UTC),
                )
            )
            await db.commit()

        log.info(
            "call_record_updated",
            record_id=str(call_record.id),
            duration=call_record.duration_seconds,
            has_transcript=bool(call_record.transcript),
        )
        return {"status": "received"}

    except Exception as e:
        log.exception("call_ended_error", error=str(e))
        return {"status": "error", "message": str(e)}


async def _handle_call_analyzed(
    body: dict[str, Any],
    db: AsyncSession,
    log: structlog.BoundLogger,
) -> dict[str, Any]:
    """Internal handler for call_analyzed events."""
    try:
        payload = RetellWebhookPayload(**body)
        call = payload.call

        log = log.bind(call_id=call.call_id)
        log.info("processing_call_analyzed")

        if not call.call_analysis:
            log.info("no_analysis_data")
            return {"status": "received", "message": "No analysis data"}

        # Find call record
        result = await db.execute(
            select(CallRecord).where(CallRecord.provider_call_id == call.call_id)
        )
        call_record = result.scalar_one_or_none()

        if call_record:
            analysis = call.call_analysis
            log.info(
                "call_analysis_received",
                record_id=str(call_record.id),
                sentiment=analysis.get("user_sentiment"),
                has_summary=bool(analysis.get("call_summary")),
            )
            return {
                "status": "received",
                "sentiment": analysis.get("user_sentiment"),
                "has_summary": bool(analysis.get("call_summary")),
            }

        log.warning("call_record_not_found_for_analysis", call_id=call.call_id)
        return {"status": "received", "message": "Call record not found"}

    except Exception as e:
        log.exception("call_analyzed_error", error=str(e))
        return {"status": "error", "message": str(e)}


@router.post("/call-started")
async def retell_call_started(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Handle call started webhook from Retell.

    Creates a call record when a new call begins.

    Args:
        request: FastAPI request
        db: Database session

    Returns:
        Acknowledgment response
    """
    await verify_retell_signature(request)

    body = await request.json()
    log = logger.bind(endpoint="retell_call_started")

    try:
        payload = RetellWebhookPayload(**body)
        call = payload.call

        log = log.bind(
            call_id=call.call_id,
            agent_id=call.agent_id,
            direction=call.direction,
        )
        log.info("retell_call_started_received")

        # Look up our internal agent by Retell agent_id
        # For now, we store retell agent_id in metadata
        # In Phase 6, we'll add a retell_agent_id column
        agent = None
        user_id = None

        if call.agent_id:
            # Find agent by Retell agent ID
            result = await db.execute(select(Agent).where(Agent.retell_agent_id == call.agent_id))
            agent = result.scalar_one_or_none()

            # Fallback: check metadata for internal agent ID
            if not agent and call.metadata and call.metadata.get("internal_agent_id"):
                agent_id_str = call.metadata.get("internal_agent_id")
                try:
                    result = await db.execute(
                        select(Agent).where(Agent.id == uuid.UUID(agent_id_str))
                    )
                    agent = result.scalar_one_or_none()
                except (ValueError, TypeError):
                    pass

            if agent:
                user_id = agent.user_id

        # Auto-create contact from caller ID for inbound calls
        contact = None
        if user_id and call.from_number and call.direction == "inbound":
            contact = await get_or_create_contact(
                db=db,
                phone_number=call.from_number,
                user_id=user_id,
                log=log,
            )

        # Create call record
        call_record = CallRecord(
            user_id=user_id,
            provider="retell",
            provider_call_id=call.call_id,
            agent_id=agent.id if agent else None,
            contact_id=contact.id if contact else None,  # Link to CRM contact
            from_number=call.from_number or "",
            to_number=call.to_number or "",
            direction=convert_retell_direction(call.direction),
            status=CallStatus.IN_PROGRESS,
            started_at=datetime.fromtimestamp(call.start_timestamp / 1000, tz=UTC)
            if call.start_timestamp
            else datetime.now(UTC),
        )

        db.add(call_record)
        await db.commit()

        log.info(
            "call_record_created",
            record_id=str(call_record.id),
            contact_id=contact.id if contact else None,
        )
        return {"status": "received", "call_record_id": str(call_record.id)}

    except Exception as e:
        log.exception("call_started_error", error=str(e))
        # Return 200 to prevent Retell from retrying
        return {"status": "error", "message": str(e)}


@router.post("/call-ended")
async def retell_call_ended(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Handle call ended webhook from Retell.

    Updates the call record with final status, duration, and transcript.

    Args:
        request: FastAPI request
        db: Database session

    Returns:
        Acknowledgment response
    """
    await verify_retell_signature(request)

    body = await request.json()
    log = logger.bind(endpoint="retell_call_ended")

    try:
        payload = RetellWebhookPayload(**body)
        call = payload.call

        log = log.bind(
            call_id=call.call_id,
            duration_ms=call.duration_ms,
            disconnection_reason=call.disconnection_reason,
        )
        log.info("retell_call_ended_received")

        # Find existing call record
        result = await db.execute(
            select(CallRecord).where(CallRecord.provider_call_id == call.call_id)
        )
        call_record = result.scalar_one_or_none()

        if call_record:
            # Update call record
            call_record.status = CallStatus.COMPLETED
            call_record.ended_at = (
                datetime.fromtimestamp(call.end_timestamp / 1000, tz=UTC)
                if call.end_timestamp
                else datetime.now(UTC)
            )
            call_record.duration_seconds = (call.duration_ms or 0) // 1000

            # Save transcript
            if call.transcript:
                call_record.transcript = call.transcript
            elif call.transcript_object:
                call_record.transcript = format_transcript(call.transcript_object)

            # Save recording URL if available
            if call.recording_url:
                call_record.recording_url = call.recording_url

            await db.commit()

            # Update agent metrics
            if call_record.agent_id:
                await db.execute(
                    update(Agent)
                    .where(Agent.id == call_record.agent_id)
                    .values(
                        total_calls=Agent.total_calls + 1,
                        total_duration_seconds=Agent.total_duration_seconds
                        + (call_record.duration_seconds or 0),
                        last_call_at=datetime.now(UTC),
                    )
                )
                await db.commit()

            log.info(
                "call_record_updated",
                record_id=str(call_record.id),
                duration=call_record.duration_seconds,
                has_transcript=bool(call_record.transcript),
            )
        else:
            log.warning("call_record_not_found", call_id=call.call_id)

        return {"status": "received"}

    except Exception as e:
        log.exception("call_ended_error", error=str(e))
        return {"status": "error", "message": str(e)}


@router.post("/call-analyzed")
async def retell_call_analyzed(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Handle call analyzed webhook from Retell.

    Retell can perform post-call analysis including:
    - Sentiment analysis
    - Call summary
    - Custom data extraction

    This implements the "Outcome-Based Reporting" from the SpaceVoice spec.

    Args:
        request: FastAPI request
        db: Database session

    Returns:
        Acknowledgment response
    """
    await verify_retell_signature(request)

    body = await request.json()
    log = logger.bind(endpoint="retell_call_analyzed")

    try:
        payload = RetellWebhookPayload(**body)
        call = payload.call

        log = log.bind(call_id=call.call_id)
        log.info("retell_call_analyzed_received")

        if not call.call_analysis:
            log.info("no_analysis_data")
            return {"status": "received", "message": "No analysis data"}

        # Find call record
        result = await db.execute(
            select(CallRecord).where(CallRecord.provider_call_id == call.call_id)
        )
        call_record = result.scalar_one_or_none()

        if call_record:
            # Store analysis in metadata
            # The call_analysis can contain:
            # - call_summary: Brief summary of the call
            # - user_sentiment: Sentiment of the customer
            # - custom_analysis_data: Any custom extraction
            analysis = call.call_analysis

            # Log key metrics for the SpaceVoice spec
            log.info(
                "call_analysis_received",
                record_id=str(call_record.id),
                sentiment=analysis.get("user_sentiment"),
                has_summary=bool(analysis.get("call_summary")),
                custom_data_keys=list(analysis.get("custom_analysis_data", {}).keys()),
            )

            # In a full implementation, we'd store this in a dedicated
            # call_analysis table or in the call_record metadata
            # For now, we log it for visibility

            return {
                "status": "received",
                "sentiment": analysis.get("user_sentiment"),
                "has_summary": bool(analysis.get("call_summary")),
            }
        log.warning("call_record_not_found_for_analysis", call_id=call.call_id)
        return {"status": "received", "message": "Call record not found"}

    except Exception as e:
        log.exception("call_analyzed_error", error=str(e))
        return {"status": "error", "message": str(e)}


@router.post("/inbound")
async def retell_inbound_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> InboundCallResponse:
    """Handle inbound call webhook from Retell.

    When a call comes in to a Retell phone number, Retell calls this
    webhook to determine which agent should handle the call.

    This enables dynamic agent routing based on:
    - Called number (which agent owns this number)
    - Caller ID (VIP routing)
    - Time of day
    - Custom business logic

    Args:
        request: FastAPI request
        db: Database session

    Returns:
        Agent ID and optional metadata for the call
    """
    await verify_retell_signature(request)

    body = await request.json()
    log = logger.bind(endpoint="retell_inbound")

    try:
        inbound = InboundCallRequest(**body)

        log = log.bind(
            from_number=inbound.from_number,
            to_number=inbound.to_number,
        )
        log.info("retell_inbound_received")

        # Look up agent by the called phone number
        # Strategy 1: Use PhoneNumber.assigned_agent_id (preferred relationship)
        result = await db.execute(
            select(Agent)
            .join(PhoneNumber, PhoneNumber.assigned_agent_id == Agent.id)
            .where(PhoneNumber.phone_number == inbound.to_number)
            .where(Agent.is_active == True)  # noqa: E712
        )
        agent = result.scalar_one_or_none()

        # Strategy 2: Fallback - check if Agent.phone_number_id contains the phone number directly
        # (handles legacy data where phone_number_id stores the E.164 number instead of UUID)
        if not agent:
            log.info("trying_fallback_phone_lookup")
            result = await db.execute(
                select(Agent)
                .where(Agent.phone_number_id == inbound.to_number)
                .where(Agent.is_active == True)  # noqa: E712
            )
            agent = result.scalar_one_or_none()

        if not agent:
            # No agent found for this number
            log.warning("no_agent_for_number", to_number=inbound.to_number)

            # Return a default error response
            # In production, you'd have a fallback agent
            raise HTTPException(
                status_code=404,
                detail=f"No agent configured for number {inbound.to_number}",
            )

        log.info("agent_found_for_inbound", agent_id=str(agent.id), agent_name=agent.name)

        # Return the Retell agent ID for Retell to use
        # If the agent doesn't have a Retell agent ID, return our internal ID
        retell_id = agent.retell_agent_id or str(agent.id)

        return InboundCallResponse(
            agent_id=retell_id,
            metadata={
                "internal_agent_id": str(agent.id),
                "agent_name": agent.name,
                "caller_phone": inbound.from_number,
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        log.exception("inbound_routing_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from None
