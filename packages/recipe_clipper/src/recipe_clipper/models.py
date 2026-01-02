"""Data models for recipe clipper."""

from typing import Optional
from pydantic import BaseModel, Field, HttpUrl, AnyUrl, ConfigDict


class ImmutableBaseModel(BaseModel):
    """Base model with immutability enabled."""

    model_config = ConfigDict(frozen=True)


class Ingredient(ImmutableBaseModel):
    """An ingredient in a recipe."""

    name: str = Field(..., description="Ingredient name")
    amount: Optional[str] = Field(None, description="Quantity (e.g., '2', '1/2')")
    unit: Optional[str] = Field(None, description="Unit of measurement (e.g., 'cup', 'tsp')")
    preparation: Optional[str] = Field(
        None, description="Preparation method (e.g., 'chopped', 'diced', 'minced')"
    )
    display_text: Optional[str] = Field(None, description="How the ingredient should be displayed")


class RecipeMetadata(ImmutableBaseModel):
    """Metadata about a recipe."""

    author: Optional[str] = Field(None, description="Recipe author or source")
    servings: Optional[str] = Field(None, description="Number of servings")
    prep_time: Optional[int] = Field(None, description="Prep time in minutes")
    cook_time: Optional[int] = Field(None, description="Cook time in minutes")
    total_time: Optional[int] = Field(None, description="Total time in minutes")
    categories: Optional[list[str]] = Field(None, description="Recipe categories")


class Recipe(ImmutableBaseModel):
    """A complete recipe."""

    title: str = Field(..., description="Recipe title")
    ingredients: list[Ingredient] = Field(default_factory=list, description="List of ingredients")
    instructions: list[str] = Field(default_factory=list, description="Step-by-step instructions")
    source_url: Optional[AnyUrl] = Field(None, description="Source URL (http/https/file)")
    image: Optional[HttpUrl] = Field(None, description="Recipe image URL")
    metadata: Optional[RecipeMetadata] = Field(None, description="Recipe metadata")
