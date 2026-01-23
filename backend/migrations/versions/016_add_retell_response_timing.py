"""Add Retell response timing settings to agents

Revision ID: 016_add_retell_response_timing
Revises: 3ec8f7908c3c
Create Date: 2026-01-22

This migration adds response timing fields to optimize voice agent conversation flow:
- responsiveness: How quickly the agent responds (0-1, higher = faster)
- interruption_sensitivity: How easily user can interrupt (0-1, higher = easier)
- enable_backchannel: Enable "uh-huh", "mm-hmm" responses for natural flow

Default values are optimized for conversational flow:
- responsiveness=0.9 for quick 2-3 second responses instead of 5+ seconds
- interruption_sensitivity=0.8 for natural interruption handling
- enable_backchannel=True for active listening signals
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "016_add_retell_response_timing"
down_revision: Union[str, Sequence[str], None] = "3ec8f7908c3c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add response timing columns to agents table."""

    # Add responsiveness column - controls how quickly agent responds
    op.add_column(
        "agents",
        sa.Column(
            "responsiveness",
            sa.Float(),
            nullable=False,
            server_default="0.9",
            comment="Retell responsiveness (0.0-1.0). Higher = faster responses. Default 0.9.",
        ),
    )

    # Add interruption_sensitivity column - controls how easily user can interrupt
    op.add_column(
        "agents",
        sa.Column(
            "interruption_sensitivity",
            sa.Float(),
            nullable=False,
            server_default="0.8",
            comment="Retell interruption sensitivity (0.0-1.0). Higher = easier to interrupt.",
        ),
    )

    # Add enable_backchannel column - enables "uh-huh" responses
    op.add_column(
        "agents",
        sa.Column(
            "enable_backchannel",
            sa.Boolean(),
            nullable=False,
            server_default="true",
            comment="Enable AI backchannel responses (uh-huh, mm-hmm) for natural conversation.",
        ),
    )


def downgrade() -> None:
    """Remove response timing columns."""
    op.drop_column("agents", "enable_backchannel")
    op.drop_column("agents", "interruption_sensitivity")
    op.drop_column("agents", "responsiveness")
