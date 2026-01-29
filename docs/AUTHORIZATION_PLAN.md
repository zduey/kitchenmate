# Authorization System Plan: Tier-Based Permissions

This document outlines the plan for adding tier-based authorization to KitchenMate.

## Overview

| Component | Technology |
|-----------|------------|
| Authentication | Supabase (existing) |
| Authorization | Simple tier-based permission checks |
| Tier Storage | Config (short-term) → Supabase user metadata (with Stripe) |
| User Tiers | free, pro |

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Authorization library | None (simple dict-based) | Only 2 tiers with static permissions; Casbin is overkill |
| Pro subscription source | Hardcoded user list → Stripe webhook | Simple start, proper payment later |
| Tier storage (short-term) | Environment variable | No DB changes needed, easy to configure |
| Tier storage (long-term) | Supabase user metadata | JWT claims avoid DB lookup, Stripe webhook integration |
| Expiration handling | Distinct messaging for expired vs never-upgraded | Better UX for lapsed subscribers |
| Single-tenant default | Pro tier (full access) | Maintains current behavior |
| Admin interface | Supabase dashboard (long-term) | No custom admin API needed |

## User Tiers and Permissions

### Free Tier

- Clip recipes from URL (no AI fallback)
- Save recipes to collection
- Create recipes manually
- Edit saved recipes
- List and delete saved recipes

### Pro Tier

Everything in Free tier, plus:

- Clip from webpage with AI fallback
- Clip from uploaded file (images, PDFs)
- Future pro-only features

## Permission Model

Simple dictionary-based permissions (no external library needed):

```python
# authorization/permissions.py
from enum import StrEnum

class Tier(StrEnum):
    FREE = "free"
    PRO = "pro"

class Permission(StrEnum):
    CLIP_BASIC = "clip_basic"
    CLIP_AI = "clip_ai"
    CLIP_UPLOAD = "clip_upload"
    RECIPE_SAVE = "recipe_save"
    RECIPE_CREATE = "recipe_create"
    RECIPE_EDIT = "recipe_edit"
    RECIPE_LIST = "recipe_list"
    RECIPE_DELETE = "recipe_delete"

TIER_PERMISSIONS: dict[Tier, set[Permission]] = {
    Tier.FREE: {
        Permission.CLIP_BASIC,
        Permission.RECIPE_SAVE,
        Permission.RECIPE_CREATE,
        Permission.RECIPE_EDIT,
        Permission.RECIPE_LIST,
        Permission.RECIPE_DELETE,
    },
    Tier.PRO: {
        Permission.CLIP_BASIC,
        Permission.CLIP_AI,
        Permission.CLIP_UPLOAD,
        Permission.RECIPE_SAVE,
        Permission.RECIPE_CREATE,
        Permission.RECIPE_EDIT,
        Permission.RECIPE_LIST,
        Permission.RECIPE_DELETE,
    },
}

def has_permission(tier: Tier, permission: Permission) -> bool:
    """Check if a tier has a specific permission."""
    return permission in TIER_PERMISSIONS.get(tier, set())
```

## Module Structure

```
apps/kitchen_mate/src/kitchen_mate/
├── authorization/
│   ├── __init__.py           # Exports: Permission, Tier, has_permission, require_permission
│   ├── permissions.py        # Permission/Tier enums, TIER_PERMISSIONS dict
│   ├── dependencies.py       # FastAPI dependencies (get_user_tier, require_permission)
│   └── exceptions.py         # UpgradeRequiredError, SubscriptionExpiredError
```

## Implementation Phases

### Phase 1: Config-Based Pro Users (Short-Term)

Replace IP allowlist with user ID allowlist. No database changes required.

#### Configuration

