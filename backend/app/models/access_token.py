"""Access token model for one-time dashboard access links."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class AccessToken(Base, TimestampMixin):
    """One-time access token for secure dashboard access sharing.

    These tokens allow admins to generate single-use URLs that grant
    temporary read-only access to the dashboard for superior review.
    """

    __tablename__ = "access_tokens"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    used_by_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)  # IPv6 max length
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_read_only: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    created_by: Mapped["User"] = relationship("User", back_populates="access_tokens")

    @property
    def is_valid(self) -> bool:
        """Check if token is still valid (not used, not expired, not revoked)."""
        from datetime import UTC

        now = datetime.now(UTC)
        return (
            self.used_at is None
            and self.revoked_at is None
            and self.expires_at > now
        )

    @property
    def status(self) -> str:
        """Get human-readable status of the token."""
        if self.revoked_at:
            return "revoked"
        if self.used_at:
            return "used"
        from datetime import UTC

        if self.expires_at <= datetime.now(UTC):
            return "expired"
        return "active"
