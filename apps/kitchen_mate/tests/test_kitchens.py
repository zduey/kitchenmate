"""Tests for kitchen endpoints."""

from __future__ import annotations

import asyncio
import tempfile
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Generator

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from kitchen_mate.config import Settings, get_settings
from kitchen_mate.database import (
    close_database,
    create_tables,
    init_database,
    save_user_recipe,
    store_recipe,
)
from kitchen_mate.main import app
from kitchen_mate.schemas import Parser
from kitchen_mate.storage import get_storage
from recipe_clipper.models import Ingredient, Recipe

if TYPE_CHECKING:
    pass


def create_test_jwt(user_id: str, email: str, secret: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "aud": "authenticated",
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


class FakeStorage:
    def __init__(self) -> None:
        self.uploaded: list[str] = []
        self.deleted: list[str] = []

    async def upload(self, key: str, content: bytes, content_type: str) -> None:
        self.uploaded.append(key)

    def get_url(self, key: str) -> str:
        return f"https://storage.test/{key}"

    async def delete(self, key: str) -> None:
        self.deleted.append(key)


@pytest.fixture
def kitchen_client() -> Generator[tuple[TestClient, str, FakeStorage], None, None]:
    """Test client in multi-tenant mode with fake storage and a real database."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    jwt_secret = "test-secret-key-at-least-32-characters-long"
    test_settings = Settings(
        cache_enabled=True,
        cache_db_path=db_path,
        supabase_jwt_secret=jwt_secret,
        supabase_url=None,
    )
    fake_storage = FakeStorage()
    app.dependency_overrides[get_settings] = lambda: test_settings
    app.dependency_overrides[get_storage] = lambda: fake_storage

    with TestClient(app) as test_client:
        asyncio.run(init_database(db_path))
        asyncio.run(create_tables())
        yield test_client, jwt_secret, fake_storage

    app.dependency_overrides.clear()
    asyncio.run(close_database())


@pytest.fixture
def sample_recipe() -> Recipe:
    return Recipe(
        title="Test Pasta",
        ingredients=[Ingredient(name="pasta", amount="200", unit="g")],
        instructions=["Boil pasta"],
        image="https://example.com/pasta-original.jpg",
    )


def test_kitchen_recipe_list_uses_thumbnail_when_present(
    kitchen_client: tuple[TestClient, str, FakeStorage],
    sample_recipe: Recipe,
) -> None:
    """Kitchen recipe list should show the uploaded thumbnail URL, not the original recipe image."""
    client, jwt_secret, fake_storage = kitchen_client
    user_id = "user-kitchen-thumb-test"
    email = "kitchen-thumb@example.com"
    token = create_test_jwt(user_id, email, jwt_secret)
    cookies = {"access_token": token}

    # Register the user
    client.get("/api/auth/me", cookies=cookies)

    cached = asyncio.run(
        store_recipe(
            "https://example.com/pasta",
            sample_recipe,
            "abc123hash",
            Parser.recipe_scrapers,
        )
    )
    thumbnail_key = f"users/{user_id}/recipes/some-id/thumbnail.jpg"
    saved, _ = asyncio.run(
        save_user_recipe(
            user_id=user_id,
            recipe_id=cached.id,
            recipe_data=sample_recipe,
            thumbnail_key=thumbnail_key,
        )
    )

    # Create a kitchen
    response = client.post("/api/kitchens", json={"name": "Test Kitchen"}, cookies=cookies)
    assert response.status_code == 201
    kitchen_id = response.json()["id"]

    # Share the recipe — the response should already resolve the thumbnail
    response = client.post(
        f"/api/kitchens/{kitchen_id}/recipes",
        json={"user_recipe_id": saved.id},
        cookies=cookies,
    )
    assert response.status_code == 201
    assert response.json()["image_url"] == fake_storage.get_url(thumbnail_key)

    # List kitchen recipes — this was the broken path before the fix
    response = client.get(f"/api/kitchens/{kitchen_id}/recipes", cookies=cookies)
    assert response.status_code == 200
    recipes = response.json()["recipes"]
    assert len(recipes) == 1
    assert recipes[0]["image_url"] == fake_storage.get_url(thumbnail_key)
    assert recipes[0]["image_url"] != str(sample_recipe.image)


def test_kitchen_recipe_list_falls_back_to_original_image(
    kitchen_client: tuple[TestClient, str, FakeStorage],
    sample_recipe: Recipe,
) -> None:
    """Kitchen recipe list should fall back to original recipe image when no thumbnail is set."""
    client, jwt_secret, fake_storage = kitchen_client
    user_id = "user-kitchen-noThumb-test"
    email = "kitchen-nothumb@example.com"
    token = create_test_jwt(user_id, email, jwt_secret)
    cookies = {"access_token": token}

    client.get("/api/auth/me", cookies=cookies)

    cached = asyncio.run(
        store_recipe(
            "https://example.com/pasta",
            sample_recipe,
            "abc123hash",
            Parser.recipe_scrapers,
        )
    )
    saved, _ = asyncio.run(
        save_user_recipe(
            user_id=user_id,
            recipe_id=cached.id,
            recipe_data=sample_recipe,
        )
    )

    response = client.post("/api/kitchens", json={"name": "Test Kitchen 2"}, cookies=cookies)
    assert response.status_code == 201
    kitchen_id = response.json()["id"]

    response = client.post(
        f"/api/kitchens/{kitchen_id}/recipes",
        json={"user_recipe_id": saved.id},
        cookies=cookies,
    )
    assert response.status_code == 201

    response = client.get(f"/api/kitchens/{kitchen_id}/recipes", cookies=cookies)
    assert response.status_code == 200
    recipes = response.json()["recipes"]
    assert len(recipes) == 1
    assert recipes[0]["image_url"] == str(sample_recipe.image)


# =============================================================================
# GET /kitchens/{kitchen_id}/recipes/{kitchen_recipe_id}
# =============================================================================


def _setup_kitchen_with_shared_recipe(
    client: "TestClient",
    jwt_secret: str,
    sample_recipe: Recipe,
    owner_user_id: str,
    owner_email: str,
) -> tuple[str, str, str]:
    """Create a kitchen, save and share a recipe as owner. Returns (kitchen_id, kitchen_recipe_id, user_recipe_id)."""
    owner_token = create_test_jwt(owner_user_id, owner_email, jwt_secret)
    owner_cookies = {"access_token": owner_token}

    client.get("/api/auth/me", cookies=owner_cookies)

    cached = asyncio.run(
        store_recipe(
            "https://example.com/pasta",
            sample_recipe,
            "abc123hash",
            Parser.recipe_scrapers,
        )
    )
    saved, _ = asyncio.run(
        save_user_recipe(
            user_id=owner_user_id,
            recipe_id=cached.id,
            recipe_data=sample_recipe,
        )
    )

    resp = client.post("/api/kitchens", json={"name": "Detail Test Kitchen"}, cookies=owner_cookies)
    assert resp.status_code == 201
    kitchen_id = resp.json()["id"]

    resp = client.post(
        f"/api/kitchens/{kitchen_id}/recipes",
        json={"user_recipe_id": saved.id},
        cookies=owner_cookies,
    )
    assert resp.status_code == 201
    kitchen_recipe_id = resp.json()["id"]

    return kitchen_id, kitchen_recipe_id, saved.id


def test_get_kitchen_recipe_owner_can_view(
    kitchen_client: tuple["TestClient", str, FakeStorage],
    sample_recipe: Recipe,
) -> None:
    """The member who shared a recipe can view its full detail."""
    client, jwt_secret, _ = kitchen_client
    owner_id = "owner-view-own"
    owner_email = "owner-view-own@example.com"

    kitchen_id, kitchen_recipe_id, _ = _setup_kitchen_with_shared_recipe(
        client, jwt_secret, sample_recipe, owner_id, owner_email
    )

    owner_cookies = {"access_token": create_test_jwt(owner_id, owner_email, jwt_secret)}
    resp = client.get(
        f"/api/kitchens/{kitchen_id}/recipes/{kitchen_recipe_id}",
        cookies=owner_cookies,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["recipe"]["title"] == sample_recipe.title


def test_get_kitchen_recipe_non_owner_member_can_view(
    kitchen_client: tuple["TestClient", str, FakeStorage],
    sample_recipe: Recipe,
) -> None:
    """A kitchen member who did not share the recipe can still view its full detail."""
    client, jwt_secret, _ = kitchen_client
    owner_id = "owner-non-owner-test"
    owner_email = "owner-non-owner@example.com"
    member_id = "member-non-owner-test"
    member_email = "member-non-owner@example.com"

    kitchen_id, kitchen_recipe_id, _ = _setup_kitchen_with_shared_recipe(
        client, jwt_secret, sample_recipe, owner_id, owner_email
    )

    # Add second member
    owner_cookies = {"access_token": create_test_jwt(owner_id, owner_email, jwt_secret)}
    client.get(
        "/api/auth/me",
        cookies={"access_token": create_test_jwt(member_id, member_email, jwt_secret)},
    )
    resp = client.post(
        f"/api/kitchens/{kitchen_id}/members",
        json={"email": member_email},
        cookies=owner_cookies,
    )
    assert resp.status_code == 200

    member_cookies = {"access_token": create_test_jwt(member_id, member_email, jwt_secret)}
    resp = client.get(
        f"/api/kitchens/{kitchen_id}/recipes/{kitchen_recipe_id}",
        cookies=member_cookies,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["recipe"]["title"] == sample_recipe.title


def test_get_kitchen_recipe_non_member_gets_403(
    kitchen_client: tuple["TestClient", str, FakeStorage],
    sample_recipe: Recipe,
) -> None:
    """A user who is not a kitchen member cannot view the recipe detail."""
    client, jwt_secret, _ = kitchen_client
    owner_id = "owner-non-member-test"
    owner_email = "owner-non-member@example.com"
    outsider_id = "outsider-non-member-test"
    outsider_email = "outsider-non-member@example.com"

    kitchen_id, kitchen_recipe_id, _ = _setup_kitchen_with_shared_recipe(
        client, jwt_secret, sample_recipe, owner_id, owner_email
    )

    client.get(
        "/api/auth/me",
        cookies={"access_token": create_test_jwt(outsider_id, outsider_email, jwt_secret)},
    )
    outsider_cookies = {"access_token": create_test_jwt(outsider_id, outsider_email, jwt_secret)}
    resp = client.get(
        f"/api/kitchens/{kitchen_id}/recipes/{kitchen_recipe_id}",
        cookies=outsider_cookies,
    )
    assert resp.status_code == 403


def test_get_kitchen_recipe_not_found(
    kitchen_client: tuple["TestClient", str, FakeStorage],
    sample_recipe: Recipe,
) -> None:
    """A valid kitchen member gets 404 for a non-existent kitchen_recipe_id."""
    client, jwt_secret, _ = kitchen_client
    owner_id = "owner-not-found-test"
    owner_email = "owner-not-found@example.com"

    kitchen_id, _, _ = _setup_kitchen_with_shared_recipe(
        client, jwt_secret, sample_recipe, owner_id, owner_email
    )

    owner_cookies = {"access_token": create_test_jwt(owner_id, owner_email, jwt_secret)}
    resp = client.get(
        f"/api/kitchens/{kitchen_id}/recipes/nonexistent-id",
        cookies=owner_cookies,
    )
    assert resp.status_code == 404


def test_get_kitchen_recipe_unauthenticated_gets_401(
    kitchen_client: tuple["TestClient", str, FakeStorage],
    sample_recipe: Recipe,
) -> None:
    """An unauthenticated request to view a kitchen recipe is rejected."""
    client, jwt_secret, _ = kitchen_client
    owner_id = "owner-unauth-test"
    owner_email = "owner-unauth@example.com"

    kitchen_id, kitchen_recipe_id, _ = _setup_kitchen_with_shared_recipe(
        client, jwt_secret, sample_recipe, owner_id, owner_email
    )

    resp = client.get(f"/api/kitchens/{kitchen_id}/recipes/{kitchen_recipe_id}")
    assert resp.status_code in (401, 403)
