import { createContext } from "react";
import { AuthError } from "@supabase/supabase-js";
import { User } from "../types/auth";

export interface AuthContextType {
  user: User | null;
  loading: boolean;
  isAuthEnabled: boolean;
  signInWithMagicLink: (email: string) => Promise<{ error: AuthError | null }>;
  signOut: () => Promise<{ error: AuthError | null }>;
}

export const AuthContext = createContext<AuthContextType | undefined>(
  undefined
);
