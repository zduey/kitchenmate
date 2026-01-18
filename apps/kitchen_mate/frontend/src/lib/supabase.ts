import { createClient, Session, SupabaseClient } from "@supabase/supabase-js";

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

// Auth is optional - app works without Supabase configured
export const isAuthEnabled = Boolean(supabaseUrl && supabaseAnonKey);

// Log tenant mode on startup
if (isAuthEnabled) {
  console.log("[KitchenMate] Running in MULTI-TENANT mode (Supabase auth enabled)");
} else {
  console.log("[KitchenMate] Running in SINGLE-TENANT mode (no authentication)");
}

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
  if (session?.access_token) {
    document.cookie = `access_token=${session.access_token}; path=/; SameSite=Strict; Secure`;
  } else {
    document.cookie =
      "access_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
  }
}
