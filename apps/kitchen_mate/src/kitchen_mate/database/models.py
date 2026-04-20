"""SQLAlchemy ORM models for kitchen_mate."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    pass


class RecipeModel(Base):
    """Cached parsed recipes from the recipes table."""

    __tablename__ = "recipes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    source_url: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    source_domain: Mapped[str] = mapped_column(Text, nullable=False)
    parsing_method: Mapped[str] = mapped_column(Text, nullable=False)
    recipe_data: Mapped[str] = mapped_column(Text, nullable=False)  # JSON blob
    content_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    parsing_metadata: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON blob
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # Relationship to user recipes
    user_recipes: Mapped[list["UserRecipeModel"]] = relationship(back_populates="source_recipe")

    __table_args__ = (
        Index("idx_recipes_source_url", "source_url"),
        Index("idx_recipes_source_domain", "source_domain"),
        Index("idx_recipes_parsing_method", "parsing_method"),
    )


class UserRecipeModel(Base):
    """User's saved recipes with modifications from the user_recipes table."""

    __tablename__ = "user_recipes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(Text, nullable=False)
    recipe_id: Mapped[str] = mapped_column(String(36), ForeignKey("recipes.id"), nullable=False)
    recipe_data: Mapped[str] = mapped_column(Text, nullable=False)  # JSON blob
    is_modified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array
    source_file_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    thumbnail_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationship to source recipe
    source_recipe: Mapped["RecipeModel"] = relationship(back_populates="user_recipes")

    __table_args__ = (
        Index("idx_user_recipes_user_id", "user_id"),
        Index("idx_user_recipes_recipe_id", "recipe_id"),
        Index("idx_user_recipes_user_created", "user_id", "created_at"),
        Index("idx_user_recipes_deleted", "deleted_at"),
        # Unique constraint: one user can save a recipe once
        Index("uq_user_recipe", "user_id", "recipe_id", unique=True),
    )


class UserModel(Base):
    """Persisted user records synced from JWT claims."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(Text, primary_key=True)  # Supabase UUID
    email: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    __table_args__ = (Index("idx_users_email", "email"),)


class RecipeShareModel(Base):
    """Public share links for individual user recipes."""

    __tablename__ = "recipe_shares"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_recipe_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("user_recipes.id"), nullable=False
    )
    share_token: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user_recipe: Mapped["UserRecipeModel"] = relationship()

    __table_args__ = (
        Index("idx_recipe_shares_share_token", "share_token"),
        Index("idx_recipe_shares_user_recipe_id", "user_recipe_id"),
    )


class KitchenModel(Base):
    """Groups of users that can share recipes."""

    __tablename__ = "kitchens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[str] = mapped_column(Text, nullable=False)  # user_id
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    members: Mapped[list["KitchenMemberModel"]] = relationship(back_populates="kitchen")
    kitchen_recipes: Mapped[list["KitchenRecipeModel"]] = relationship(back_populates="kitchen")

    __table_args__ = (Index("idx_kitchens_created_by", "created_by"),)


class KitchenMemberModel(Base):
    """Members belonging to a kitchen."""

    __tablename__ = "kitchen_members"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    kitchen_id: Mapped[str] = mapped_column(String(36), ForeignKey("kitchens.id"), nullable=False)
    user_id: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(Text, nullable=False)  # "admin" | "member"
    joined_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    kitchen: Mapped["KitchenModel"] = relationship(back_populates="members")

    __table_args__ = (
        Index("uq_kitchen_member", "kitchen_id", "user_id", unique=True),
        Index("idx_kitchen_members_user_id", "user_id"),
    )


class KitchenInviteModel(Base):
    """Pending email invitations to kitchens."""

    __tablename__ = "kitchen_invites"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    kitchen_id: Mapped[str] = mapped_column(String(36), ForeignKey("kitchens.id"), nullable=False)
    invited_email: Mapped[str] = mapped_column(Text, nullable=False)
    invited_by: Mapped[str] = mapped_column(Text, nullable=False)  # user_id
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    __table_args__ = (
        Index("uq_kitchen_invite", "kitchen_id", "invited_email", unique=True),
        Index("idx_kitchen_invites_email", "invited_email"),
    )


class KitchenRecipeModel(Base):
    """Recipes shared with a kitchen."""

    __tablename__ = "kitchen_recipes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    kitchen_id: Mapped[str] = mapped_column(String(36), ForeignKey("kitchens.id"), nullable=False)
    user_recipe_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("user_recipes.id"), nullable=False
    )
    shared_by: Mapped[str] = mapped_column(Text, nullable=False)  # user_id
    shared_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    kitchen: Mapped["KitchenModel"] = relationship(back_populates="kitchen_recipes")
    user_recipe: Mapped["UserRecipeModel"] = relationship()

    __table_args__ = (
        Index("uq_kitchen_recipe", "kitchen_id", "user_recipe_id", unique=True),
        Index("idx_kitchen_recipes_kitchen_id", "kitchen_id"),
    )


class ClipRequestLogModel(Base):
    """Log of every /api/clip request for usage tracking."""

    __tablename__ = "clip_request_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    method: Mapped[str | None] = mapped_column(Text, nullable=True)
    succeeded: Mapped[bool] = mapped_column(Boolean, nullable=False)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON blob

    __table_args__ = (
        Index("idx_clip_request_logs_user_id", "user_id"),
        Index("idx_clip_request_logs_requested_at", "requested_at"),
        Index("idx_clip_request_logs_user_requested", "user_id", "requested_at"),
    )
