"""add_revenue_fields_to_call_records

Revision ID: d5d6c771f2f0
Revises: 017_add_access_tokens
Create Date: 2026-01-28 16:29:48.347730

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'd5d6c771f2f0'
down_revision: Union[str, Sequence[str], None] = '017_add_access_tokens'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add revenue tracking fields to call_records and drop sim_* tables."""
    # Add revenue fields to call_records
    op.add_column('call_records', sa.Column('pricing_tier_id', sa.String(length=50), nullable=True, comment='Pricing tier used for this call'))
    op.add_column('call_records', sa.Column('price_per_minute', sa.Numeric(precision=10, scale=4), nullable=True, comment='Price per minute at time of call'))
    op.add_column('call_records', sa.Column('revenue_usd', sa.Numeric(precision=10, scale=4), nullable=True, comment='Revenue generated from this call'))
    op.add_column('call_records', sa.Column('cost_usd', sa.Numeric(precision=10, scale=4), nullable=True, comment='Cost to SpaceVoice for this call'))

    # Drop sv_internal tables (no longer needed - revenue from call records)
    op.execute("DROP TABLE IF EXISTS sim_income_snapshots CASCADE")
    op.execute("DROP TABLE IF EXISTS sim_client_history CASCADE")
    op.execute("DROP TABLE IF EXISTS sim_clients CASCADE")


def downgrade() -> None:
    """Remove revenue fields from call_records."""
    op.drop_column('call_records', 'cost_usd')
    op.drop_column('call_records', 'revenue_usd')
    op.drop_column('call_records', 'price_per_minute')
    op.drop_column('call_records', 'pricing_tier_id')
    # Note: sim_* tables are not recreated in downgrade
