import { useAuthContext } from "./useAuthContext";
import { User, DEFAULT_USER } from "../types/auth";

interface RequireAuthResult {
  /** Whether the user is authorized to perform user-gated actions */
  isAuthorized: boolean;
  /** The current user (DEFAULT_USER in single-tenant, authenticated user in multi-tenant) */
  user: User;
  /** Whether the user has Pro tier access */
  isPro: boolean;
}

/**
 * Hook for user-gated features that require authentication in multi-tenant mode.
 *
 * In single-tenant mode: Always returns authorized with DEFAULT_USER and isPro=true
 * In multi-tenant mode: Returns authorized only if user is authenticated
 *
 * Usage:
 * ```tsx
 * const { isAuthorized, user, isPro } = useRequireAuth();
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

  // Single-tenant mode: always authorized with default user and Pro access
  if (!isAuthEnabled) {
    return {
      isAuthorized: true,
      user: DEFAULT_USER,
      isPro: true,
    };
  }

  // Multi-tenant mode: authorized only if authenticated
  const currentUser = user ?? DEFAULT_USER;
  return {
    isAuthorized: user !== null,
    user: currentUser,
    isPro: currentUser.tier === "pro",
  };
}
