"""Add Retell voice provider support to agents

Revision ID: 015_add_retell_voice_provider
Revises: e9a148e30e35
Create Date: 2026-01-17

This migration adds fields to support Retell AI as an alternative voice provider:
- voice_provider: Selects between OpenAI Realtime and Retell + Claude
- retell_agent_id: Stores the Retell agent ID for agents using Retell

This enables the SpaceVoice "Solid Stack":
- Retell AI for 140ms voice orchestration
- Claude 4.5 Sonnet for LLM reasoning
- Telnyx for telephony (already supported)
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "015_add_retell_voice_provider"
down_revision: Union[str, Sequence[str], None] = "e9a148e30e35"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add voice_provider and retell_agent_id columns to agents table."""

    # Add voice_provider column - determines which voice stack to use
    op.add_column(
        "agents",
        sa.Column(
            "voice_provider",
            sa.String(50),
            nullable=False,
            server_default="openai_realtime",
            comment="Voice provider: openai_realtime (GPT-4o) or retell_claude (Retell + Claude)",
        ),
    )

    # Add retell_agent_id column - stores Retell's agent ID
    op.add_column(
        "agents",
        sa.Column(
            "retell_agent_id",
            sa.String(100),
            nullable=True,
            comment="Retell AI agent ID (if using retell_claude voice provider)",
        ),
    )

    # Create index on retell_agent_id for quick lookups
    op.create_index(
        "ix_agents_retell_agent_id",
        "agents",
        ["retell_agent_id"],
        unique=False,
    )


def downgrade() -> None:
    """Remove voice_provider and retell_agent_id columns."""
    op.drop_index("ix_agents_retell_agent_id", table_name="agents")
    op.drop_column("agents", "retell_agent_id")
    op.drop_column("agents", "voice_provider")
