export interface User {
  id: string;
  email: string | null;
}

export interface AuthState {
  user: User | null;
  loading: boolean;
}

/** Default user for single-tenant mode (no authentication) */
export const DEFAULT_USER: User = {
  id: "local",
  email: null,
};