```python
# config.py
class Settings(BaseSettings):
    # ... existing settings ...

    # Replace LLM_ALLOWED_IPS with:
    pro_user_ids: set[str] = set()  # Comma-separated in env var

    @field_validator("pro_user_ids", mode="before")
    @classmethod
    def parse_pro_user_ids(cls, v: str | set[str]) -> set[str]:
        if isinstance(v, str):
            return {uid.strip() for uid in v.split(",") if uid.strip()}
        return v
```

#### Environment Variable

```bash
# Comma-separated Supabase user IDs
PRO_USER_IDS=uuid-1,uuid-2,uuid-3
```

#### Get User Tier Dependency

```python
# authorization/dependencies.py
from datetime import datetime, timezone

async def get_user_tier(
    user: User = Depends(get_user),
    settings: Settings = Depends(get_settings),
) -> Tier:
    """
    Determine user's tier.

    Priority:
    1. Single-tenant mode → Pro
    2. User ID in PRO_USER_IDS → Pro
    3. Default → Free
    """
    if settings.is_single_tenant:
        return Tier.PRO

    if user.id in settings.pro_user_ids:
        return Tier.PRO

    return Tier.FREE
```

### Phase 2: Supabase User Metadata (With Stripe)

Store tier in Supabase user metadata, included in JWT claims.

#### Supabase User Metadata Schema

```json
{
  "app_metadata": {
    "tier": "pro",
    "tier_expires_at": "2025-02-01T00:00:00Z",
    "stripe_customer_id": "cus_xxx",
    "stripe_subscription_id": "sub_xxx"
  }
}
```

#### Updated Get User Tier Dependency

```python
# authorization/dependencies.py
from datetime import datetime, timezone

@dataclass
class TierInfo:
    tier: Tier
    expires_at: datetime | None = None
    is_expired: bool = False

async def get_tier_info(
    user: User = Depends(get_user),
    settings: Settings = Depends(get_settings),
) -> TierInfo:
    """
    Determine user's tier with expiration info.

    Priority:
    1. Single-tenant mode → Pro (never expires)
    2. Config-based pro list → Pro (never expires, for manual overrides)
    3. Supabase metadata → Check tier and expiration
    4. Default → Free
    """
    if settings.is_single_tenant:
        return TierInfo(tier=Tier.PRO)

    # Manual override via config (useful for testing, special cases)
    if user.id in settings.pro_user_ids:
        return TierInfo(tier=Tier.PRO)

    # Check Supabase user metadata (from JWT claims)
    metadata = user.app_metadata or {}
    tier_str = metadata.get("tier", "free")
    expires_at_str = metadata.get("tier_expires_at")

    if tier_str != "pro":
        return TierInfo(tier=Tier.FREE)

    # Pro tier - check expiration
    if expires_at_str:
        expires_at = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
        if expires_at < datetime.now(timezone.utc):
            return TierInfo(tier=Tier.FREE, expires_at=expires_at, is_expired=True)
        return TierInfo(tier=Tier.PRO, expires_at=expires_at)

    return TierInfo(tier=Tier.PRO)
```

#### User Model Extension

```python
# auth.py - extend User dataclass
@dataclass
class User:
    id: str
    email: str | None = None
    app_metadata: dict | None = None  # Add this field
```

Parse `app_metadata` from JWT claims in `get_user` dependency.

## Custom Exceptions

```python
# authorization/exceptions.py
from fastapi import HTTPException, status

class UpgradeRequiredError(HTTPException):
    """Raised when a free user attempts to use a pro feature."""

    def __init__(self, feature: str):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "message": f"This feature requires a Pro subscription.",
                "error_code": "upgrade_required",
                "required_tier": "pro",
                "feature": feature,
            },
        )

class SubscriptionExpiredError(HTTPException):
    """Raised when an expired pro user attempts to use a pro feature."""

    def __init__(self, feature: str, expired_at: datetime):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "message": "Your Pro subscription has expired.",
                "error_code": "subscription_expired",
                "required_tier": "pro",
                "feature": feature,
                "expired_at": expired_at.isoformat(),
            },
        )
```

