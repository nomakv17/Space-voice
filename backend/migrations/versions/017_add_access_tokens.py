"""Add access_tokens table for one-time dashboard access links

Revision ID: 017_add_access_tokens
Revises: 016_add_retell_response_timing
Create Date: 2026-01-24

This migration adds the access_tokens table for secure, single-use URLs
that grant temporary dashboard access for superior review.

Features:
- One-time use: token is invalidated after first use
- Time-limited: configurable expiration (default 24h, max 72h)
- Audit trail: logs usage IP, creation time, and revocation
- Read-only mode: optional flag to restrict write operations
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "017_add_access_tokens"
down_revision: Union[str, Sequence[str], None] = "016_add_retell_response_timing"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create access_tokens table."""

    op.create_table(
        "access_tokens",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "token",
            sa.String(64),
            unique=True,
            index=True,
            nullable=False,
            comment="Unique access token (sv_at_xxx format)",
        ),
        sa.Column(
            "created_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            comment="Admin user who created this token",
        ),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="When the token expires",
        ),
        sa.Column(
            "used_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When the token was consumed (null = not used)",
        ),
        sa.Column(
            "used_by_ip",
            sa.String(45),
            nullable=True,
            comment="IP address of the user who consumed the token",
        ),
        sa.Column(
            "label",
            sa.String(255),
            nullable=True,
            comment="Human-readable label (e.g., 'For CEO Review')",
        ),
        sa.Column(
            "is_read_only",
            sa.Boolean(),
            nullable=False,
            server_default="true",
            comment="Whether access is read-only",
        ),
        sa.Column(
            "revoked_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="When the token was manually revoked (null = not revoked)",
        ),
        sa.Column(
            "notes",
            sa.Text(),
            nullable=True,
            comment="Optional notes about this access token",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )

    # Create index for quick lookups by creator
    op.create_index(
        "ix_access_tokens_created_by_id",
        "access_tokens",
        ["created_by_id"],
    )


def downgrade() -> None:
    """Drop access_tokens table."""
    op.drop_index("ix_access_tokens_created_by_id", table_name="access_tokens")
    op.drop_table("access_tokens")
