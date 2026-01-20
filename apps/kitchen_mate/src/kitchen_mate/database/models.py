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
