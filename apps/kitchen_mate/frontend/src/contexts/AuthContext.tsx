import { createContext, useContext, ReactNode } from "react";
import { AuthError } from "@supabase/supabase-js";
import { useAuth } from "../hooks/useAuth";
import { User } from "../types/auth";

interface AuthContextType {
  user: User | null;
  loading: boolean;
  isAuthEnabled: boolean;
  signInWithMagicLink: (email: string) => Promise<{ error: AuthError | null }>;
  signOut: () => Promise<{ error: AuthError | null }>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const auth = useAuth();

  return <AuthContext.Provider value={auth}>{children}</AuthContext.Provider>;
}

export function useAuthContext() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuthContext must be used within AuthProvider");
  }
  return context;
}
