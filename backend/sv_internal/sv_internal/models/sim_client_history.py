"""Simulated client monthly history model."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, Integer, Numeric, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from sv_internal.models.sim_client import SimClient


class SimClientHistory(Base, TimestampMixin):
    """Monthly history record for a simulated client."""

    __tablename__ = "sim_client_history"
    __table_args__ = (
        UniqueConstraint("client_id", "month", name="uq_sim_client_month"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sim_clients.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    month: Mapped[date] = mapped_column(Date, index=True, nullable=False)

    # Revenue
    invoiced_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    mrr: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    refunds: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=Decimal("0"), nullable=False
    )
    chargebacks: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=Decimal("0"), nullable=False
    )
    net_revenue: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    # Usage
    calls_handled: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_minutes: Mapped[float] = mapped_column(
        Numeric(10, 2), default=0.0, nullable=False
    )
    avg_call_duration: Mapped[float] = mapped_column(
        Numeric(8, 2), default=0.0, nullable=False
    )

    # Relationship
    client: Mapped["SimClient"] = relationship("SimClient", back_populates="history")
