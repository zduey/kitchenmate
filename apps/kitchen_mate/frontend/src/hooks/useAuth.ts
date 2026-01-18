import { useState, useEffect } from "react";
import { User as SupabaseUser, AuthError } from "@supabase/supabase-js";
import { supabase, syncSessionToCookie, isAuthEnabled } from "../lib/supabase";
import { User, AuthState, DEFAULT_USER } from "../types/auth";

function mapSupabaseUser(user: SupabaseUser): User {
  return {
    id: user.id,
    email: user.email ?? null,
  };
}

export function useAuth() {
  // In single-tenant mode, always use DEFAULT_USER with no loading state
  const [state, setState] = useState<AuthState>({
    user: isAuthEnabled ? null : DEFAULT_USER,
    loading: isAuthEnabled,
  });

  useEffect(() => {
    // Single-tenant mode: no auth setup needed
    if (!supabase) {
      return;
    }

    // Check active session on mount
    supabase.auth.getSession().then(({ data: { session } }) => {
      setState({
        user: session?.user ? mapSupabaseUser(session.user) : null,
        loading: false,
      });
      syncSessionToCookie(session);
    });

    // Listen for auth changes (handles magic link redirects)
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setState({
        user: session?.user ? mapSupabaseUser(session.user) : null,
        loading: false,
      });
      syncSessionToCookie(session);
    });

    return () => subscription.unsubscribe();
  }, []);

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
