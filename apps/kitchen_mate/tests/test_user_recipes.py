"""Tests for user recipe management endpoints."""

from __future__ import annotations

import asyncio
import tempfile
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Generator

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from kitchen_mate.config import Settings, get_settings
from kitchen_mate.database import create_tables, init_database, store_recipe
from kitchen_mate.main import app
from kitchen_mate.schemas import Parser
from recipe_clipper.models import Ingredient, Recipe

if TYPE_CHECKING:
    pass


def create_test_jwt(user_id: str, email: str, secret: str) -> str:
    """Create a test JWT token."""
    payload = {
        "sub": user_id,
        "email": email,
        "aud": "authenticated",
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


@pytest.fixture
def client_with_db() -> Generator[TestClient, None, None]:
    """Create a test client with a temporary database."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    test_settings = Settings(
        cache_enabled=True,
        cache_db_path=db_path,
        supabase_jwt_secret=None,  # Single-tenant mode
        supabase_url=None,  # Ensure single-tenant mode (override .env)
    )
    app.dependency_overrides[get_settings] = lambda: test_settings

    with TestClient(app) as test_client:
        # Re-initialize DB with test path (lifespan used default settings)
        asyncio.run(init_database(db_path))
        asyncio.run(create_tables())
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def client_with_db_multi_tenant() -> Generator[tuple[TestClient, str], None, None]:
    """Create a test client with a temporary database in multi-tenant mode."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    jwt_secret = "test-secret-key-at-least-32-characters-long"
    test_settings = Settings(
        cache_enabled=True,
        cache_db_path=db_path,
        supabase_jwt_secret=jwt_secret,
        supabase_url=None,  # Use HS256 verification (not ES256 JWKS)
    )
    app.dependency_overrides[get_settings] = lambda: test_settings

    with TestClient(app) as test_client:
        # Re-initialize DB with test path (lifespan used default settings)
        asyncio.run(init_database(db_path))
        asyncio.run(create_tables())
        yield test_client, jwt_secret

    app.dependency_overrides.clear()


@pytest.fixture
def sample_recipe() -> Recipe:
    """Create a sample recipe for testing."""
    return Recipe(
        title="Test Chocolate Cake",
        ingredients=[
            Ingredient(name="flour", amount="2", unit="cups"),
            Ingredient(name="sugar", amount="1", unit="cup"),
            Ingredient(name="cocoa", amount="1/2", unit="cup"),
        ],
        instructions=["Mix dry ingredients", "Add wet ingredients", "Bake at 350F"],
        image="https://example.com/cake.jpg",
    )


# =============================================================================
# Single-Tenant Mode Tests
# =============================================================================


def test_list_recipes_empty_single_tenant(client_with_db: TestClient) -> None:
    """Test listing recipes when collection is empty."""
    response = client_with_db.get("/api/me/recipes")

    assert response.status_code == 200
    data = response.json()
    assert data["recipes"] == []
    assert data["next_cursor"] is None
    assert data["has_more"] is False


def test_save_and_list_recipe_single_tenant(
    client_with_db: TestClient, sample_recipe: Recipe
) -> None:
    """Test saving and listing a recipe in single-tenant mode."""
    # Store a recipe in the cache first (simulating a previously clipped recipe)
    cached = asyncio.run(
        store_recipe(
            "https://example.com/cake",
            sample_recipe,
            "abc123hash",
            Parser.recipe_scrapers,
        )
    )

    # Save the recipe to user's collection
    response = client_with_db.post(
        "/api/me/recipes",
        json={
            "url": "https://example.com/cake",
            "tags": ["dessert", "chocolate"],
            "notes": "Family favorite",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["recipe_id"] == cached.id
    assert data["source_url"] == "https://example.com/cake"
    assert data["is_new"] is True

    # List recipes
    response = client_with_db.get("/api/me/recipes")

    assert response.status_code == 200
    data = response.json()
    assert len(data["recipes"]) == 1
    assert data["recipes"][0]["title"] == "Test Chocolate Cake"
    assert data["recipes"][0]["tags"] == ["dessert", "chocolate"]


def test_get_recipe_single_tenant(client_with_db: TestClient, sample_recipe: Recipe) -> None:
    """Test getting a specific recipe."""
    # Store and save recipe
    cached = asyncio.run(
        store_recipe(
            "https://example.com/cake",
            sample_recipe,
            "abc123hash",
            Parser.recipe_scrapers,
        )
    )
    response = client_with_db.post(
        "/api/me/recipes",
        json={"url": "https://example.com/cake"},
    )
    user_recipe_id = response.json()["user_recipe_id"]

    # Get the recipe
    response = client_with_db.get(f"/api/me/recipes/{user_recipe_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == user_recipe_id
    assert data["source_url"] == "https://example.com/cake"
    assert data["recipe"]["title"] == "Test Chocolate Cake"
    assert data["lineage"]["recipe_id"] == cached.id


def test_get_recipe_not_found_single_tenant(client_with_db: TestClient) -> None:
    """Test getting a non-existent recipe returns 404."""
    response = client_with_db.get("/api/me/recipes/nonexistent-id")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_update_recipe_single_tenant(client_with_db: TestClient, sample_recipe: Recipe) -> None:
    """Test updating a recipe."""
    # Store and save recipe
    asyncio.run(store_recipe("https://example.com/cake", sample_recipe, "abc123hash", Parser.recipe_scrapers))
    response = client_with_db.post(
        "/api/me/recipes",
        json={"url": "https://example.com/cake"},
    )
    user_recipe_id = response.json()["user_recipe_id"]

    # Update notes and tags
    response = client_with_db.put(
        f"/api/me/recipes/{user_recipe_id}",
        json={
            "notes": "Reduced sugar by 25%",
            "tags": ["dessert", "healthy"],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == user_recipe_id
    assert data["is_modified"] is False  # Only modified if recipe data changes

    # Verify update
    response = client_with_db.get(f"/api/me/recipes/{user_recipe_id}")
    data = response.json()
    assert data["notes"] == "Reduced sugar by 25%"
    assert data["tags"] == ["dessert", "healthy"]


def test_update_recipe_data_sets_modified(
    client_with_db: TestClient, sample_recipe: Recipe
) -> None:
    """Test that updating recipe data sets is_modified flag."""
    # Store and save recipe
    asyncio.run(store_recipe("https://example.com/cake", sample_recipe, "abc123hash", Parser.recipe_scrapers))
    response = client_with_db.post(
        "/api/me/recipes",
        json={"url": "https://example.com/cake"},
    )
    user_recipe_id = response.json()["user_recipe_id"]

    # Modify the recipe itself
    modified_recipe = sample_recipe.model_copy(update={"title": "My Special Chocolate Cake"})
    response = client_with_db.put(
        f"/api/me/recipes/{user_recipe_id}",
        json={"recipe": modified_recipe.model_dump(mode="json")},
    )

    assert response.status_code == 200
    assert response.json()["is_modified"] is True

    # Verify in listing
    response = client_with_db.get("/api/me/recipes")
    assert response.json()["recipes"][0]["is_modified"] is True


def test_delete_recipe_single_tenant(client_with_db: TestClient, sample_recipe: Recipe) -> None:
    """Test deleting (soft delete) a recipe."""
    # Store and save recipe
    asyncio.run(store_recipe("https://example.com/cake", sample_recipe, "abc123hash", Parser.recipe_scrapers))
    response = client_with_db.post(
        "/api/me/recipes",
        json={"url": "https://example.com/cake"},
    )
    user_recipe_id = response.json()["user_recipe_id"]

    # Delete the recipe
    response = client_with_db.delete(f"/api/me/recipes/{user_recipe_id}")
    assert response.status_code == 204

    # Verify it's no longer in list
    response = client_with_db.get("/api/me/recipes")
    assert len(response.json()["recipes"]) == 0

    # Verify get returns 404
    response = client_with_db.get(f"/api/me/recipes/{user_recipe_id}")
    assert response.status_code == 404


def test_delete_recipe_not_found(client_with_db: TestClient) -> None:
    """Test deleting a non-existent recipe returns 404."""
    response = client_with_db.delete("/api/me/recipes/nonexistent-id")
    assert response.status_code == 404


def test_save_recipe_already_saved(client_with_db: TestClient, sample_recipe: Recipe) -> None:
    """Test saving a recipe that's already saved returns existing."""
    # Store and save recipe
    asyncio.run(store_recipe("https://example.com/cake", sample_recipe, "abc123hash", Parser.recipe_scrapers))
    response = client_with_db.post(
        "/api/me/recipes",
        json={"url": "https://example.com/cake"},
    )
    first_id = response.json()["user_recipe_id"]
    assert response.json()["is_new"] is True

    # Try to save again
    response = client_with_db.post(
        "/api/me/recipes",
        json={"url": "https://example.com/cake"},
    )
    assert response.status_code == 201
    assert response.json()["user_recipe_id"] == first_id
    assert response.json()["is_new"] is False


def test_save_recipe_restores_deleted(client_with_db: TestClient, sample_recipe: Recipe) -> None:
    """Test saving a deleted recipe restores it."""
    # Store, save, and delete recipe
    asyncio.run(store_recipe("https://example.com/cake", sample_recipe, "abc123hash", Parser.recipe_scrapers))
    response = client_with_db.post(
        "/api/me/recipes",
        json={"url": "https://example.com/cake"},
    )
    user_recipe_id = response.json()["user_recipe_id"]
    client_with_db.delete(f"/api/me/recipes/{user_recipe_id}")

    # Save again - should restore
    response = client_with_db.post(
        "/api/me/recipes",
        json={"url": "https://example.com/cake"},
    )
    assert response.status_code == 201
    assert response.json()["user_recipe_id"] == user_recipe_id
    assert response.json()["is_new"] is False

    # Should be back in list
    response = client_with_db.get("/api/me/recipes")
    assert len(response.json()["recipes"]) == 1


# =============================================================================
# Multi-Tenant Mode Tests
# =============================================================================


def test_list_recipes_requires_auth_multi_tenant(
    client_with_db_multi_tenant: tuple[TestClient, str],
) -> None:
    """Test that listing recipes requires authentication in multi-tenant mode."""
    client, _ = client_with_db_multi_tenant
    response = client.get("/api/me/recipes")

    assert response.status_code == 401
    assert "not authenticated" in response.json()["detail"].lower()


def test_save_recipe_requires_auth_multi_tenant(
    client_with_db_multi_tenant: tuple[TestClient, str],
) -> None:
    """Test that saving recipes requires authentication in multi-tenant mode."""
    client, _ = client_with_db_multi_tenant
    response = client.post(
        "/api/me/recipes",
        json={"url": "https://example.com/cake"},
    )

    assert response.status_code == 401


def test_save_and_list_recipe_multi_tenant(
    client_with_db_multi_tenant: tuple[TestClient, str],
    sample_recipe: Recipe,
) -> None:
    """Test saving and listing recipes with authentication."""
    client, jwt_secret = client_with_db_multi_tenant
    token = create_test_jwt("user-123", "test@example.com", jwt_secret)

    # Store a recipe in the cache first
    _ = asyncio.run(
        store_recipe(
            "https://example.com/cake",
            sample_recipe,
            "abc123hash",
            Parser.recipe_scrapers,
        )
    )

    # Save with auth
    response = client.post(
        "/api/me/recipes",
        json={"url": "https://example.com/cake", "tags": ["dessert"]},
        cookies={"access_token": token},
    )

    assert response.status_code == 201
    assert response.json()["is_new"] is True

    # List with auth
    response = client.get("/api/me/recipes", cookies={"access_token": token})

    assert response.status_code == 200
    assert len(response.json()["recipes"]) == 1


def test_users_have_separate_collections_multi_tenant(
    client_with_db_multi_tenant: tuple[TestClient, str],
    sample_recipe: Recipe,
) -> None:
    """Test that different users have separate recipe collections."""
    client, jwt_secret = client_with_db_multi_tenant

    # Store recipe
    asyncio.run(store_recipe("https://example.com/cake", sample_recipe, "abc123hash", Parser.recipe_scrapers))

    # User 1 saves recipe
    token1 = create_test_jwt("user-1", "user1@example.com", jwt_secret)
    response = client.post(
        "/api/me/recipes",
        json={"url": "https://example.com/cake"},
        cookies={"access_token": token1},
    )
    assert response.status_code == 201

    # User 2 should have empty collection
    token2 = create_test_jwt("user-2", "user2@example.com", jwt_secret)
    response = client.get("/api/me/recipes", cookies={"access_token": token2})
    assert response.status_code == 200
    assert len(response.json()["recipes"]) == 0

    # User 2 saves same recipe - should work (different user)
    response = client.post(
        "/api/me/recipes",
        json={"url": "https://example.com/cake"},
        cookies={"access_token": token2},
    )
    assert response.status_code == 201
    assert response.json()["is_new"] is True  # New for this user

    # Both users now have 1 recipe each
    response = client.get("/api/me/recipes", cookies={"access_token": token1})
    assert len(response.json()["recipes"]) == 1

    response = client.get("/api/me/recipes", cookies={"access_token": token2})
    assert len(response.json()["recipes"]) == 1


def test_user_cannot_access_other_user_recipe_multi_tenant(
    client_with_db_multi_tenant: tuple[TestClient, str],
    sample_recipe: Recipe,
) -> None:
    """Test that users cannot access other users' recipes."""
    client, jwt_secret = client_with_db_multi_tenant

    # Store recipe
    asyncio.run(store_recipe("https://example.com/cake", sample_recipe, "abc123hash", Parser.recipe_scrapers))

    # User 1 saves recipe
    token1 = create_test_jwt("user-1", "user1@example.com", jwt_secret)
    response = client.post(
        "/api/me/recipes",
        json={"url": "https://example.com/cake"},
        cookies={"access_token": token1},
    )
    user1_recipe_id = response.json()["user_recipe_id"]

    # User 2 tries to access user 1's recipe - should get 404
    token2 = create_test_jwt("user-2", "user2@example.com", jwt_secret)
    response = client.get(
        f"/api/me/recipes/{user1_recipe_id}",
        cookies={"access_token": token2},
    )
    assert response.status_code == 404

    # User 2 tries to update user 1's recipe - should get 404
    response = client.put(
        f"/api/me/recipes/{user1_recipe_id}",
        json={"notes": "Hacked!"},
        cookies={"access_token": token2},
    )
    assert response.status_code == 404

    # User 2 tries to delete user 1's recipe - should get 404
    response = client.delete(
        f"/api/me/recipes/{user1_recipe_id}",
        cookies={"access_token": token2},
    )
    assert response.status_code == 404


# =============================================================================
# Pagination Tests
# =============================================================================


def test_list_recipes_pagination(client_with_db: TestClient, sample_recipe: Recipe) -> None:
    """Test recipe listing pagination."""
    # Create 5 recipes
    for i in range(5):
        recipe = sample_recipe.model_copy(update={"title": f"Recipe {i}"})
        asyncio.run(store_recipe(f"https://example.com/recipe{i}", recipe, f"hash{i}", Parser.recipe_scrapers))
        client_with_db.post("/api/me/recipes", json={"url": f"https://example.com/recipe{i}"})

    # Get first page (limit 2)
    response = client_with_db.get("/api/me/recipes?limit=2")
    data = response.json()
    assert len(data["recipes"]) == 2
    assert data["has_more"] is True
    assert data["next_cursor"] is not None

    # Get second page
    cursor = data["next_cursor"]
    response = client_with_db.get(f"/api/me/recipes?limit=2&cursor={cursor}")
    data = response.json()
    assert len(data["recipes"]) == 2
    assert data["has_more"] is True

    # Get third page
    cursor = data["next_cursor"]
    response = client_with_db.get(f"/api/me/recipes?limit=2&cursor={cursor}")
    data = response.json()
    assert len(data["recipes"]) == 1
    assert data["has_more"] is False
    assert data["next_cursor"] is None


def test_list_recipes_filter_by_modified(client_with_db: TestClient, sample_recipe: Recipe) -> None:
    """Test filtering recipes by modified status."""
    # Create 2 recipes
    asyncio.run(store_recipe("https://example.com/recipe1", sample_recipe, "hash1", Parser.recipe_scrapers))
    asyncio.run(store_recipe("https://example.com/recipe2", sample_recipe, "hash2", Parser.recipe_scrapers))

    response = client_with_db.post("/api/me/recipes", json={"url": "https://example.com/recipe1"})
    id1 = response.json()["user_recipe_id"]
    client_with_db.post("/api/me/recipes", json={"url": "https://example.com/recipe2"})

    # Modify first recipe
    modified = sample_recipe.model_copy(update={"title": "Modified"})
    client_with_db.put(f"/api/me/recipes/{id1}", json={"recipe": modified.model_dump(mode="json")})

    # Filter by modified
    response = client_with_db.get("/api/me/recipes?modified_only=true")
    data = response.json()
    assert len(data["recipes"]) == 1
    assert data["recipes"][0]["is_modified"] is True
