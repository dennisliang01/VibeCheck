/**
 * Format a date for display.
 */
export function formatDate(d: Date): string {
  return d.toISOString().slice(0, 10);
}
