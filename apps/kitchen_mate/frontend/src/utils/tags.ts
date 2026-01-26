/**
 * Format a tag for display.
 * Converts "past-night" to "Past Night", "desert" to "Desert", etc.
 */
export function formatTagForDisplay(tag: string): string {
  return tag
    .split(/[-_\s]+/)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(" ");
}

/**
 * Normalize a tag for storage.
 * Converts to lowercase and trims whitespace.
 */
export function normalizeTag(tag: string): string {
  return tag.trim().toLowerCase();
}
