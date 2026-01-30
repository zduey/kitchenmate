export type Tier = "free" | "pro";

export interface User {
  id: string;
  email: string | null;
  tier: Tier;
}

export interface AuthState {
  user: User | null;
  loading: boolean;
}

/** Default user for single-tenant mode (no authentication) - gets full Pro access */
export const DEFAULT_USER: User = {
  id: "local",
  email: null,
  tier: "pro",
};
