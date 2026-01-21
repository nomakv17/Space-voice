"""add_client_id_field

Revision ID: 95e55d624d3e
Revises: 4238d067155a
Create Date: 2026-01-20 22:42:50.883350

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '95e55d624d3e'
down_revision: Union[str, Sequence[str], None] = '4238d067155a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add client_id column for client login
    op.add_column('users', sa.Column('client_id', sa.String(length=50), nullable=True))
    op.create_index(op.f('ix_users_client_id'), 'users', ['client_id'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_users_client_id'), table_name='users')
    op.drop_column('users', 'client_id')
