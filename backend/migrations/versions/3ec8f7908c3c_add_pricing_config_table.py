"""add_pricing_config_table

Revision ID: 3ec8f7908c3c
Revises: bfb7493e2e0e
Create Date: 2026-01-21 21:08:58.321581

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '3ec8f7908c3c'
down_revision: Union[str, Sequence[str], None] = 'bfb7493e2e0e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('pricing_configs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('tier_id', sa.String(length=50), nullable=False),
    sa.Column('tier_name', sa.String(length=100), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('base_llm_cost_per_minute', sa.Numeric(precision=10, scale=6), nullable=False, comment='LLM provider cost per minute'),
    sa.Column('base_stt_cost_per_minute', sa.Numeric(precision=10, scale=6), nullable=False, comment='Speech-to-text cost per minute'),
    sa.Column('base_tts_cost_per_minute', sa.Numeric(precision=10, scale=6), nullable=False, comment='Text-to-speech cost per minute'),
    sa.Column('base_telephony_cost_per_minute', sa.Numeric(precision=10, scale=6), nullable=False, comment='Telephony cost per minute'),
    sa.Column('ai_markup_percentage', sa.Numeric(precision=5, scale=2), nullable=False, comment='Markup % on AI costs'),
    sa.Column('telephony_markup_percentage', sa.Numeric(precision=5, scale=2), nullable=False, comment='Markup % on telephony'),
    sa.Column('final_ai_price_per_minute', sa.Numeric(precision=10, scale=6), nullable=False, comment='Client-facing AI price per minute'),
    sa.Column('final_telephony_price_per_minute', sa.Numeric(precision=10, scale=6), nullable=False, comment='Client-facing telephony price per minute'),
    sa.Column('final_total_price_per_minute', sa.Numeric(precision=10, scale=6), nullable=False, comment='Total client-facing price per minute'),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_pricing_configs_id'), 'pricing_configs', ['id'], unique=False)
    op.create_index(op.f('ix_pricing_configs_tier_id'), 'pricing_configs', ['tier_id'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_pricing_configs_tier_id'), table_name='pricing_configs')
    op.drop_index(op.f('ix_pricing_configs_id'), table_name='pricing_configs')
    op.drop_table('pricing_configs')
