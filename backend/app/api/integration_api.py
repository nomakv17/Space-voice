"""External Integration API for third-party CRM systems.

This module provides REST endpoints that allow external CRM systems to:
- Push contacts to SpaceVoice
- Receive call events/transcripts via webhooks
- Query call history and transcripts
- Sync appointment data

Authentication is via API key in the X-API-Key header.
"""

import hashlib
import hmac
import logging
import secrets
import uuid
from datetime import UTC, datetime
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser
from app.core.limiter import limiter
from app.db.session import get_db
from app.models.call_record import CallRecord
from app.models.contact import Contact
from app.models.workspace import Workspace

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/integrations", tags=["integrations"])


# --- Schemas ---


class ContactCreateRequest(BaseModel):
    """Request to create/update a contact from external system."""

    phone_number: str
    first_name: str
    last_name: str | None = None
    email: EmailStr | None = None
    company_name: str | None = None
    tags: str | None = None
    notes: str | None = None
    external_id: str | None = None  # ID from the external CRM

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        """Normalize phone number."""
        # Remove common formatting
        cleaned = "".join(c for c in v if c.isdigit() or c == "+")
        if not cleaned.startswith("+"):
            cleaned = f"+1{cleaned}"  # Default to US
        return cleaned


class ContactResponse(BaseModel):
    """Contact response for external systems."""

    id: int
    phone_number: str
    first_name: str
    last_name: str | None
    email: str | None
    company_name: str | None
    status: str
    tags: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class WebhookRegisterRequest(BaseModel):
    """Request to register a webhook endpoint."""

    url: str
    events: list[str]  # e.g., ["call.started", "call.ended", "call.analyzed"]
    secret: str | None = None  # Optional secret for signature verification


class WebhookResponse(BaseModel):
    """Webhook registration response."""

    id: str
    url: str
    events: list[str]
    created_at: datetime


class CallRecordResponse(BaseModel):
    """Call record response for external systems."""

    id: str
    agent_id: str | None
    caller_phone: str | None
    status: str
    direction: str
    started_at: datetime | None
    ended_at: datetime | None
    duration_seconds: int | None
    transcript: str | None
    sentiment: str | None
    summary: str | None


# --- In-memory webhook storage (in production, use Redis or DB) ---
# Format: {user_id: [{id, url, events, secret, created_at}]}
registered_webhooks: dict[int, list[dict[str, Any]]] = {}


# --- Endpoints ---


@router.post("/contacts", response_model=ContactResponse, status_code=201)
@limiter.limit("100/minute")
async def create_or_update_contact(
    request: Request,
    contact_data: ContactCreateRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    workspace_id: str | None = None,
) -> dict[str, Any]:
    """Create or update a contact from an external CRM.

    If a contact with the same phone number exists, it will be updated.
    Otherwise, a new contact is created.

    Args:
        contact_data: Contact information
        workspace_id: Optional workspace ID to scope the contact
    """
    user_id = current_user.id

    # Get workspace UUID if provided
    ws_uuid: uuid.UUID | None = None
    if workspace_id:
        try:
            ws_uuid = uuid.UUID(workspace_id)
            # Verify workspace belongs to user
            ws_result = await db.execute(
                select(Workspace).where(Workspace.id == ws_uuid, Workspace.user_id == user_id)
            )
            if not ws_result.scalar_one_or_none():
                raise HTTPException(status_code=404, detail="Workspace not found")
        except ValueError as e:
            raise HTTPException(status_code=400, detail="Invalid workspace ID") from e

    # Check for existing contact
    query = select(Contact).where(
        Contact.user_id == user_id,
        Contact.phone_number == contact_data.phone_number,
    )
    if ws_uuid:
        query = query.where(Contact.workspace_id == ws_uuid)

    contact_result = await db.execute(query)
    contact: Contact | None = contact_result.scalar_one_or_none()

    if contact:
        # Update existing contact
        contact.first_name = contact_data.first_name
        if contact_data.last_name:
            contact.last_name = contact_data.last_name
        if contact_data.email:
            contact.email = contact_data.email
        if contact_data.company_name:
            contact.company_name = contact_data.company_name
        if contact_data.tags:
            # Merge tags
            existing_tags = set((contact.tags or "").split(","))
            new_tags = set(contact_data.tags.split(","))
            contact.tags = ",".join(existing_tags | new_tags)
        if contact_data.notes:
            contact.notes = (contact.notes or "") + "\n" + contact_data.notes

        logger.info("Updated contact from external API: %d", contact.id)
    else:
        # Create new contact
        contact = Contact(
            user_id=user_id,
            workspace_id=ws_uuid,
            phone_number=contact_data.phone_number,
            first_name=contact_data.first_name,
            last_name=contact_data.last_name,
            email=contact_data.email,
            company_name=contact_data.company_name,
            tags=contact_data.tags or "api-import",
            notes=contact_data.notes,
            status="new",
        )
        db.add(contact)
        logger.info("Created contact from external API: %s", contact_data.phone_number)

    await db.commit()
    await db.refresh(contact)

    return {
        "id": contact.id,
        "phone_number": contact.phone_number,
        "first_name": contact.first_name,
        "last_name": contact.last_name,
        "email": contact.email,
        "company_name": contact.company_name,
        "status": contact.status,
        "tags": contact.tags,
        "notes": contact.notes,
        "created_at": contact.created_at,
        "updated_at": contact.updated_at,
    }


