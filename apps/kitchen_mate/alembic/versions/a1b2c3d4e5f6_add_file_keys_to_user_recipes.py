"""Add source_file_key and thumbnail_key to user_recipes

Revision ID: a1b2c3d4e5f6
Revises: ede6c69f37ad
Create Date: 2026-04-11 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "ede6c69f37ad"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add file storage key columns to user_recipes."""
    op.add_column("user_recipes", sa.Column("source_file_key", sa.Text(), nullable=True))
    op.add_column("user_recipes", sa.Column("thumbnail_key", sa.Text(), nullable=True))


def downgrade() -> None:
    """Remove file storage key columns from user_recipes."""
    op.drop_column("user_recipes", "thumbnail_key")
    op.drop_column("user_recipes", "source_file_key")
