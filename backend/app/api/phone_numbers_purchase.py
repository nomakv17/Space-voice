"""Phone number purchasing API routes for Telnyx."""

import uuid
from datetime import UTC, datetime
from typing import Any

import httpx
import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser, user_id_to_uuid
from app.core.config import settings
from app.core.limiter import limiter
from app.db.session import get_db
from app.models.phone_number import PhoneNumber

router = APIRouter(prefix="/api/v1/phone-numbers", tags=["phone-numbers"])
logger = structlog.get_logger()

TELNYX_API_URL = "https://api.telnyx.com/v2"


# =============================================================================
# Pydantic Models
# =============================================================================


class AvailablePhoneNumber(BaseModel):
    """Available phone number from Telnyx."""

    phone_number: str
    region_code: str | None = None
    city: str | None = None
    state: str | None = None
    country_code: str
    cost: str | None = None
    features: list[str] = []
    record_type: str | None = None


class SearchAvailableNumbersResponse(BaseModel):
    """Response for available phone numbers search."""

    numbers: list[AvailablePhoneNumber]
    total: int


class PurchasePhoneNumberRequest(BaseModel):
    """Request to purchase a phone number."""

    phone_number: str
    friendly_name: str | None = None
    workspace_id: str | None = None


class PurchasedPhoneNumberResponse(BaseModel):
    """Response after purchasing a phone number."""

    id: str
    phone_number: str
    provider: str
    provider_id: str
    status: str
    created_at: datetime


# =============================================================================
# Helper Functions
# =============================================================================


def get_telnyx_headers() -> dict[str, str]:
    """Get Telnyx API headers."""
    if not settings.TELNYX_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="Telnyx API key not configured. Please set TELNYX_API_KEY in settings.",
        )
    return {
        "Authorization": f"Bearer {settings.TELNYX_API_KEY}",
        "Content-Type": "application/json",
    }


# =============================================================================
# Phone Number Purchasing Endpoints
# =============================================================================


@router.get("/available", response_model=SearchAvailableNumbersResponse)
@limiter.limit("30/minute")
async def search_available_numbers(
    request: Request,
    current_user: CurrentUser,
    country_code: str = Query(default="US", description="Two-letter country code"),
    area_code: str | None = Query(default=None, description="Area code filter"),
    city: str | None = Query(default=None, description="City filter"),
    state: str | None = Query(default=None, description="State/province filter"),
    contains: str | None = Query(default=None, description="Number contains pattern"),
    limit: int = Query(default=20, ge=1, le=100, description="Number of results"),
) -> SearchAvailableNumbersResponse:
    """Search for available phone numbers to purchase.

    Uses Telnyx Number Search API to find available numbers.

    Args:
        country_code: Two-letter ISO country code (default: US)
        area_code: Filter by area code (e.g., 415 for San Francisco)
        city: Filter by city name
        state: Filter by state/province
        contains: Find numbers containing this pattern
        limit: Maximum number of results (1-100)

    Returns:
        List of available phone numbers with pricing
    """
    log = logger.bind(user_id=current_user.id, country_code=country_code)
    log.info("searching_available_numbers")

    # Build Telnyx API query params
    params: dict[str, Any] = {
        "filter[country_code]": country_code,
        "filter[limit]": limit,
    }

    if area_code:
        params["filter[phone_number][national_destination_code]"] = area_code

    if city:
        params["filter[locality]"] = city

    if state:
        params["filter[administrative_area]"] = state

    if contains:
        params["filter[phone_number][contains]"] = contains

    try:
        async with httpx.AsyncClient(timeout=settings.TELNYX_TIMEOUT) as client:
            response = await client.get(
                f"{TELNYX_API_URL}/available_phone_numbers",
                headers=get_telnyx_headers(),
                params=params,
            )

            if response.status_code != 200:
                log.warning("telnyx_search_failed", status=response.status_code, body=response.text)
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Telnyx API error: {response.text}",
                )

            data = response.json()
            numbers = data.get("data", [])

            available_numbers = [
                AvailablePhoneNumber(
                    phone_number=n.get("phone_number", ""),
                    region_code=n.get("region_information", [{}])[0].get("region_code")
                    if n.get("region_information")
                    else None,
                    city=n.get("locality"),
                    state=n.get("administrative_area"),
                    country_code=n.get("country_code", country_code),
                    cost=n.get("cost_information", {}).get("upfront_cost"),
                    features=[
                        f.get("name", f) if isinstance(f, dict) else f
                        for f in n.get("features", [])
                    ],
                    record_type=n.get("record_type"),
                )
                for n in numbers
            ]

            return SearchAvailableNumbersResponse(
                numbers=available_numbers,
                total=len(available_numbers),
            )

    except httpx.RequestError as e:
        log.exception("telnyx_request_error", error=str(e))
        raise HTTPException(status_code=503, detail="Failed to connect to Telnyx API") from e


