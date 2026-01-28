"""Platform-wide income snapshot model."""

from datetime import date
from decimal import Decimal

from sqlalchemy import Date, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class SimIncomeSnapshot(Base, TimestampMixin):
    """Pre-computed platform-wide monthly aggregates."""

    __tablename__ = "sim_income_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    month: Mapped[date] = mapped_column(Date, unique=True, index=True, nullable=False)

    # Revenue aggregates
    total_mrr: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    total_arr: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    total_revenue: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    total_setup_fees: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total_refunds: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total_chargebacks: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total_net_revenue: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)

    # Client counts
    active_clients: Mapped[int] = mapped_column(Integer, nullable=False)
    new_clients: Mapped[int] = mapped_column(Integer, nullable=False)
    churned_clients: Mapped[int] = mapped_column(Integer, nullable=False)
    avg_revenue_per_client: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False
    )
