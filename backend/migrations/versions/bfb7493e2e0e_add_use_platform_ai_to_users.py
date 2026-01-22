"""add_use_platform_ai_to_users

Revision ID: bfb7493e2e0e
Revises: 95e55d624d3e
Create Date: 2026-01-21 21:02:40.220268

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'bfb7493e2e0e'
down_revision: Union[str, Sequence[str], None] = '95e55d624d3e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add use_platform_ai column with server_default for existing rows
    op.add_column('users', sa.Column('use_platform_ai', sa.Boolean(), nullable=False, server_default='true'))
    # Remove server_default after column is created
    op.alter_column('users', 'use_platform_ai', server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'use_platform_ai')
