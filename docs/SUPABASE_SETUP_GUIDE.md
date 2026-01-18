# Supabase Setup Guide - Phase 2

This guide walks through setting up Supabase authentication for Kitchen Mate.

## Step 1: Create Supabase Project

1. Go to [https://supabase.com](https://supabase.com)
2. Sign in or create an account
3. Click **"New Project"**
4. Fill in project details:
   - **Name:** `kitchen-mate` (or your preferred name)
   - **Database Password:** Generate a strong password (save it!)
   - **Region:** Choose closest to your users
   - **Pricing Plan:** Free tier is sufficient for development
5. Click **"Create new project"**
6. Wait 2-3 minutes for project initialization

## Step 2: Configure Email Authentication

### Enable Magic Links

1. In your Supabase dashboard, navigate to:
   **Authentication** → **Providers**

2. Find **Email** provider (should be enabled by default)

3. Click on **Email** to expand settings

4. Configure the following:
   - ✅ **Enable Email provider** (should already be checked)
   - ✅ **Confirm email** - DISABLE for development (enable later for production)
   - ✅ **Secure email change** - Enable (recommended)

5. Under **Email Templates**, click **"Magic Link"**

6. Verify the template includes `{{ .ConfirmationURL }}` variable
   - This is the magic link that will be sent to users
   - You can customize the email styling/branding later

7. Click **"Save"**

## Step 3: Configure Redirect URLs

1. Navigate to: **Authentication** → **URL Configuration**

2. Set **Site URL:**
   ```
   http://localhost:5173
   ```
   (For development - you'll update this for production later)

3. Add **Redirect URLs** (one per line):
   ```
   http://localhost:5173
   http://localhost:5173/**
   ```

   Later, for production, add:
   ```
   https://kitchenmate.onrender.com
   https://kitchenmate.onrender.com/**
   ```

4. Click **"Save"**

## Step 4: Get Your Credentials

### Project URL and Keys

1. Navigate to: **Settings** → **API**

2. You'll need three values:

   **A. Project URL:**
   ```
   Look for: "Project URL"
   Format: https://xxxxxxxxxxxxx.supabase.co
   ```

   **B. Anon/Public Key:**
   ```
   Look for: "Project API keys" → "anon" → "public"
   Copy the long string starting with "eyJ..."
   ```

   **C. JWT Secret:**
   ```
   Look for: "JWT Settings" → "JWT Secret"
   Copy this secret (will be used for backend verification)
   ```

3. **IMPORTANT:** Keep these credentials secure!
   - Don't commit them to git
   - Don't share them publicly
   - Store them in `.env` files (which are gitignored)

## Step 5: Create Environment Files

### Backend Environment File

Create: `/home/user/kitchenmate/apps/kitchen_mate/.env`

```bash
# Existing variables (if any)
ANTHROPIC_API_KEY=your-existing-anthropic-key-if-any

# Supabase Configuration
SUPABASE_URL=https://xxxxxxxxxxxxx.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_JWT_SECRET=your-jwt-secret-here
```

**Replace with your actual values from Step 4!**

### Frontend Environment File

Create: `/home/user/kitchenmate/apps/kitchen_mate/frontend/.env`

```bash
VITE_SUPABASE_URL=https://xxxxxxxxxxxxx.supabase.co
VITE_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Use the same URL and anon key from backend, but NOT the JWT secret!**

## Step 6: Verify .gitignore

Ensure `.env` files are not tracked by git:

```bash
# Check that .env is in .gitignore
cat apps/kitchen_mate/.gitignore | grep .env
cat apps/kitchen_mate/frontend/.gitignore | grep .env
```

If not present, add `.env` to both `.gitignore` files.

## Step 7: Test Supabase Configuration

### Test in Supabase Dashboard

1. Navigate to: **Authentication** → **Users**

2. Click **"Invite user"** or **"Add user"**

3. Enter a test email (your own email for testing)

4. Choose **"Send Magic Link"**

5. Check your email for the magic link

6. Click the link - you should be redirected to `http://localhost:5173`

7. If successful, you'll see the user in the Users table

### Test with Kitchen Mate App

1. Start the backend:
   ```bash
   cd apps/kitchen_mate
   uv run uvicorn kitchen_mate.main:app --reload
   ```

2. Start the frontend (in another terminal):
   ```bash
   cd apps/kitchen_mate/frontend
   npm run dev
   ```

3. Open browser to: `http://localhost:5173`

4. Click **"Sign In"** button in header

5. Enter your email address

6. Click **"Send magic link"**

7. Check your email and click the magic link

8. You should be redirected back to the app and see your email in the header

## Troubleshooting

### Magic Link Email Not Arriving

**Issue:** Email doesn't arrive after clicking "Send magic link"

**Solutions:**
1. Check spam/junk folder
2. Verify email provider settings in Supabase
3. Check Supabase logs: **Logs** → **Auth Logs**
4. For production, you'll need to configure custom SMTP (Supabase has rate limits on free tier)

### CORS Errors in Browser Console

**Issue:** Browser shows CORS errors when calling Supabase

**Solutions:**
1. Verify redirect URLs are correctly configured in Supabase dashboard
2. Ensure `http://localhost:5173` is in the allowed URLs list
3. Check that frontend is running on port 5173 (Vite default)

### JWT Verification Fails in Backend

**Issue:** Backend returns 401 even with valid token

**Solutions:**
1. Verify `SUPABASE_JWT_SECRET` in backend `.env` matches Supabase dashboard
2. Check that secret doesn't have extra spaces or newlines
3. Restart backend server after updating `.env` file
4. Verify cookie is being set (check browser DevTools → Application → Cookies)

### Session Not Persisting

**Issue:** User logged out after page refresh

**Solutions:**
1. Check browser localStorage for Supabase session
2. Verify cookie is set with correct domain and path
3. Ensure `Secure` flag is only set in production (HTTPS)
4. Check browser privacy settings (some browsers block cookies)

## Next Steps

Once Supabase is configured and tested:

✅ You have a working authentication system
✅ Users can sign in with magic links
✅ Sessions persist across page refreshes
✅ Backend can verify JWTs from cookies

Ready to proceed with:
- Phase 5: Integration testing
- Phase 6: Production deployment
- Adding authenticated-only features

## Production Considerations (Later)

When deploying to production:

1. **Custom SMTP:** Configure SendGrid, AWS SES, or another email service
   - Supabase free tier has email limits
   - Better deliverability with custom SMTP

2. **Update URLs:** Change redirect URLs to production domain

3. **Enable Email Confirmation:** Re-enable email confirmation for security

4. **Rate Limiting:** Configure rate limits for magic link requests

5. **Monitoring:** Set up alerts for authentication failures

---

**Note:** Keep this guide handy for reference when setting up production environment or debugging authentication issues.
