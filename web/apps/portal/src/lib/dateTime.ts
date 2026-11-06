/**
 * Shared date/time display helpers (AGENTS.md §5).
 * Dates: dd/mm/yyyy; times without milliseconds; optional local/UTC label.
 */

export type DateTimeLabelOpt = 'local' | 'UTC' | false;

export interface FormatDateOpts {
  /** Append ` local` / ` UTC` when set; omit when false/undefined. */
  timeZoneLabel?: DateTimeLabelOpt;
}

function toDate(input: Date | string | number): Date {
  if (input instanceof Date) return input;
  return new Date(input);
}

function pad2(n: number): string {
  return String(n).padStart(2, '0');
}

function appendTzLabel(base: string, label: DateTimeLabelOpt | undefined): string {
  if (label === 'local') return `${base} local`;
  if (label === 'UTC') return `${base} UTC`;
  return base;
}

/** Format as `dd/mm/yyyy`, optionally with ` local` / ` UTC`. */
export function formatDateDdMmYyyy(
  date: Date | string | number,
  opts?: FormatDateOpts,
): string {
  const d = toDate(date);
  if (Number.isNaN(d.getTime())) return '';

  const useUtc = opts?.timeZoneLabel === 'UTC';
  const day = pad2(useUtc ? d.getUTCDate() : d.getDate());
  const month = pad2(useUtc ? d.getUTCMonth() + 1 : d.getMonth() + 1);
  const year = useUtc ? d.getUTCFullYear() : d.getFullYear();
  return appendTzLabel(`${day}/${month}/${year}`, opts?.timeZoneLabel);
}

/** Format as `dd/mm/yyyy HH:mm`, optionally with ` local` / ` UTC`. */
export function formatDateTimeDdMmYyyy(
  date: Date | string | number,
  opts?: FormatDateOpts,
): string {
  const d = toDate(date);
  if (Number.isNaN(d.getTime())) return '';

  const useUtc = opts?.timeZoneLabel === 'UTC';
  const day = pad2(useUtc ? d.getUTCDate() : d.getDate());
  const month = pad2(useUtc ? d.getUTCMonth() + 1 : d.getMonth() + 1);
  const year = useUtc ? d.getUTCFullYear() : d.getFullYear();
  const hours = pad2(useUtc ? d.getUTCHours() : d.getHours());
  const minutes = pad2(useUtc ? d.getUTCMinutes() : d.getMinutes());
  return appendTzLabel(`${day}/${month}/${year} ${hours}:${minutes}`, opts?.timeZoneLabel);
}

/**
 * Format a duration in milliseconds.
 * Under 60s → `45s`; otherwise → `2m 15s` (never shows milliseconds).
 */
export function formatDuration(ms: number): string {
  const totalSeconds = Math.max(0, Math.floor(Math.abs(ms) / 1000));
  if (totalSeconds < 60) {
    return `${totalSeconds}s`;
  }
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}m ${seconds}s`;
}

/**
 * Compact clock for chat bubbles: `HH:mm` (local) or `HH:mm UTC`.
 * Prefer `formatDateTimeDdMmYyyy` for admin/audit tables that need a full date.
 */
export function formatTimeHm(
  date: Date | string | number,
  opts?: FormatDateOpts,
): string {
  const d = toDate(date);
  if (Number.isNaN(d.getTime())) return '';
  const useUtc = opts?.timeZoneLabel === 'UTC';
  const hours = pad2(useUtc ? d.getUTCHours() : d.getHours());
  const minutes = pad2(useUtc ? d.getUTCMinutes() : d.getMinutes());
  return appendTzLabel(`${hours}:${minutes}`, opts?.timeZoneLabel);
}
