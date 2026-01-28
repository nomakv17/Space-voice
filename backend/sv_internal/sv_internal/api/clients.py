"""Internal client API routes."""

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from sv_internal.models import SimClient, SimClientHistory

router = APIRouter(prefix="/api/v1/internal", tags=["internal"])
logger = structlog.get_logger()

# Type alias for dependency injection
CurrentUser = Annotated[User, Depends(get_current_user)]


def mask_client_id(client_id: str) -> str:
    """Mask client ID for list views: SV-A1B2C3 -> SV-A1B2••"""
    if len(client_id) < 7:
        return client_id
    return f"{client_id[:7]}••"


def require_admin(user: User) -> None:
    """Require superuser access."""
    if not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )


class SimClientListResponse(BaseModel):
    """Client list item with masked ID."""

    id: str
    masked_id: str
    descriptor: str
    display_label: str
    client_size: str
    status: str
    mrr: float
    setup_fee: float
    net_revenue: float
    calls_handled_30d: int
    last_charge_status: str
    pricing_tier: str

    model_config = {"from_attributes": True}


class SimClientDetailResponse(BaseModel):
    """Full client detail response."""

    # Identity
    id: str
    client_id: str  # Full ID (admin detail only)
    masked_id: str
    descriptor: str
    client_size: str
    industry: str
    status: str
    onboarded_at: str

    # Payment
    processor: str
    customer_id: str
    subscription_id: str
    plan_id: str
    billing_cycle: str
    next_charge_date: str | None
    last_charge_date: str | None
    last_charge_status: str
    payment_method_type: str
    billing_currency: str

    # Revenue
    mrr: float
    arr: float
    setup_fee: float
    total_first_month: float
    paid_amount: float
    refunded_amount: float
    chargebacks_amount: float
    net_revenue: float

    # Payment counts
    invoice_count: int
    payment_count: int
    successful_payments: int
    failed_payments: int

    # Usage
    calls_received_30d: int
    calls_handled_30d: int
    avg_call_duration: float
    total_minutes_30d: float

    pricing_tier: str

    model_config = {"from_attributes": True}


class SimClientHistoryResponse(BaseModel):
    """Client monthly history response."""

    month: str
    invoiced_amount: float
    paid_amount: float
    mrr: float
    refunds: float
    chargebacks: float
    net_revenue: float
    calls_handled: int
    total_minutes: float
    avg_call_duration: float

    model_config = {"from_attributes": True}


@router.get("/clients", response_model=list[SimClientListResponse])
async def list_clients(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    size_filter: Annotated[str | None, Query(alias="size")] = None,
) -> list[SimClientListResponse]:
    """List all simulated clients with masked IDs."""
    require_admin(current_user)

    query = select(SimClient).order_by(SimClient.mrr.desc())

    if status_filter:
        query = query.where(SimClient.status == status_filter)
    if size_filter:
        query = query.where(SimClient.client_size == size_filter)

    result = await db.execute(query)
    clients = result.scalars().all()

    return [
        SimClientListResponse(
            id=str(c.id),
            masked_id=mask_client_id(c.client_id),
            descriptor=c.descriptor,
            display_label=f"{mask_client_id(c.client_id)} · {c.descriptor}",
            client_size=c.client_size,
            status=c.status,
            mrr=float(c.mrr),
            setup_fee=float(c.setup_fee),
            net_revenue=float(c.net_revenue),
            calls_handled_30d=c.calls_handled_30d,
            last_charge_status=c.last_charge_status,
            pricing_tier=c.pricing_tier,
        )
        for c in clients
    ]


@router.get("/clients/{client_id}", response_model=SimClientDetailResponse)
async def get_client(
    client_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> SimClientDetailResponse:
    """Get full client details (includes unmasked client_id)."""
    require_admin(current_user)

    result = await db.execute(select(SimClient).where(SimClient.id == client_id))
    client = result.scalar_one_or_none()

    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Client not found"
        )

    return SimClientDetailResponse(
        id=str(client.id),
        client_id=client.client_id,  # Full ID in detail view
        masked_id=mask_client_id(client.client_id),
        descriptor=client.descriptor,
        client_size=client.client_size,
        industry=client.industry,
        status=client.status,
        onboarded_at=client.onboarded_at.isoformat(),
        processor=client.processor,
        customer_id=client.customer_id,
        subscription_id=client.subscription_id,
        plan_id=client.plan_id,
        billing_cycle=client.billing_cycle,
        next_charge_date=(
            client.next_charge_date.isoformat() if client.next_charge_date else None
        ),
        last_charge_date=(
            client.last_charge_date.isoformat() if client.last_charge_date else None
        ),
        last_charge_status=client.last_charge_status,
        payment_method_type=client.payment_method_type,
        billing_currency=client.billing_currency,
        mrr=float(client.mrr),
        arr=float(client.arr),
        setup_fee=float(client.setup_fee),
        total_first_month=float(client.total_first_month),
        paid_amount=float(client.paid_amount),
        refunded_amount=float(client.refunded_amount),
        chargebacks_amount=float(client.chargebacks_amount),
        net_revenue=float(client.net_revenue),
        invoice_count=client.invoice_count,
        payment_count=client.payment_count,
        successful_payments=client.successful_payments,
        failed_payments=client.failed_payments,
        calls_received_30d=client.calls_received_30d,
        calls_handled_30d=client.calls_handled_30d,
        avg_call_duration=float(client.avg_call_duration),
        total_minutes_30d=float(client.total_minutes_30d),
        pricing_tier=client.pricing_tier,
    )


@router.get("/clients/{client_id}/history", response_model=list[SimClientHistoryResponse])
async def get_client_history(
    client_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> list[SimClientHistoryResponse]:
    """Get 6-month history for a client."""
    require_admin(current_user)

    result = await db.execute(
        select(SimClientHistory)
        .where(SimClientHistory.client_id == client_id)
        .order_by(SimClientHistory.month.desc())
    )
    history = result.scalars().all()

    return [
        SimClientHistoryResponse(
            month=h.month.isoformat(),
            invoiced_amount=float(h.invoiced_amount),
            paid_amount=float(h.paid_amount),
            mrr=float(h.mrr),
            refunds=float(h.refunds),
            chargebacks=float(h.chargebacks),
            net_revenue=float(h.net_revenue),
            calls_handled=h.calls_handled,
            total_minutes=float(h.total_minutes),
            avg_call_duration=float(h.avg_call_duration),
        )
        for h in history
    ]
