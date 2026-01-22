"""Pricing configuration model for admin-managed margins and costs."""

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import DateTime, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PricingConfig(Base):
    """Pricing configuration per tier with margin management.

    Allows admins to set markup percentages on top of base provider costs
    to control profitability while maintaining competitive pricing.
    """

    __tablename__ = "pricing_configs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # Tier identification (matches frontend tier IDs)
    tier_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    tier_name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Base costs (what SpaceVoice pays to providers)
    base_llm_cost_per_minute: Mapped[Decimal] = mapped_column(
        Numeric(10, 6), nullable=False, comment="LLM provider cost per minute"
    )
    base_stt_cost_per_minute: Mapped[Decimal] = mapped_column(
        Numeric(10, 6), nullable=False, comment="Speech-to-text cost per minute"
    )
    base_tts_cost_per_minute: Mapped[Decimal] = mapped_column(
        Numeric(10, 6), nullable=False, comment="Text-to-speech cost per minute"
    )
    base_telephony_cost_per_minute: Mapped[Decimal] = mapped_column(
        Numeric(10, 6), nullable=False, comment="Telephony cost per minute"
    )

    # Markup percentages (admin configurable)
    ai_markup_percentage: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), default=Decimal("30.00"), nullable=False, comment="Markup % on AI costs"
    )
    telephony_markup_percentage: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), default=Decimal("20.00"), nullable=False, comment="Markup % on telephony"
    )

    # Computed final prices (updated when base costs or markups change)
    final_ai_price_per_minute: Mapped[Decimal] = mapped_column(
        Numeric(10, 6), nullable=False, comment="Client-facing AI price per minute"
    )
    final_telephony_price_per_minute: Mapped[Decimal] = mapped_column(
        Numeric(10, 6), nullable=False, comment="Client-facing telephony price per minute"
    )
    final_total_price_per_minute: Mapped[Decimal] = mapped_column(
        Numeric(10, 6), nullable=False, comment="Total client-facing price per minute"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    def recalculate_prices(self) -> None:
        """Recalculate final prices based on base costs and markups."""
        # Total base AI cost
        base_ai_total = (
            self.base_llm_cost_per_minute
            + self.base_stt_cost_per_minute
            + self.base_tts_cost_per_minute
        )

        # Apply markups
        ai_multiplier = 1 + (self.ai_markup_percentage / 100)
        telephony_multiplier = 1 + (self.telephony_markup_percentage / 100)

        self.final_ai_price_per_minute = base_ai_total * ai_multiplier
        self.final_telephony_price_per_minute = (
            self.base_telephony_cost_per_minute * telephony_multiplier
        )
        self.final_total_price_per_minute = (
            self.final_ai_price_per_minute + self.final_telephony_price_per_minute
        )

    @property
    def total_base_cost_per_minute(self) -> Decimal:
        """Total base cost per minute (what SpaceVoice pays)."""
        return (
            self.base_llm_cost_per_minute
            + self.base_stt_cost_per_minute
            + self.base_tts_cost_per_minute
            + self.base_telephony_cost_per_minute
        )

    @property
    def profit_per_minute(self) -> Decimal:
        """Profit margin per minute."""
        return self.final_total_price_per_minute - self.total_base_cost_per_minute

    @property
    def profit_margin_percentage(self) -> Decimal:
        """Overall profit margin as percentage."""
        if self.total_base_cost_per_minute == 0:
            return Decimal("0")
        return (self.profit_per_minute / self.total_base_cost_per_minute) * 100

    def __repr__(self) -> str:
        return f"<PricingConfig(tier_id={self.tier_id}, total=${self.final_total_price_per_minute}/min)>"
