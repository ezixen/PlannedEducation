/**
 * Name helper utilities for PlannedEducation.
 * Policy: Real full name is required, and users/students are addressed by their real first name.
 */

export function getFirstName(fullName?: string | null, fallback = 'User'): string {
  if (!fullName) return fallback;
  const trimmed = fullName.trim();
  if (!trimmed) return fallback;
  const parts = trimmed.split(/\s+/);
  return parts[0] || fallback;
}

export function formatRealName(fullName?: string | null, email?: string | null, fallback = 'User'): string {
  if (fullName && fullName.trim()) {
    return fullName.trim();
  }
  if (email && email.trim()) {
    return email.trim();
  }
  return fallback;
}