## FastAPI Dependencies

### require_permission

Dependency factory for protecting entire routes:

```python
# authorization/dependencies.py

def require_permission(permission: Permission):
    """
    Dependency factory that ensures user has the required permission.

    Usage:
        @router.post("/clip/upload")
        async def clip_upload(
            user: User = Depends(require_permission(Permission.CLIP_UPLOAD)),
        ):
            ...
    """
    async def check_permission(
        tier_info: TierInfo = Depends(get_tier_info),
        user: User = Depends(get_user),
    ) -> User:
        if has_permission(tier_info.tier, permission):
            return user

        if tier_info.is_expired:
            raise SubscriptionExpiredError(
                feature=permission.value,
                expired_at=tier_info.expires_at,
            )

        raise UpgradeRequiredError(feature=permission.value)

    return check_permission
```

### check_permission

For conditional feature checks within a route:

```python
# authorization/dependencies.py

async def check_permission_soft(
    permission: Permission,
    tier_info: TierInfo,
) -> tuple[bool, str | None]:
    """
    Check permission without raising. Returns (allowed, error_code).

    error_code is None if allowed, "upgrade_required" or "subscription_expired" otherwise.
    """
    if has_permission(tier_info.tier, permission):
        return True, None

    if tier_info.is_expired:
        return False, "subscription_expired"

    return False, "upgrade_required"
```

## Route Integration Examples

### Protected Route (Upload)

```python
# routes/clip.py

@router.post("/clip/upload")
async def clip_upload(
    file: UploadFile,
    user: User = Depends(require_permission(Permission.CLIP_UPLOAD)),
):
    # Only pro users reach here
    ...
```

### Conditional Feature (AI Fallback in /clip)

```python
# routes/clip.py

@router.post("/clip")
async def clip(
    request: ClipRequest,
    user: User = Depends(get_user),
    tier_info: TierInfo = Depends(get_tier_info),
):
    # Check if user can use AI fallback
    can_use_ai, error_code = await check_permission_soft(
        Permission.CLIP_AI,
        tier_info,
    )

    if request.use_llm_fallback and not can_use_ai:
        if error_code == "subscription_expired":
            raise SubscriptionExpiredError(
                feature=Permission.CLIP_AI.value,
                expired_at=tier_info.expires_at,
            )
        raise UpgradeRequiredError(feature=Permission.CLIP_AI.value)

    # Proceed with clipping
    effective_use_llm = request.use_llm_fallback and can_use_ai
    ...
```

## Error Response Format

All authorization errors return structured JSON for frontend handling:

### Upgrade Required (never had pro)

```json
{
    "detail": {
        "message": "This feature requires a Pro subscription.",
        "error_code": "upgrade_required",
        "required_tier": "pro",
        "feature": "clip_ai"
    }
}
```

### Subscription Expired (was pro, now expired)

```json
{
    "detail": {
        "message": "Your Pro subscription has expired.",
        "error_code": "subscription_expired",
        "required_tier": "pro",
        "feature": "clip_ai",
        "expired_at": "2025-01-15T00:00:00+00:00"
    }
}
```

## Frontend Integration

### Types

```typescript
// types/auth.ts

type Tier = "free" | "pro";

interface User {
  id: string;
  email?: string;
  tier: Tier;
  tierExpiresAt?: string;  // ISO datetime
}

type AuthErrorCode = "upgrade_required" | "subscription_expired";

interface AuthErrorDetail {
  message: string;
  error_code: AuthErrorCode;
  required_tier: Tier;
  feature: string;
  expired_at?: string;  // Only for subscription_expired
}
```

### Permission Hook

