import { useAuthContext } from "./useAuthContext";
import { User, DEFAULT_USER } from "../types/auth";

interface RequireAuthResult {
  /** Whether the user is authorized to perform user-gated actions */
  isAuthorized: boolean;
  /** The current user (DEFAULT_USER in single-tenant, authenticated user in multi-tenant) */
  user: User;
}

/**
 * Hook for user-gated features that require authentication in multi-tenant mode.
 *
 * In single-tenant mode: Always returns authorized with DEFAULT_USER
 * In multi-tenant mode: Returns authorized only if user is authenticated
 *
 * Usage:
 * ```tsx
 * const { isAuthorized, user } = useRequireAuth();
 *
 * const handleSaveRecipe = () => {
 *   if (!isAuthorized) {
 *     openSignInModal();
 *     return;
 *   }
 *   // Save recipe with user.id
 * };
 * ```
 */
export function useRequireAuth(): RequireAuthResult {
  const { user, isAuthEnabled } = useAuthContext();

  // Single-tenant mode: always authorized with default user
  if (!isAuthEnabled) {
    return {
      isAuthorized: true,
      user: DEFAULT_USER,
    };
  }

  // Multi-tenant mode: authorized only if authenticated
  return {
    isAuthorized: user !== null,
    user: user ?? DEFAULT_USER,
  };
}
