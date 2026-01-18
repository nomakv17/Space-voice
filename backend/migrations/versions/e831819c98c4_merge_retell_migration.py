"""merge_retell_migration

Revision ID: e831819c98c4
Revises: 015_add_retell_voice_provider, 2aeb78a98185
Create Date: 2026-01-17 17:56:07.677729

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e831819c98c4'
down_revision: Union[str, Sequence[str], None] = ('015_add_retell_voice_provider', '2aeb78a98185')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
