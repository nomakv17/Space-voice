"""add_user_onboarding_fields

Revision ID: 4238d067155a
Revises: e831819c98c4
Create Date: 2026-01-20 21:58:54.328616

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '4238d067155a'
down_revision: Union[str, Sequence[str], None] = 'e831819c98c4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add onboarding fields to users table
    op.add_column('users', sa.Column('onboarding_completed', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('users', sa.Column('onboarding_step', sa.Integer(), server_default='1', nullable=False))
    op.add_column('users', sa.Column('company_name', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('company_size', sa.String(length=50), nullable=True))
    op.add_column('users', sa.Column('industry', sa.String(length=100), nullable=True))
    op.add_column('users', sa.Column('phone_number', sa.String(length=50), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove onboarding fields from users table
    op.drop_column('users', 'phone_number')
    op.drop_column('users', 'industry')
    op.drop_column('users', 'company_size')
    op.drop_column('users', 'company_name')
    op.drop_column('users', 'onboarding_step')
    op.drop_column('users', 'onboarding_completed')