@router.get("/contacts/{contact_id}", response_model=ContactResponse)
@limiter.limit("100/minute")
async def get_contact(
    request: Request,
    contact_id: int,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get a contact by ID."""
    user_id = current_user.id

    result = await db.execute(
        select(Contact).where(Contact.id == contact_id, Contact.user_id == user_id)
    )
    contact = result.scalar_one_or_none()

    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    return {
        "id": contact.id,
        "phone_number": contact.phone_number,
        "first_name": contact.first_name,
        "last_name": contact.last_name,
        "email": contact.email,
        "company_name": contact.company_name,
        "status": contact.status,
        "tags": contact.tags,
        "notes": contact.notes,
        "created_at": contact.created_at,
        "updated_at": contact.updated_at,
    }


@router.get("/contacts", response_model=list[ContactResponse])
@limiter.limit("100/minute")
async def list_contacts(
    request: Request,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    workspace_id: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """List contacts, optionally filtered by workspace."""
    user_id = current_user.id

    query = select(Contact).where(Contact.user_id == user_id)

    if workspace_id:
        try:
            ws_uuid = uuid.UUID(workspace_id)
            query = query.where(Contact.workspace_id == ws_uuid)
        except ValueError as e:
            raise HTTPException(status_code=400, detail="Invalid workspace ID") from e

    query = query.order_by(Contact.created_at.desc()).offset(offset).limit(min(limit, 500))
    result = await db.execute(query)
    contacts = result.scalars().all()

    return [
        {
            "id": c.id,
            "phone_number": c.phone_number,
            "first_name": c.first_name,
            "last_name": c.last_name,
            "email": c.email,
            "company_name": c.company_name,
            "status": c.status,
            "tags": c.tags,
            "notes": c.notes,
            "created_at": c.created_at,
            "updated_at": c.updated_at,
        }
        for c in contacts
    ]


@router.post("/webhooks", response_model=WebhookResponse, status_code=201)
@limiter.limit("10/minute")
async def register_webhook(
    request: Request,
    webhook_data: WebhookRegisterRequest,
    current_user: CurrentUser,
) -> dict[str, Any]:
    """Register a webhook to receive call events.

    Supported events:
    - call.started: When a call begins
    - call.ended: When a call ends
    - call.analyzed: When call analysis is complete (transcript, sentiment)
    """
    user_id = current_user.id
    valid_events = {"call.started", "call.ended", "call.analyzed"}

    # Validate events
    invalid = set(webhook_data.events) - valid_events
    if invalid:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid events: {invalid}. Valid events: {valid_events}",
        )

    # Generate webhook ID and secret
    webhook_id = str(uuid.uuid4())
    secret = webhook_data.secret or secrets.token_urlsafe(32)

    webhook = {
        "id": webhook_id,
        "url": webhook_data.url,
        "events": webhook_data.events,
        "secret": secret,
        "created_at": datetime.now(UTC),
    }

    # Store webhook (in production, use Redis or DB)
    if user_id not in registered_webhooks:
        registered_webhooks[user_id] = []
    registered_webhooks[user_id].append(webhook)

    logger.info("Registered webhook for user %d: %s -> %s", user_id, webhook_id, webhook_data.url)

    return {
        "id": webhook_id,
        "url": webhook_data.url,
        "events": webhook_data.events,
        "created_at": webhook["created_at"],
    }


@router.get("/webhooks")
@limiter.limit("100/minute")
async def list_webhooks(
    request: Request,
    current_user: CurrentUser,
) -> list[dict[str, Any]]:
    """List registered webhooks for the current user."""
    user_id = current_user.id
    webhooks = registered_webhooks.get(user_id, [])

    return [
        {
            "id": w["id"],
            "url": w["url"],
            "events": w["events"],
            "created_at": w["created_at"],
        }
        for w in webhooks
    ]


@router.delete("/webhooks/{webhook_id}", status_code=204)
@limiter.limit("100/minute")
async def delete_webhook(
    request: Request,
    webhook_id: str,
    current_user: CurrentUser,
) -> None:
    """Delete a registered webhook."""
    user_id = current_user.id
    webhooks = registered_webhooks.get(user_id, [])

    for i, w in enumerate(webhooks):
        if w["id"] == webhook_id:
            webhooks.pop(i)
            logger.info("Deleted webhook for user %d: %s", user_id, webhook_id)
            return

    raise HTTPException(status_code=404, detail="Webhook not found")


@router.get("/calls", response_model=list[CallRecordResponse])
@limiter.limit("100/minute")
async def list_calls(
    request: Request,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    workspace_id: str | None = None,
    agent_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """List call records with optional filtering.

    Returns call history with transcripts and analysis for integration
    with external CRM systems.
    """
    user_id = current_user.id

    # Build query - user_id is a UUID in call_records
    from app.core.auth import user_id_to_uuid

    user_uuid = user_id_to_uuid(user_id)
    query = select(CallRecord).where(CallRecord.user_id == user_uuid)

    if workspace_id:
        try:
            ws_uuid = uuid.UUID(workspace_id)
            query = query.where(CallRecord.workspace_id == ws_uuid)
        except ValueError as e:
            raise HTTPException(status_code=400, detail="Invalid workspace ID") from e

    if agent_id:
        try:
            agent_uuid = uuid.UUID(agent_id)
            query = query.where(CallRecord.agent_id == agent_uuid)
        except ValueError as e:
            raise HTTPException(status_code=400, detail="Invalid agent ID") from e

    query = query.order_by(CallRecord.started_at.desc()).offset(offset).limit(min(limit, 200))
    result = await db.execute(query)
    calls = result.scalars().all()

    return [
        {
            "id": str(c.id),
            "agent_id": str(c.agent_id) if c.agent_id else None,
            "caller_phone": c.from_number if c.direction == "inbound" else c.to_number,
            "status": c.status,
            "direction": c.direction,
            "started_at": c.started_at,
            "ended_at": c.ended_at,
            "duration_seconds": c.duration_seconds,
            "transcript": c.transcript,
            "sentiment": None,  # Not implemented in model
            "summary": None,  # Not implemented in model
        }
        for c in calls
    ]


@router.get("/calls/{call_id}", response_model=CallRecordResponse)
@limiter.limit("100/minute")
async def get_call(
    request: Request,
    call_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get a specific call record with full details."""
    user_id = current_user.id
    from app.core.auth import user_id_to_uuid

    user_uuid = user_id_to_uuid(user_id)

    try:
        call_uuid = uuid.UUID(call_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid call ID") from e

    result = await db.execute(
        select(CallRecord).where(CallRecord.id == call_uuid, CallRecord.user_id == user_uuid)
    )
    call = result.scalar_one_or_none()

    if not call:
        raise HTTPException(status_code=404, detail="Call not found")

    return {
        "id": str(call.id),
        "agent_id": str(call.agent_id) if call.agent_id else None,
        "caller_phone": call.from_number if call.direction == "inbound" else call.to_number,
        "status": call.status,
        "direction": call.direction,
        "started_at": call.started_at,
        "ended_at": call.ended_at,
        "duration_seconds": call.duration_seconds,
        "transcript": call.transcript,
        "sentiment": None,  # Not implemented in model
        "summary": None,  # Not implemented in model
    }


# --- Webhook Sender Utility ---


async def send_webhook_event(
    user_id: int,
    event_type: str,
    payload: dict[str, Any],
) -> None:
    """Send a webhook event to all registered endpoints for a user.

    This should be called from retell_webhooks.py when call events occur.

    Args:
        user_id: The user ID
        event_type: The event type (e.g., "call.started")
        payload: The event payload data
    """
    webhooks = registered_webhooks.get(user_id, [])

    for webhook in webhooks:
        if event_type not in webhook["events"]:
            continue

        try:
            # Prepare payload
            event_payload = {
                "event": event_type,
                "timestamp": datetime.now(UTC).isoformat(),
                "data": payload,
            }

            # Sign payload if secret is set
            headers: dict[str, str] = {"Content-Type": "application/json"}
            if webhook.get("secret"):
                signature = hmac.new(
                    webhook["secret"].encode(),
                    str(event_payload).encode(),
                    hashlib.sha256,
                ).hexdigest()
                headers["X-Webhook-Signature"] = f"sha256={signature}"

            # Send webhook (fire and forget)
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    webhook["url"],
                    json=event_payload,
                    headers=headers,
                )

                if response.status_code >= 400:
                    logger.warning(
                        "Webhook delivery failed: user=%d, url=%s, status=%d",
                        user_id,
                        webhook["url"],
                        response.status_code,
                    )
                else:
                    logger.debug(
                        "Webhook delivered: user=%d, event=%s, url=%s",
                        user_id,
                        event_type,
                        webhook["url"],
                    )

        except Exception as e:
            logger.warning(
                "Webhook delivery error: user=%d, url=%s, error=%s",
                user_id,
                webhook["url"],
                str(e),
            )
