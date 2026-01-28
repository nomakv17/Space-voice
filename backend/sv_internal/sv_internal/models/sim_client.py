"""Simulated client model."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from sv_internal.models.sim_client_history import SimClientHistory


class SimClient(Base, TimestampMixin):
    """Simulated client with payment-derived data."""

    __tablename__ = "sim_clients"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Identity (masked in list views)
    client_id: Mapped[str] = mapped_column(
        String(20), unique=True, index=True, nullable=False
    )
    client_size: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # medium, enterprise
    industry: Mapped[str] = mapped_column(String(100), nullable=False)
    descriptor: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # "Enterprise HVAC"
    status: Mapped[str] = mapped_column(
        String(50), default="active", nullable=False
    )  # active, churned, paused
    onboarded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # Payment processor fields
    processor: Mapped[str] = mapped_column(
        String(50), default="stripe", nullable=False
    )
    customer_id: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # cus_...
    subscription_id: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # sub_...
    plan_id: Mapped[str] = mapped_column(String(100), nullable=False)  # price_...
    billing_cycle: Mapped[str] = mapped_column(
        String(20), default="monthly", nullable=False
    )  # monthly, annual
    next_charge_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_charge_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_charge_status: Mapped[str] = mapped_column(
        String(50), default="succeeded", nullable=False
    )  # succeeded, failed, pending
    payment_method_type: Mapped[str] = mapped_column(
        String(50), default="card", nullable=False
    )  # card, ach, wire
    billing_currency: Mapped[str] = mapped_column(
        String(10), default="usd", nullable=False
    )

    # Revenue (MRR separate from setup fees)
    mrr: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    arr: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    setup_fee: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=Decimal("0"), nullable=False
    )
    total_first_month: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    paid_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0"), nullable=False
    )
    refunded_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0"), nullable=False
    )
    chargebacks_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0"), nullable=False
    )
    net_revenue: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0"), nullable=False
    )

    # Payment counts
    invoice_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    payment_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    successful_payments: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_payments: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Usage (30-day rolling)
    calls_received_30d: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    calls_handled_30d: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    avg_call_duration: Mapped[float] = mapped_column(
        Numeric(8, 2), default=0.0, nullable=False
    )
    total_minutes_30d: Mapped[float] = mapped_column(
        Numeric(10, 2), default=0.0, nullable=False
    )

    # Pricing tier reference
    pricing_tier: Mapped[str] = mapped_column(
        String(50), default="balanced", nullable=False
    )

    # Relationship
    history: Mapped[list["SimClientHistory"]] = relationship(
        "SimClientHistory", back_populates="client", cascade="all, delete-orphan"
    )
