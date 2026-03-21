/**
 * Octant AI — Formatting utilities.
 *
 * Helper functions for number formatting, date handling, and display
 * transformations used across all frontend components.
 */

/**
 * Format a number as a percentage string with specified decimal places.
 *
 * @param value - The decimal value (e.g., 0.1234 for 12.34%).
 * @param decimals - Number of decimal places to show (default 2).
 * @returns Formatted percentage string (e.g., "12.34%").
 */
export function formatPercent(value: number, decimals: number = 2): string {
  return `${(value * 100).toFixed(decimals)}%`;
}

/**
 * Format a number with commas and optional decimal places.
 *
 * @param value - The number to format.
 * @param decimals - Number of decimal places (default 2).
 * @returns Formatted number string (e.g., "1,234,567.89").
 */
export function formatNumber(value: number, decimals: number = 2): string {
  return value.toLocaleString("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

/**
 * Format a large number as a compact abbreviated string.
 *
 * @param value - The number to format (e.g., 1500000000).
 * @returns Abbreviated string (e.g., "1.5B").
 */
export function formatCompact(value: number): string {
  if (value >= 1e12) return `${(value / 1e12).toFixed(1)}T`;
  if (value >= 1e9) return `${(value / 1e9).toFixed(1)}B`;
  if (value >= 1e6) return `${(value / 1e6).toFixed(1)}M`;
  if (value >= 1e3) return `${(value / 1e3).toFixed(1)}K`;
  return value.toFixed(0);
}

/**
 * Format an ISO timestamp into a human-readable date/time string.
 *
 * @param iso - ISO 8601 timestamp string.
 * @returns Formatted local date/time string (e.g., "Mar 21, 2025, 10:45 AM").
 */
export function formatTimestamp(iso: string): string {
  return new Date(iso).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  });
}

/**
 * Format seconds remaining into a human-readable estimate string.
 *
 * @param seconds - Estimated seconds remaining.
 * @returns Human-readable string (e.g., "~2 min", "~45 sec").
 */
export function formatETA(seconds: number): string {
  if (seconds <= 0) return "finishing up...";
  if (seconds < 60) return `~${Math.round(seconds)} sec`;
  if (seconds < 3600) return `~${Math.round(seconds / 60)} min`;
  return `~${(seconds / 3600).toFixed(1)} hr`;
}

/**
 * Map a Sharpe ratio to a CSS colour class for the Octant display.
 *
 * @param sharpe - The Sharpe ratio value.
 * @returns Tailwind text colour class string.
 */
export function sharpeColour(sharpe: number): string {
  if (sharpe >= 2.0) return "text-oct-green";
  if (sharpe >= 1.0) return "text-oct-green-dk";
  if (sharpe >= 0.5) return "text-oct-amber";
  return "text-oct-red";
}

/**
 * Map a significance label to a Tailwind colour class.
 *
 * @param label - The significance label from hypothesis testing.
 * @returns Tailwind text colour class string.
 */
export function significanceColour(
  label: "strongly significant" | "significant" | "not significant"
): string {
  switch (label) {
    case "strongly significant":
      return "text-oct-green";
    case "significant":
      return "text-oct-amber";
    case "not significant":
      return "text-oct-text-dim";
  }
}

/**
 * Generate a unique session ID (UUID v4).
 *
 * @returns A new UUID v4 string.
 */
export function generateSessionId(): string {
  return crypto.randomUUID();
}