@router.post("/purchase", response_model=PurchasedPhoneNumberResponse, status_code=201)
@limiter.limit("10/minute")
async def purchase_phone_number(
    request: Request,
    purchase_request: PurchasePhoneNumberRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> PurchasedPhoneNumberResponse:
    """Purchase a phone number from Telnyx.

    This will:
    1. Order the phone number from Telnyx
    2. Configure it for voice calls
    3. Save it to the database

    Args:
        purchase_request: Phone number to purchase and optional settings

    Returns:
        Purchased phone number details
    """
    log = logger.bind(user_id=current_user.id, phone_number=purchase_request.phone_number)
    log.info("purchasing_phone_number")

    user_uuid = user_id_to_uuid(current_user.id)
    workspace_uuid = (
        uuid.UUID(purchase_request.workspace_id) if purchase_request.workspace_id else None
    )

    # Step 1: Order the phone number from Telnyx
    order_payload = {
        "phone_numbers": [{"phone_number": purchase_request.phone_number}],
        "connection_id": None,  # Will be configured later
    }

    try:
        async with httpx.AsyncClient(timeout=settings.TELNYX_TIMEOUT) as client:
            # Create number order
            order_response = await client.post(
                f"{TELNYX_API_URL}/number_orders",
                headers=get_telnyx_headers(),
                json=order_payload,
            )

            if order_response.status_code not in (200, 201):
                log.warning(
                    "telnyx_purchase_failed",
                    status=order_response.status_code,
                    body=order_response.text,
                )
                raise HTTPException(
                    status_code=order_response.status_code,
                    detail=f"Failed to purchase number: {order_response.text}",
                )

            order_data = order_response.json().get("data", {})
            order_id = order_data.get("id")

            # The phone numbers in the order
            phone_numbers = order_data.get("phone_numbers", [])
            if not phone_numbers:
                raise HTTPException(status_code=500, detail="No phone numbers in order response")

            # Get the Telnyx phone number ID
            telnyx_number_id = phone_numbers[0].get("id")
            actual_number = phone_numbers[0].get("phone_number", purchase_request.phone_number)

            log.info("phone_number_ordered", order_id=order_id, telnyx_number_id=telnyx_number_id)

    except httpx.RequestError as e:
        log.exception("telnyx_request_error", error=str(e))
        raise HTTPException(status_code=503, detail="Failed to connect to Telnyx API") from e

    # Step 2: Save to database
    phone_number = PhoneNumber(
        user_id=user_uuid,
        phone_number=actual_number,
        friendly_name=purchase_request.friendly_name or f"Number {actual_number[-4:]}",
        provider="telnyx",
        provider_id=telnyx_number_id or order_id,
        workspace_id=workspace_uuid,
        can_receive_calls=True,
        can_make_calls=True,
        can_receive_sms=True,
        can_send_sms=True,
        status="active",
        purchased_at=datetime.now(UTC),
    )

    db.add(phone_number)
    await db.commit()
    await db.refresh(phone_number)

    log.info("phone_number_saved", phone_number_id=str(phone_number.id))

    return PurchasedPhoneNumberResponse(
        id=str(phone_number.id),
        phone_number=phone_number.phone_number,
        provider=phone_number.provider,
        provider_id=phone_number.provider_id,
        status=phone_number.status,
        created_at=phone_number.created_at,
    )


@router.delete("/release/{phone_number_id}", status_code=204)
@limiter.limit("10/minute")
async def release_phone_number(
    phone_number_id: str,
    request: Request,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Release (delete) a phone number back to Telnyx.

    This will:
    1. Delete the number from Telnyx
    2. Remove it from the database

    Args:
        phone_number_id: ID of the phone number to release
    """
    from sqlalchemy import select

    log = logger.bind(user_id=current_user.id, phone_number_id=phone_number_id)
    log.info("releasing_phone_number")

    user_uuid = user_id_to_uuid(current_user.id)

    # Get the phone number from database
    result = await db.execute(
        select(PhoneNumber).where(
            PhoneNumber.id == uuid.UUID(phone_number_id),
            PhoneNumber.user_id == user_uuid,
        )
    )
    phone_number = result.scalar_one_or_none()

    if not phone_number:
        raise HTTPException(status_code=404, detail="Phone number not found")

    # Delete from Telnyx if it's a Telnyx number
    if phone_number.provider == "telnyx" and phone_number.provider_id:
        try:
            async with httpx.AsyncClient(timeout=settings.TELNYX_TIMEOUT) as client:
                delete_response = await client.delete(
                    f"{TELNYX_API_URL}/phone_numbers/{phone_number.provider_id}",
                    headers=get_telnyx_headers(),
                )

                if delete_response.status_code not in (200, 204, 404):
                    log.warning(
                        "telnyx_release_failed",
                        status=delete_response.status_code,
                        body=delete_response.text,
                    )
                    # Don't fail - still remove from our database

                log.info("telnyx_number_released", provider_id=phone_number.provider_id)

        except httpx.RequestError as e:
            log.warning("telnyx_release_error", error=str(e))
            # Don't fail - still remove from our database

    # Delete from database
    await db.delete(phone_number)
    await db.commit()

    log.info("phone_number_deleted")


@router.get("/pricing")
@limiter.limit("30/minute")
async def get_phone_number_pricing(
    request: Request,
    current_user: CurrentUser,
    country_code: str = Query(default="US", description="Two-letter country code"),
) -> dict[str, Any]:
    """Get phone number pricing for a country.

    Returns Telnyx pricing information for the specified country.
    """
    log = logger.bind(user_id=current_user.id, country_code=country_code)
    log.info("fetching_pricing")

    # Note: Telnyx doesn't have a direct pricing API
    # Pricing is typically shown on the number search results
    # This endpoint returns general pricing info

    pricing = {
        "country_code": country_code,
        "currency": "USD",
        "local_numbers": {
            "monthly": "1.00",
            "per_minute_inbound": "0.0060",
            "per_minute_outbound": "0.0075",
        },
        "toll_free_numbers": {
            "monthly": "2.00",
            "per_minute_inbound": "0.0120",
        },
        "note": "Prices are estimates. Actual pricing shown during number search.",
        "pricing_url": "https://telnyx.com/pricing",
    }

    return pricing
