import { useAuthContext } from "./useAuthContext";

/**
 * Check if the current user has Pro tier access.
 *
 * In single-tenant mode: Always returns true (DEFAULT_USER has "pro" tier)
 * In multi-tenant mode: Returns true only for Pro tier users
 */
export function useIsPro(): boolean {
  const { user, isAuthEnabled } = useAuthContext();

  // Single-tenant mode = Pro access for everyone
  if (!isAuthEnabled) {
    return true;
  }

  return user?.tier === "pro";
}

/**
 * Check if the current user can use AI-based recipe extraction.
 * Requires Pro tier.
 */
export function useCanUseAI(): boolean {
  return useIsPro();
}

/**
 * Check if the current user can upload files for recipe extraction.
 * Requires Pro tier.
 */
export function useCanUpload(): boolean {
  return useIsPro();
}
