import { createClient, Session } from "@supabase/supabase-js";

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseAnonKey) {
  throw new Error("Missing Supabase environment variables");
}

export const supabase = createClient(supabaseUrl, supabaseAnonKey, {
  auth: {
    autoRefreshToken: true,
    persistSession: true,
    detectSessionInUrl: true, // Important for magic link redirects
    flowType: "pkce",
  },
});

/**
 * Sync session to httpOnly cookie for backend authentication
 */
export function syncSessionToCookie(session: Session | null): void {
  if (session?.access_token) {
    document.cookie = `access_token=${session.access_token}; path=/; SameSite=Lax; Secure`;
  } else {
    document.cookie =
      "access_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
  }
}