```typescript
// hooks/usePermission.ts

import { Permission, Tier, TIER_PERMISSIONS } from "../types/permissions";
import { useAuth } from "./useAuth";

// Mirror backend permissions (or fetch from /api/permissions endpoint)
const TIER_PERMISSIONS: Record<Tier, Set<Permission>> = {
  free: new Set(["clip_basic", "recipe_save", "recipe_create", "recipe_edit", "recipe_list", "recipe_delete"]),
  pro: new Set(["clip_basic", "clip_ai", "clip_upload", "recipe_save", "recipe_create", "recipe_edit", "recipe_list", "recipe_delete"]),
};

export function usePermission(permission: Permission): boolean {
  const { user } = useAuth();

  if (!user) return false;
  return TIER_PERMISSIONS[user.tier]?.has(permission) ?? false;
}
```

### Error Handling

```typescript
// api/errors.ts

export function handleAuthError(error: AuthErrorDetail): void {
  if (error.error_code === "subscription_expired") {
    showModal({
      title: "Subscription Expired",
      message: "Your Pro subscription has expired. Renew to continue using this feature.",
      action: { label: "Renew", href: "/pricing" },
    });
  } else {
    showModal({
      title: "Pro Feature",
      message: error.message,
      action: { label: "Upgrade", href: "/pricing" },
    });
  }
}
```

### Fetching Tier from Supabase Session

```typescript
// hooks/useAuth.ts

function mapSupabaseUser(supabaseUser: SupabaseUser): User {
  const metadata = supabaseUser.app_metadata || {};

  return {
    id: supabaseUser.id,
    email: supabaseUser.email,
    tier: metadata.tier || "free",
    tierExpiresAt: metadata.tier_expires_at,
  };
}
```

## Configuration

### Environment Variables

| Variable | Description | Required | Phase |
|----------|-------------|----------|-------|
| `PRO_USER_IDS` | Comma-separated user IDs with pro access | No | 1 |
| `LLM_ALLOWED_IPS` | (Deprecated) Remove after Phase 1 | - | - |

### Deprecation: LLM_ALLOWED_IPS

Phase 1 replaces `LLM_ALLOWED_IPS` with `PRO_USER_IDS`. Migration:

1. Add `PRO_USER_IDS` with pro user IDs
2. Update `/clip` route to use `require_permission` instead of IP check
3. Remove `LLM_ALLOWED_IPS` from config and environment

## Stripe Integration (Future)

When implementing Stripe:

### Webhook Handler

```python
# routes/webhooks.py

@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    event = stripe.Webhook.construct_event(payload, sig_header, settings.stripe_webhook_secret)

    if event["type"] == "customer.subscription.created":
        await update_user_tier(
            user_id=event["data"]["object"]["metadata"]["user_id"],
            tier="pro",
            expires_at=datetime.fromtimestamp(event["data"]["object"]["current_period_end"]),
            stripe_customer_id=event["data"]["object"]["customer"],
            stripe_subscription_id=event["data"]["object"]["id"],
        )

    elif event["type"] == "customer.subscription.deleted":
        await update_user_tier(
            user_id=event["data"]["object"]["metadata"]["user_id"],
            tier="free",
        )

    return {"status": "ok"}
```

### Update Supabase User Metadata

```python
# services/supabase.py

from supabase import create_client

async def update_user_tier(
    user_id: str,
    tier: str,
    expires_at: datetime | None = None,
    stripe_customer_id: str | None = None,
    stripe_subscription_id: str | None = None,
):
    """Update user's tier in Supabase app_metadata."""
    supabase = create_client(settings.supabase_url, settings.supabase_service_role_key)

    metadata = {"tier": tier}
    if expires_at:
        metadata["tier_expires_at"] = expires_at.isoformat()
    if stripe_customer_id:
        metadata["stripe_customer_id"] = stripe_customer_id
    if stripe_subscription_id:
        metadata["stripe_subscription_id"] = stripe_subscription_id

    supabase.auth.admin.update_user_by_id(
        user_id,
        {"app_metadata": metadata},
    )
```

## Implementation Checklist

### Phase 1: Config-Based Pro Users

