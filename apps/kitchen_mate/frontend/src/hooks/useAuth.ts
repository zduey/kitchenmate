import { useState, useEffect, useCallback } from "react";
import { User as SupabaseUser, AuthError, Session } from "@supabase/supabase-js";
import { supabase, syncSessionToCookie, isAuthEnabled } from "../lib/supabase";
import { User, AuthState, DEFAULT_USER, Tier } from "../types/auth";

interface AuthMeResponse {
  id: string;
  email: string | null;
  tier: Tier;
  expires_at: string | null;
}

async function fetchUserWithTier(supabaseUser: SupabaseUser): Promise<User> {
  try {
    const response = await fetch("/api/auth/me", {
      credentials: "include",
    });

    if (response.ok) {
      const data: AuthMeResponse = await response.json();
      return {
        id: data.id,
        email: data.email,
        tier: data.tier,
      };
    }
  } catch {
    // Fall back to default tier on error
  }

  // Fallback: use Supabase user info with free tier
  return {
    id: supabaseUser.id,
    email: supabaseUser.email ?? null,
    tier: "free",
  };
}

export function useAuth() {
  // In single-tenant mode, always use DEFAULT_USER with no loading state
  const [state, setState] = useState<AuthState>({
    user: isAuthEnabled ? null : DEFAULT_USER,
    loading: isAuthEnabled,
  });

  const handleSession = useCallback(async (session: Session | null) => {
    if (session?.user) {
      const user = await fetchUserWithTier(session.user);
      setState({ user, loading: false });
    } else {
      setState({ user: null, loading: false });
    }
    syncSessionToCookie(session);
  }, []);

  useEffect(() => {
    // Single-tenant mode: no auth setup needed
    if (!supabase) {
      return;
    }

    // Check active session on mount
    supabase.auth.getSession().then(({ data: { session } }) => {
      handleSession(session);
    });

    // Listen for auth changes (handles magic link redirects)
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      handleSession(session);
    });

    return () => subscription.unsubscribe();
  }, [handleSession]);

  const signInWithMagicLink = async (
    email: string
  ): Promise<{ error: AuthError | null }> => {
    if (!supabase) {
      return { error: { message: "Authentication not configured" } as AuthError };
    }

    const { error } = await supabase.auth.signInWithOtp({
      email,
      options: {
        emailRedirectTo: window.location.origin,
      },
    });

    return { error: error ?? null };
  };

  const signOut = async (): Promise<{ error: AuthError | null }> => {
    if (!supabase) {
      return { error: null };
    }

    const { error } = await supabase.auth.signOut();
    if (!error) {
      syncSessionToCookie(null);
    }
    return { error: error ?? null };
  };

  return {
    user: state.user,
    loading: state.loading,
    signInWithMagicLink,
    signOut,
    isAuthEnabled,
  };
}
