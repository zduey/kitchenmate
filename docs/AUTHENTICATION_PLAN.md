# Authentication Implementation Plan

## Overview

**Authentication Method:** Email-based magic links (passwordless)
**Session Management:** JWT tokens in httpOnly cookies
**UI Pattern:** Minimal header with sign-in button + tooltip
**User Experience:** App fully functional without authentication

## Goals

1. Add user authentication infrastructure to Kitchen Mate
2. Maintain zero friction for anonymous users
3. Enable future authenticated features (collections, saved recipes, etc.)
4. Use industry-standard secure authentication patterns

## Authentication Flow

### User Journey

1. User enters email in authentication modal
2. Supabase sends magic link email
3. User clicks link in email
4. User redirected back to app with session tokens
5. Session stored in httpOnly cookie
6. User authenticated

### Technical Flow

```
Frontend (React)
    ↓ signInWithOtp({ email })
Supabase Auth
    ↓ sends email with magic link
User Email
    ↓ clicks link
Supabase Auth
    ↓ redirects with session
Frontend (React)
    ↓ stores JWT in cookie
Backend (FastAPI)
    ↓ verifies JWT from cookie
Authenticated Request
```

## UI Design

### Header Component

**Anonymous User:**
```
┌──────────────────────────────────────────────────────┐
│ Kitchen Mate                            [Sign In]    │
│ Extract recipes from any website                     │
└──────────────────────────────────────────────────────┘
```

- "Sign In" button in top-right
- Hover shows tooltip: "Save recipes, build collections, and more"
- Click opens authentication modal

**Authenticated User:**
```
┌──────────────────────────────────────────────────────┐
│ Kitchen Mate                    user@email.com  [⌄]  │
│ Extract recipes from any website                     │
└──────────────────────────────────────────────────────┘
```

- Shows user email address
- Dropdown/button to log out

### Authentication Modal

**Step 1 - Email Input:**
- Centered modal overlay
- Email input field
- "Send magic link" button
- Close button to dismiss

**Step 2 - Confirmation:**
- "Check your email" message
- Shows entered email address
- Instructions to click link
- "Use a different email" option

### Main App Behavior

- Recipe extraction works identically for all users
- No features blocked by authentication (initially)
- Clean, unobtrusive authentication option

## Backend Implementation

### Configuration Changes

**File:** `apps/kitchen_mate/src/kitchen_mate/config.py`

Add settings:
- `supabase_url: str | None` - Supabase project URL
- `supabase_anon_key: str | None` - Public anon key
- `supabase_jwt_secret: str | None` - JWT secret for verification

### New Authentication Module

**File:** `apps/kitchen_mate/src/kitchen_mate/auth.py`

Pure functions:
- `verify_jwt_token(token, settings) -> dict` - Verify JWT and return claims
- `extract_user_from_claims(claims) -> User` - Map JWT claims to User model
- `get_current_user()` - FastAPI dependency for required auth
- `get_current_user_optional()` - FastAPI dependency for optional auth

User model:
- `User(id: str, email: str | None)`

### New Auth Routes

**File:** `apps/kitchen_mate/src/kitchen_mate/routes/auth.py`

Endpoints:
- `GET /api/auth/me` - Returns current authenticated user

### Dependencies

Add to `apps/kitchen_mate/pyproject.toml`:
- `python-jose[cryptography]>=3.3.0` - JWT verification

### CORS Configuration

**File:** `apps/kitchen_mate/src/kitchen_mate/main.py`

Add CORS middleware:
- `allow_credentials=True` - Required for cookies
- `allow_origins` - Include localhost:5173 and production domain

### Testing

**File:** `apps/kitchen_mate/tests/test_auth.py`

Test cases:
- Valid JWT returns user
- Missing JWT returns 401
- Invalid JWT returns 401
- Expired JWT returns 401

## Frontend Implementation

### Dependencies

Add to `apps/kitchen_mate/frontend/package.json`:
- `@supabase/supabase-js@^2.39.0` - Supabase client library

### Supabase Client

**File:** `apps/kitchen_mate/frontend/src/lib/supabase.ts`

Configuration:
- `detectSessionInUrl: true` - Handle magic link redirects
- `autoRefreshToken: true` - Automatic token refresh
- `persistSession: true` - Session persistence
- `flowType: 'pkce'` - Enhanced security

Helper function:
- `syncSessionToCookie(session)` - Sync session to httpOnly cookie

### Type Definitions

**File:** `apps/kitchen_mate/frontend/src/types/auth.ts`

Types:
- `User { id: string; email: string | null }`
- `AuthState { user: User | null; loading: boolean }`

### Auth Hook

**File:** `apps/kitchen_mate/frontend/src/hooks/useAuth.ts`

