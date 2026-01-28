# Authorization System Plan: Casbin Integration

This document outlines the plan for adding role-based authorization to KitchenMate using Casbin.

## Overview

| Component | Technology |
|-----------|------------|
| Authentication | Supabase (existing) |
| Authorization | Casbin (pycasbin) |
| Policy Storage | SQLite (existing database) |
| User Tiers | free, pro |

## Design Decisions

| Decision | Choice |
|----------|--------|
| Pro subscription source | Manual assignment initially, payment webhook later |
| Expiration | Yes, `expires_at` field on pro subscriptions |
| AI clip behavior | 403 with upgrade prompt for free users |
| Single-tenant default | Pro tier (full access) |
| Admin interface | Yes, for manual + webhook management |

## User Tiers and Permissions

### Free Tier

- Clip recipes from URL (no AI assistance)
- Save recipes to collection
- Create recipes manually
- Edit saved recipes
- List and delete saved recipes

### Pro Tier

Everything in Free tier, plus:

- Clip from webpage with AI support
- Clip from uploaded file (images, PDFs, documents)
- Future pro-only features

## Casbin Model

Using RBAC (Role-Based Access Control):

```ini
# model.conf
[request_definition]
r = sub, obj, act

[policy_definition]
p = sub, obj, act

[role_definition]
g = _, _

[policy_effect]
e = some(where (p.eft == allow))

[matchers]
m = g(r.sub, p.sub) && r.obj == p.obj && r.act == p.act
```

- **sub**: User role (free, pro)
- **obj**: Resource/feature (e.g., "clip_basic", "clip_ai", "clip_upload")
- **act**: Action (e.g., "use")

## Policy Definitions

| Feature | Permission | Free | Pro |
|---------|------------|------|-----|
| Clip recipe (no AI) | `clip_basic` | Yes | Yes |
| Clip with AI fallback | `clip_ai` | No | Yes |
| Clip from uploaded file | `clip_upload` | No | Yes |
| Save recipe | `recipe_save` | Yes | Yes |
| Create recipe manually | `recipe_create` | Yes | Yes |
| Edit saved recipe | `recipe_edit` | Yes | Yes |
| List recipes | `recipe_list` | Yes | Yes |
| Delete recipe | `recipe_delete` | Yes | Yes |

## Database Schema

### user_tiers Table

```python
class UserTierModel(Base):
    __tablename__ = "user_tiers"

    id: Mapped[str]                    # UUID, primary key
    user_id: Mapped[str]               # Supabase user ID, unique, indexed
    tier: Mapped[str]                  # "free" or "pro", default "free"
    created_at: Mapped[datetime]       # Timestamp
    updated_at: Mapped[datetime]       # Timestamp, auto-updated
    expires_at: Mapped[datetime|None]  # Pro expiration date

    # For future webhook integration
    payment_provider: Mapped[str|None]          # "stripe", "paddle", etc.
    external_subscription_id: Mapped[str|None]  # External reference
```

### casbin_rules Table

```python
class CasbinRuleModel(Base):
    __tablename__ = "casbin_rules"

    id: Mapped[int]           # Auto-increment primary key
    ptype: Mapped[str]        # "p" or "g"
    v0: Mapped[str|None]      # Policy values
    v1: Mapped[str|None]
    v2: Mapped[str|None]
    v3: Mapped[str|None]
    v4: Mapped[str|None]
    v5: Mapped[str|None]
```

## Module Structure

```
apps/kitchen_mate/src/kitchen_mate/
├── authorization/
│   ├── __init__.py           # Exports: Permission, Tier, require_permission
│   ├── constants.py          # Permission and Tier enums
│   ├── enforcer.py           # Casbin enforcer singleton
│   ├── adapter.py            # SQLAlchemy adapter for Casbin
│   ├── dependencies.py       # FastAPI dependencies
│   └── policies.py           # Default policy definitions
├── database/
│   └── models/
│       └── authorization.py  # UserTierModel, CasbinRuleModel
├── routes/
│   └── admin.py              # Admin tier management endpoints
```

## FastAPI Dependencies

### get_user_tier

Returns the user's current tier, handling:
- Single-tenant mode: always returns "pro"
- Multi-tenant mode: looks up tier from database
- Expiration checking: expired pro reverts to free

```python
async def get_user_tier(
    user: User = Depends(get_user),
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_db),
) -> str:
    if settings.is_single_tenant:
        return Tier.PRO

    tier_record = await get_user_tier_record(db, user.id)
    if tier_record is None:
        return Tier.FREE

    if tier_record.tier == Tier.PRO and tier_record.expires_at:
        if tier_record.expires_at < datetime.utcnow():
            return Tier.FREE

    return tier_record.tier
```

### require_permission

Dependency factory for permission checks:

