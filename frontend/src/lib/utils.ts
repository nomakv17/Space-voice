import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Parse a date string (YYYY-MM-DD) without timezone issues.
 * JavaScript's `new Date("2026-01-01")` interprets as UTC midnight,
 * which shows as Dec 31, 2025 in US timezones.
 * This forces noon to keep the date in the same day regardless of timezone.
 */
export function parseLocalDate(dateString: string): Date {
  // If already has time component, parse directly
  if (dateString.includes("T")) {
    return new Date(dateString);
  }
  // Add noon time to avoid timezone day-shift issues
  return new Date(`${dateString}T12:00:00`);
}

/**
 * Format a date string (YYYY-MM-DD) to a localized display format.
 * Handles timezone correctly to prevent off-by-one month/day errors.
 */
export function formatMonthYear(dateString: string): string {
  return parseLocalDate(dateString).toLocaleDateString("en-US", {
    month: "long",
    year: "numeric",
  });
}

/**
 * Format a date string (YYYY-MM-DD) to short month/year (e.g., "Jan 26").
 */
export function formatShortMonthYear(dateString: string): string {
  return parseLocalDate(dateString).toLocaleDateString("en-US", {
    month: "short",
    year: "2-digit",
  });
}
