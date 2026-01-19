import { createClient, Session, SupabaseClient } from "@supabase/supabase-js";

// These constants are injected by Vite at build time (see vite.config.ts)
const supabaseUrl = __SUPABASE_URL__;
const supabaseAnonKey = __SUPABASE_ANON_KEY__;

// Auth is optional - app works without Supabase configured
export const isAuthEnabled = Boolean(supabaseUrl && supabaseAnonKey);

export const supabase: SupabaseClient | null =
  supabaseUrl && supabaseAnonKey
    ? createClient(supabaseUrl, supabaseAnonKey, {
      auth: {
        autoRefreshToken: true,
        persistSession: true,
        detectSessionInUrl: true,
        flowType: "pkce",
      },
    })
    : null;

/**
 * Sync session to httpOnly cookie for backend authentication
 */
export function syncSessionToCookie(session: Session | null): void {
  // Only use Secure flag when running on HTTPS (production)
  const isSecure = window.location.protocol === "https:";
  const secureFlag = isSecure ? "; Secure" : "";

  if (session?.access_token) {
    // URL-encode the token to handle any special characters
    const encodedToken = encodeURIComponent(session.access_token);
    document.cookie = `access_token=${encodedToken}; path=/; SameSite=Lax${secureFlag}`;
  } else {
    document.cookie =
      "access_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
  }
}
