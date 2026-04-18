"""Add recipe_shares table for public link sharing

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-04-18 00:00:01.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c2d3e4f5a6b7"
down_revision: Union[str, Sequence[str], None] = "b1c2d3e4f5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "recipe_shares",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("user_recipe_id", sa.String(36), nullable=False),
        sa.Column("share_token", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_recipe_id"], ["user_recipes.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("share_token"),
    )
    op.create_index("idx_recipe_shares_share_token", "recipe_shares", ["share_token"])
    op.create_index(
        "idx_recipe_shares_user_recipe_id", "recipe_shares", ["user_recipe_id"]
    )


def downgrade() -> None:
    op.drop_index("idx_recipe_shares_user_recipe_id", table_name="recipe_shares")
    op.drop_index("idx_recipe_shares_share_token", table_name="recipe_shares")
    op.drop_table("recipe_shares")
