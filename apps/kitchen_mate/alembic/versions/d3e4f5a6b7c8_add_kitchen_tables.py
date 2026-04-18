"""Add kitchen tables for group recipe sharing

Revision ID: d3e4f5a6b7c8
Revises: c2d3e4f5a6b7
Create Date: 2026-04-18 00:00:02.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d3e4f5a6b7c8"
down_revision: Union[str, Sequence[str], None] = "c2d3e4f5a6b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "kitchens",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("created_by", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_kitchens_created_by", "kitchens", ["created_by"])

    op.create_table(
        "kitchen_members",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("kitchen_id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("joined_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["kitchen_id"], ["kitchens.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_kitchen_member", "kitchen_members", ["kitchen_id", "user_id"], unique=True
    )
    op.create_index("idx_kitchen_members_user_id", "kitchen_members", ["user_id"])

    op.create_table(
        "kitchen_invites",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("kitchen_id", sa.String(36), nullable=False),
        sa.Column("invited_email", sa.Text(), nullable=False),
        sa.Column("invited_by", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["kitchen_id"], ["kitchens.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_kitchen_invite", "kitchen_invites", ["kitchen_id", "invited_email"], unique=True
    )
    op.create_index("idx_kitchen_invites_email", "kitchen_invites", ["invited_email"])

    op.create_table(
        "kitchen_recipes",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("kitchen_id", sa.String(36), nullable=False),
        sa.Column("user_recipe_id", sa.String(36), nullable=False),
        sa.Column("shared_by", sa.Text(), nullable=False),
        sa.Column("shared_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["kitchen_id"], ["kitchens.id"]),
        sa.ForeignKeyConstraint(["user_recipe_id"], ["user_recipes.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_kitchen_recipe",
        "kitchen_recipes",
        ["kitchen_id", "user_recipe_id"],
        unique=True,
    )
    op.create_index("idx_kitchen_recipes_kitchen_id", "kitchen_recipes", ["kitchen_id"])


def downgrade() -> None:
    op.drop_index("idx_kitchen_recipes_kitchen_id", table_name="kitchen_recipes")
    op.drop_index("uq_kitchen_recipe", table_name="kitchen_recipes")
    op.drop_table("kitchen_recipes")

    op.drop_index("idx_kitchen_invites_email", table_name="kitchen_invites")
    op.drop_index("uq_kitchen_invite", table_name="kitchen_invites")
    op.drop_table("kitchen_invites")

    op.drop_index("idx_kitchen_members_user_id", table_name="kitchen_members")
    op.drop_index("uq_kitchen_member", table_name="kitchen_members")
    op.drop_table("kitchen_members")

    op.drop_index("idx_kitchens_created_by", table_name="kitchens")
    op.drop_table("kitchens")
