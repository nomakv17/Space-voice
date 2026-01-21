"""Telnyx Call Control webhook handlers.

This module handles webhooks from Telnyx for Call Control events.
When a call comes in to the Telnyx 639 number, we answer it and
transfer it to Retell's SIP endpoint for AI handling.

Call Flow:
1. Caller dials +16399746645 (Telnyx)
2. Telnyx sends call.initiated webhook
3. We answer the call
4. Telnyx sends call.answered webhook
5. We transfer the call to Retell via SIP
6. Retell handles the AI conversation
"""

from http import HTTPStatus
from typing import Any

import structlog
from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter(prefix="/webhooks/telnyx", tags=["telnyx-webhooks"])
logger = structlog.get_logger()

# Retell SIP endpoint for inbound calls
RETELL_SIP_ENDPOINT = "sip.retellai.com"


class TelnyxCallPayload(BaseModel):
    """Telnyx Call Control event payload."""

    call_control_id: str
    call_leg_id: str | None = None
    call_session_id: str | None = None
    connection_id: str | None = None
    from_: str | None = None
    to: str | None = None
    direction: str | None = None
    state: str | None = None
    client_state: str | None = None
    sip_response_code: int | None = None

    class Config:
        populate_by_name = True


class TelnyxWebhookEvent(BaseModel):
    """Telnyx webhook event wrapper."""

    data: dict[str, Any]
    meta: dict[str, Any] | None = None


@router.post("/call")
async def telnyx_call_webhook(request: Request) -> dict[str, str]:
    """Handle Telnyx Call Control webhooks.

    This endpoint receives all call events and dispatches based on event type.
    The key events we handle:
    - call.initiated: Answer the call
    - call.answered: Transfer to Retell SIP

    Args:
        request: FastAPI request

    Returns:
        Acknowledgment response
    """
    body = await request.json()
    log = logger.bind(endpoint="telnyx_call_webhook")

    try:
        event_type = body.get("data", {}).get("event_type", "unknown")
        payload = body.get("data", {}).get("payload", {})

        call_control_id = payload.get("call_control_id", "")
        from_number = payload.get("from", "")
        to_number = payload.get("to", "")

        log = log.bind(
            event_type=event_type,
            call_control_id=call_control_id,
            from_number=from_number,
            to_number=to_number,
        )
        log.info("telnyx_webhook_received")

        if event_type == "call.initiated":
            # Only answer inbound calls (to_number is a phone number, not SIP)
            # Skip the outbound transfer leg (to_number is a SIP URI)
            if to_number.startswith("sip:"):
                log.info("outbound_sip_leg_skipping")
                return {"status": "outbound_leg_initiated"}

            # Answer the incoming call
            await answer_call(call_control_id, log)
            return {"status": "answering"}

        if event_type == "call.answered":
            # Only transfer if this is the original inbound call, not the transfer leg
            # The transfer leg has a SIP URI as the to_number
            if to_number.startswith("sip:"):
                log.info("transfer_leg_answered_skipping")
                return {"status": "transfer_leg_answered"}

            # Transfer to Retell SIP for AI handling
            await transfer_to_retell(call_control_id, to_number, log, from_number)
            return {"status": "transferring_to_retell"}

        if event_type == "call.hangup":
            log.info("call_ended")
            return {"status": "call_ended"}

        if event_type == "call.transfer.completed":
            log.info("transfer_completed")
            return {"status": "transfer_completed"}

        if event_type == "call.transfer.failed":
            log.error("transfer_failed", reason=payload.get("reason"))
            return {"status": "transfer_failed"}

        log.debug("unhandled_event_type")
        return {"status": "ignored"}

    except Exception as e:
        log.exception("telnyx_webhook_error", error=str(e))
        return {"status": "error", "message": str(e)}


async def answer_call(call_control_id: str, log: structlog.BoundLogger) -> None:
    """Answer an incoming call.

    Args:
        call_control_id: Telnyx call control ID
        log: Logger instance
    """
    import httpx

    from app.core.config import settings

    log.info("answering_call")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"https://api.telnyx.com/v2/calls/{call_control_id}/actions/answer",
            headers={
                "Authorization": f"Bearer {settings.TELNYX_API_KEY}",
                "Content-Type": "application/json",
            },
            json={},
        )

        if response.status_code == HTTPStatus.OK:
            log.info("call_answered_successfully")
        else:
            log.error("answer_failed", status=response.status_code, body=response.text)


async def transfer_to_retell(
    call_control_id: str,
    to_number: str,
    log: structlog.BoundLogger,
    from_number: str = "",
) -> None:
    """Transfer the call to Retell's SIP endpoint.

    For custom telephony, we must first register the call with Retell to get
    a call_id, then transfer to sip:{call_id}@sip.retellai.com.

    Args:
        call_control_id: Telnyx call control ID
        to_number: The number that was called (used for Retell routing)
        log: Logger instance
        from_number: The caller's phone number
    """
    import httpx
    from sqlalchemy import select

    from app.core.config import settings
    from app.db.session import AsyncSessionLocal
    from app.models.agent import Agent
    from app.models.phone_number import PhoneNumber

    # Step 1: Get the agent_id for this phone number directly from DB
    log.info("fetching_agent_for_number", to_number=to_number)
    async with AsyncSessionLocal() as db:
        # Find agent by phone number assignment
        result = await db.execute(
            select(Agent)
            .join(PhoneNumber, PhoneNumber.assigned_agent_id == Agent.id)
            .where(PhoneNumber.phone_number == to_number)
            .where(Agent.is_active.is_(True))
        )
        agent = result.scalar_one_or_none()

        if not agent or not agent.retell_agent_id:
            log.error("no_agent_found_for_number", to_number=to_number)
            return

        retell_agent_id = agent.retell_agent_id
        log.info("agent_found", agent_name=agent.name, retell_agent_id=retell_agent_id)

    async with httpx.AsyncClient() as client:
        # Step 2: Register the call with Retell to get a call_id
        log.info("registering_call_with_retell")
        register_response = await client.post(
            "https://api.retellai.com/v2/register-phone-call",
            headers={
                "Authorization": f"Bearer {settings.RETELL_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "agent_id": retell_agent_id,
                "from_number": from_number,
                "to_number": to_number,
                "direction": "inbound",
            },
            timeout=10,
        )

        if register_response.status_code != HTTPStatus.CREATED:
            log.error(
                "retell_register_failed",
                status=register_response.status_code,
                body=register_response.text,
            )
            return

        register_data = register_response.json()
        retell_call_id = register_data.get("call_id")
        if not retell_call_id:
            log.error("no_call_id_from_retell", response=register_data)
            return

        log.info("retell_call_registered", call_id=retell_call_id)

        # Step 3: Build SIP URI with the call_id and transfer
        sip_uri = f"sip:{retell_call_id}@{RETELL_SIP_ENDPOINT}"
        log.info("transferring_to_retell", sip_uri=sip_uri)

        transfer_response = await client.post(
            f"https://api.telnyx.com/v2/calls/{call_control_id}/actions/transfer",
            headers={
                "Authorization": f"Bearer {settings.TELNYX_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "to": sip_uri,
            },
        )

        if transfer_response.status_code == HTTPStatus.OK:
            log.info("transfer_initiated_successfully")
        else:
            log.error(
                "transfer_failed",
                status=transfer_response.status_code,
                body=transfer_response.text,
            )