Custom hook providing:
- `user` - Current user or null
- `loading` - Loading state
- `signInWithMagicLink(email)` - Send magic link
- `signOut()` - Clear session

### Auth Context

**File:** `apps/kitchen_mate/frontend/src/contexts/AuthContext.tsx`

React context provider:
- Wraps auth hook
- Makes auth state available app-wide
- `useAuthContext()` hook for consuming components

### Components

**File:** `apps/kitchen_mate/frontend/src/components/Header.tsx`

Features:
- App branding on left
- Conditional rendering: "Sign In" button OR user email
- Tooltip on "Sign In" button
- Manages auth modal state
- Logout functionality

**File:** `apps/kitchen_mate/frontend/src/components/AuthModal.tsx`

Features:
- Modal overlay/backdrop
- Contains AuthForm component
- Close button
- Open/close state management

**File:** `apps/kitchen_mate/frontend/src/components/AuthForm.tsx`

Features:
- Email input form
- "Check your email" confirmation screen
- Error handling
- Loading states

### App Updates

**File:** `apps/kitchen_mate/frontend/src/App.tsx`

Changes:
- Wrap with `AuthProvider`
- Add Header component
- Recipe extraction always visible (no auth required)
- Loading state during initial auth check

### API Client Updates

**File:** `apps/kitchen_mate/frontend/src/api/clip.ts`

Changes:
- Add `credentials: 'include'` to fetch calls
- Enables cookie transmission with requests

### Environment Variables

**File:** `apps/kitchen_mate/frontend/.env.example`

Variables:
- `VITE_SUPABASE_URL` - Supabase project URL
- `VITE_SUPABASE_ANON_KEY` - Supabase anon key

## Supabase Configuration

### Project Setup

1. Create Supabase project at https://supabase.com
2. Note credentials:
   - Project URL (Settings → API)
   - Anon/public key (Settings → API)
   - JWT secret (Settings → API)

### Email Authentication

**Configuration:**
- Email provider enabled by default
- Set confirmation method to "Magic Link"
- Email template includes `{{ .ConfirmationURL }}`

**Redirect URLs:**
- Development: `http://localhost:5173`
- Production: `https://kitchenmate.onrender.com`
- Set in Authentication → URL Configuration

**Site URL:**
- Production domain: `https://kitchenmate.onrender.com`

### Email Templates (Optional)

Customize magic link email:
- Add branding and styling
- Keep `{{ .ConfirmationURL }}` variable
- Clear call-to-action button

### Production SMTP

For production deployment:
- Configure custom SMTP provider (SendGrid, AWS SES, Resend)
- Avoids Supabase email rate limits
- Better deliverability
- Required for scale

## Deployment

### Environment Variables

**Backend (Render):**
- `SUPABASE_URL` - Supabase project URL
- `SUPABASE_ANON_KEY` - Supabase anon key
- `SUPABASE_JWT_SECRET` - JWT secret

**Frontend (Vite):**
- `VITE_SUPABASE_URL` - Supabase project URL
- `VITE_SUPABASE_ANON_KEY` - Supabase anon key

Add to `render.yaml`:
```yaml
envVars:
  - key: SUPABASE_URL
    sync: false
  - key: SUPABASE_ANON_KEY
    sync: false
  - key: SUPABASE_JWT_SECRET
    sync: false
```

### Production Checklist

- [ ] Set up custom SMTP provider
- [ ] Configure production redirect URLs in Supabase
- [ ] Add environment variables to Render
- [ ] Test magic link email delivery
- [ ] Verify HTTPS (required for secure cookies)
- [ ] Test across browsers
- [ ] Monitor Supabase auth logs

### Security Considerations

**Cookies:**
- httpOnly flag (prevents XSS access)
- SameSite=Lax (CSRF protection)
- Secure flag in production (HTTPS only)

**JWT Verification:**
- Verify signature on every request
- Check expiration claim
- Check audience claim ("authenticated")
- Never log tokens in production

**CORS:**
- Restrict origins to known domains
- Enable credentials for cookie support

## File Changes Summary

### New Backend Files (3)
- `apps/kitchen_mate/src/kitchen_mate/auth.py`
- `apps/kitchen_mate/src/kitchen_mate/routes/auth.py`
- `apps/kitchen_mate/tests/test_auth.py`

### Modified Backend Files (4)
- `apps/kitchen_mate/src/kitchen_mate/config.py`
- `apps/kitchen_mate/src/kitchen_mate/main.py`
- `apps/kitchen_mate/pyproject.toml`
- `apps/kitchen_mate/tests/conftest.py`