- [x] Create `authorization/` module structure
- [x] Implement `permissions.py` with enums and `TIER_PERMISSIONS`
- [x] Implement `exceptions.py` with custom HTTP exceptions
- [x] Add `PRO_USER_IDS` to `config.py`
- [x] Implement `get_tier_info` dependency (config-based)
- [x] Implement `require_permission` dependency factory
- [x] Update `/clip` route to use permission check instead of IP allowlist
- [x] Update `/clip/upload` route to use `require_permission`
- [x] Remove `LLM_ALLOWED_IPS` from config
- [ ] Add frontend error handling for auth errors
- [x] Write unit tests for permission logic
- [x] Write integration tests for protected routes

### Phase 2: Supabase User Metadata

- [ ] Extend `User` model with `app_metadata`
- [ ] Update JWT parsing to extract `app_metadata`
- [ ] Update `get_tier_info` to read from Supabase metadata
- [ ] Add `TierInfo` with expiration tracking
- [ ] Update frontend to read tier from Supabase session
- [ ] Test expiration handling

### Phase 3: Stripe Integration

- [ ] Add Stripe SDK dependency
- [ ] Add Stripe config (API key, webhook secret)
- [ ] Create checkout session endpoint
- [ ] Implement webhook handler
- [ ] Implement `update_user_tier` Supabase function
- [ ] Add customer portal link endpoint
- [ ] Test full subscription flow

## Testing Strategy

### Unit Tests

```python
# tests/test_permissions.py

def test_free_tier_has_basic_permissions():
    assert has_permission(Tier.FREE, Permission.CLIP_BASIC)
    assert has_permission(Tier.FREE, Permission.RECIPE_SAVE)

def test_free_tier_lacks_pro_permissions():
    assert not has_permission(Tier.FREE, Permission.CLIP_AI)
    assert not has_permission(Tier.FREE, Permission.CLIP_UPLOAD)

def test_pro_tier_has_all_permissions():
    for permission in Permission:
        assert has_permission(Tier.PRO, permission)
```

### Integration Tests

```python
# tests/test_authorization.py

async def test_clip_upload_requires_pro(client, free_user_token):
    response = await client.post(
        "/clip/upload",
        headers={"Authorization": f"Bearer {free_user_token}"},
        files={"file": ("recipe.jpg", b"...", "image/jpeg")},
    )
    assert response.status_code == 403
    assert response.json()["detail"]["error_code"] == "upgrade_required"

async def test_clip_upload_allowed_for_pro(client, pro_user_token):
    response = await client.post(
        "/clip/upload",
        headers={"Authorization": f"Bearer {pro_user_token}"},
        files={"file": ("recipe.jpg", b"...", "image/jpeg")},
    )
    assert response.status_code == 200

async def test_expired_pro_gets_distinct_error(client, expired_pro_user_token):
    response = await client.post(
        "/clip/upload",
        headers={"Authorization": f"Bearer {expired_pro_user_token}"},
        files={"file": ("recipe.jpg", b"...", "image/jpeg")},
    )
    assert response.status_code == 403
    assert response.json()["detail"]["error_code"] == "subscription_expired"
```

## Security Considerations

1. **JWT validation**: Tier info in JWT is signed by Supabase; cannot be tampered with
2. **Config-based overrides**: `PRO_USER_IDS` provides escape hatch but should be kept minimal
3. **Webhook verification**: Stripe webhooks must verify signature before processing
4. **Service role key**: Keep `SUPABASE_SERVICE_ROLE_KEY` secret; only used server-side for admin operations

## Migration Notes

### From IP Allowlist to User-Based Authorization

The current `LLM_ALLOWED_IPS` approach has limitations:
- Ties access to network location, not user identity
- Doesn't work for mobile users or VPNs
- No path to payment integration

The new system:
- Ties access to authenticated user identity
- Works regardless of network
- Ready for Stripe integration
- Maintains single-tenant compatibility (all users are pro)