```python
def require_permission(permission: Permission):
    async def check_permission(
        user: User = Depends(get_user),
        tier: str = Depends(get_user_tier),
        enforcer: AsyncEnforcer = Depends(get_enforcer),
    ):
        allowed = await enforcer.enforce(tier, permission, "use")
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This feature requires a Pro subscription."
            )
        return user
    return check_permission
```

## Route Integration Examples

### Protected Route (Upload)

```python
@router.post("/clip/upload")
async def clip_upload(
    file: UploadFile,
    user: User = Depends(require_permission(Permission.CLIP_UPLOAD)),
):
    # Only pro users reach here
    ...
```

### Conditional Feature (AI Clip)

```python
@router.post("/clip")
async def clip(
    request: ClipRequest,
    user: User = Depends(get_user),
    tier: str = Depends(get_user_tier),
    enforcer: AsyncEnforcer = Depends(get_enforcer),
):
    can_use_ai = await enforcer.enforce(tier, Permission.CLIP_AI, "use")

    if request.use_llm_fallback and not can_use_ai:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="AI-assisted clipping requires a Pro subscription.",
            headers={"X-Upgrade-Required": "true"},
        )

    effective_use_llm = request.use_llm_fallback and can_use_ai
    ...
```

## Admin API

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/admin/users/{user_id}/tier` | Get user's tier status |
| POST | `/api/admin/users/{user_id}/tier` | Set/update user's tier |
| DELETE | `/api/admin/users/{user_id}/tier` | Revoke pro (set to free) |
| POST | `/api/admin/webhooks/subscription` | Payment provider webhook (future) |

### Request/Response Models

```python
class SetTierRequest(BaseModel):
    tier: Literal["free", "pro"]
    expires_at: datetime | None = None  # Required for pro

class TierResponse(BaseModel):
    user_id: str
    tier: str
    expires_at: datetime | None
    is_expired: bool
    created_at: datetime
    updated_at: datetime
```

### Authentication

Admin endpoints use bearer token authentication via `ADMIN_API_KEY` environment variable.

```python
async def verify_admin_key(authorization: str = Header(...)):
    if authorization != f"Bearer {settings.admin_api_key}":
        raise HTTPException(status_code=401, detail="Invalid admin key")
```

## Error Response Format

Structured error for frontend upgrade prompts:

```json
{
    "detail": "AI-assisted recipe clipping requires a Pro subscription.",
    "error_code": "upgrade_required",
    "required_tier": "pro",
    "feature": "clip_ai"
}
```

## Frontend Integration

### User Type Extension

```typescript
interface User {
  id: string;
  email?: string;
  tier: "free" | "pro";
}
```

### Permission Hook

```typescript
export function usePermission(permission: Permission): boolean {
  const { user } = useAuth();

  const TIER_PERMISSIONS: Record<Tier, Permission[]> = {
    free: [Permission.CLIP_BASIC, Permission.RECIPE_SAVE, ...],
    pro: [Permission.CLIP_BASIC, Permission.CLIP_AI, Permission.CLIP_UPLOAD, ...],
  };

  if (!user) return false;
  return TIER_PERMISSIONS[user.tier]?.includes(permission) ?? false;
}
```

## Implementation Phases

| Phase | Tasks | Priority |
|-------|-------|----------|
| **1. Core Setup** | Add dependencies (pycasbin, casbin-sqlalchemy-adapter), create authorization module structure | High |
| **2. Database** | Add `user_tiers` and `casbin_rules` tables | High |
| **3. Casbin Config** | Create model.conf, seed default policies for free/pro | High |
| **4. Dependencies** | Implement `get_user_tier`, `require_permission` FastAPI dependencies | High |
| **5. Route Integration** | Add permission checks to `/clip`, `/clip/upload`, `/me/*` routes | High |
| **6. Admin API** | Create `/api/admin/users/{user_id}/tier` endpoints | High |
| **7. Frontend** | Add tier to user context, permission hooks, upgrade prompts | Medium |
| **8. Webhook Prep** | Stub webhook endpoint for future payment provider integration | Low |

## Configuration

New environment variables:

| Variable | Description | Required |
|----------|-------------|----------|
| `ADMIN_API_KEY` | Bearer token for admin API access | Yes (multi-tenant) |

## Testing Strategy

1. **Unit tests**: Test permission checking logic in isolation
2. **Integration tests**: Test route authorization with mocked enforcer
3. **E2E tests**: Test full flow from login to permission-gated features

## Future Considerations

- **Payment webhooks**: Stripe/Paddle integration for automatic tier management
- **Usage quotas**: Rate limiting or usage caps per tier
- **Additional tiers**: Team/enterprise tiers with shared recipes
- **Granular permissions**: Per-resource permissions (e.g., share specific recipes)