### New Frontend Files (6)
- `apps/kitchen_mate/frontend/src/lib/supabase.ts`
- `apps/kitchen_mate/frontend/src/types/auth.ts`
- `apps/kitchen_mate/frontend/src/hooks/useAuth.ts`
- `apps/kitchen_mate/frontend/src/contexts/AuthContext.tsx`
- `apps/kitchen_mate/frontend/src/components/Header.tsx`
- `apps/kitchen_mate/frontend/src/components/AuthModal.tsx`
- `apps/kitchen_mate/frontend/src/components/AuthForm.tsx`

### Modified Frontend Files (3)
- `apps/kitchen_mate/frontend/src/App.tsx`
- `apps/kitchen_mate/frontend/src/api/clip.ts`
- `apps/kitchen_mate/frontend/package.json`

**Total:** 16 files (9 new, 7 modified)

## Implementation Phases

### Phase 1: Backend Foundation (2-3 hours)
1. Add python-jose dependency
2. Update config.py with Supabase settings
3. Create auth.py with JWT verification
4. Create routes/auth.py with /me endpoint
5. Update main.py for CORS and router registration
6. Write backend tests

### Phase 2: Supabase Setup (30 minutes)
1. Create Supabase project
2. Configure email authentication
3. Set redirect URLs
4. Copy credentials
5. Test via Supabase dashboard

### Phase 3: Frontend Foundation (2-3 hours)
1. Install @supabase/supabase-js
2. Create Supabase client
3. Create auth types
4. Create useAuth hook
5. Create AuthContext
6. Test in console

### Phase 4: Frontend UI (2-3 hours)
1. Create Header component
2. Create AuthModal component
3. Create AuthForm component
4. Update App.tsx
5. Update API client
6. Wire up all interactions

### Phase 5: Integration Testing (1-2 hours)
1. Test complete magic link flow
2. Test session persistence
3. Test logout
4. Test error cases
5. Verify cookies
6. Cross-browser testing

### Phase 6: Deployment (1 hour)
1. Add environment variables to Render
2. Deploy
3. Test in production
4. Verify email delivery
5. Optional: Set up custom SMTP

**Total Estimated Time:** 8-12 hours

## Future Enhancements

When authenticated features are needed:

1. **Save Recipes** - Store extracted recipes per user
2. **Collections** - Organize recipes into collections
3. **Favorites** - Mark recipes as favorites
4. **Export Collections** - Export multiple recipes at once
5. **Search History** - Track user's recipe extraction history
6. **Preferences** - Save user preferences (default export format, etc.)
7. **Rate Limiting** - Per-user rate limits instead of IP-based

All infrastructure will be in place to add these incrementally.

## Testing Strategy

### Backend Tests
- JWT verification with valid token
- JWT verification with missing token
- JWT verification with invalid token
- JWT verification with expired token
- User extraction from claims

### Frontend Manual Tests
- [ ] Sign in flow completes successfully
- [ ] Magic link email received
- [ ] Click magic link redirects correctly
- [ ] Session persists on page refresh
- [ ] Logout clears session
- [ ] Header shows correct state
- [ ] Tooltip appears on hover
- [ ] Modal opens/closes correctly
- [ ] Form validation works
- [ ] Error messages display properly

### Integration Tests
- [ ] End-to-end authentication flow
- [ ] Recipe extraction works while authenticated
- [ ] Cookie set correctly with proper flags
- [ ] JWT verified correctly by backend
- [ ] Token refresh works automatically

## Design Decisions

### Why Magic Links?
- No passwords to manage or forget
- Automatic email verification
- Better security (no password leaks)
- Excellent UX (one click)
- Zero cost (no SMS fees)

### Why Cookies Over localStorage?
- httpOnly flag prevents XSS attacks
- SameSite attribute prevents CSRF
- Automatic inclusion in requests
- More secure for web apps

### Why Minimal UI?
- Respects anonymous user workflow
- Professional, clean aesthetic
- Easy to discover but not pushy
- Familiar pattern users understand
- Scalable for future features

### Why Supabase?
- Managed authentication service
- Built-in JWT verification
- Email delivery included
- Free tier sufficient for development
- Easy to scale in production
- Good documentation and community

## Success Criteria

✅ Anonymous users can use app without any authentication
✅ "Sign In" button visible but non-intrusive
✅ Magic link flow works end-to-end
✅ Session persists across page refreshes
✅ Backend correctly verifies JWT tokens
✅ All tests passing
✅ Works in production environment
✅ Email delivery reliable

## References

- [Supabase Auth Documentation](https://supabase.com/docs/guides/auth)
- [Magic Link Guide](https://supabase.com/docs/guides/auth/passwordless-login/auth-magic-link)
- [React Quickstart](https://supabase.com/docs/guides/auth/quickstarts/react)
- [JWT Best Practices](https://supabase.com/docs/guides/auth/server-side/advanced-guide)

---

**Plan Status:** Approved and ready for implementation
**Branch:** `claude/plan-supabase-auth-qTLeX`
**Created:** 2026-01-17
