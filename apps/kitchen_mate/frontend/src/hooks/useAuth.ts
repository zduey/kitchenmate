import { useState, useEffect } from "react";
import { User as SupabaseUser, AuthError } from "@supabase/supabase-js";
import { supabase, syncSessionToCookie } from "../lib/supabase";
import { User, AuthState } from "../types/auth";

function mapSupabaseUser(user: SupabaseUser): User {
  return {
    id: user.id,
    email: user.email ?? null,
  };
}

export function useAuth() {
  const [state, setState] = useState<AuthState>({
    user: null,
    loading: true,
  });

  useEffect(() => {
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

  /**
   * Send magic link to user's email
   */
  const signInWithMagicLink = async (
    email: string
  ): Promise<{ error: AuthError | null }> => {
    const { error } = await supabase.auth.signInWithOtp({
      email,
      options: {
        emailRedirectTo: window.location.origin,
      },
    });

    if (error) {
      return { error };
    }

    return { error: null };
  };

  const signOut = async (): Promise<{ error: AuthError | null }> => {
    const { error } = await supabase.auth.signOut();
    if (!error) {
      syncSessionToCookie(null);
    }
    return { error };
  };

  return {
    user: state.user,
    loading: state.loading,
    signInWithMagicLink,
    signOut,
  };
}
