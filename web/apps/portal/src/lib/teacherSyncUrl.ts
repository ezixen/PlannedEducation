/**
 * F-048: Validate teacher-device LAN sync URLs (fail closed).
 *
 * Opposite of AI SSRF policy: only http(s) to private/LAN/loopback addresses,
 * OR hosts listed in VITE_TEACHER_SYNC_URL_ALLOWLIST (comma-separated).
 * Public internet hosts are rejected so educational records cannot be
 * exfiltrated via an arbitrary localStorage teacherSyncUrl.
 */

export type TeacherSyncUrlValidation =
  | { ok: true; url: string }
  | { ok: false; reasonKey: string };

const PRIVATE_V4 = [
  /^10\.\d{1,3}\.\d{1,3}\.\d{1,3}$/,
  /^192\.168\.\d{1,3}\.\d{1,3}$/,
  /^172\.(1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3}$/,
  /^127\.\d{1,3}\.\d{1,3}\.\d{1,3}$/,
];

function allowlistHosts(): Set<string> {
  const raw =
    (typeof import.meta !== 'undefined' &&
      (import.meta as ImportMeta & { env?: Record<string, string> }).env
        ?.VITE_TEACHER_SYNC_URL_ALLOWLIST) ||
    '';
  return new Set(
    raw
      .split(',')
      .map((h: string) => h.trim().toLowerCase())
      .filter(Boolean)
  );
}

function isPrivateOrLoopbackHost(hostname: string): boolean {
  const host = hostname.replace(/^\[|\]$/g, '').toLowerCase();
  if (host === 'localhost' || host === 'localhost.localdomain' || host.endsWith('.localhost')) {
    return true;
  }
  if (host.endsWith('.local')) {
    return true;
  }
  if (host === '::1') {
    return true;
  }
  // IPv6 ULA fc00::/7 and link-local fe80::/10 — treat as LAN.
  if (host.includes(':')) {
    const normalized = host.toLowerCase();
    if (
      normalized.startsWith('fc') ||
      normalized.startsWith('fd') ||
      normalized.startsWith('fe80')
    ) {
      return true;
    }
  }
  return PRIVATE_V4.some((re) => re.test(host));
}

function hasCredentialExfilPatterns(parsed: URL): boolean {
  if (parsed.username || parsed.password) {
    return true;
  }
  const q = parsed.search.toLowerCase();
  const markers = [
    'api_key=',
    'apikey=',
    'access_token=',
    'auth_token=',
    'password=',
    'secret=',
    'token=',
  ];
  return markers.some((m) => q.includes(m));
}

/**
 * Validate and normalize a teacher sync base URL.
 * Returns a stripped URL without trailing slash on success.
 */
export function validateTeacherSyncUrl(raw: string | null | undefined): TeacherSyncUrlValidation {
  if (raw == null) {
    return { ok: false, reasonKey: 'offline_sync.teacher_url_missing' };
  }
  const cleaned = String(raw).trim().replace(/\/+$/, '');
  if (!cleaned) {
    return { ok: false, reasonKey: 'offline_sync.teacher_url_missing' };
  }
  if (/\s/.test(cleaned)) {
    return { ok: false, reasonKey: 'offline_sync.teacher_url_invalid' };
  }

  let parsed: URL;
  try {
    parsed = new URL(cleaned);
  } catch {
    return { ok: false, reasonKey: 'offline_sync.teacher_url_invalid' };
  }

  const scheme = parsed.protocol.replace(':', '').toLowerCase();
  if (scheme !== 'http' && scheme !== 'https') {
    return { ok: false, reasonKey: 'offline_sync.teacher_url_invalid' };
  }

  if (!parsed.hostname) {
    return { ok: false, reasonKey: 'offline_sync.teacher_url_invalid' };
  }

  if (hasCredentialExfilPatterns(parsed)) {
    return { ok: false, reasonKey: 'offline_sync.teacher_url_invalid' };
  }

  const host = parsed.hostname.replace(/^\[|\]$/g, '').toLowerCase();
  if (allowlistHosts().has(host)) {
    return { ok: true, url: cleaned };
  }

  if (!isPrivateOrLoopbackHost(host)) {
    return { ok: false, reasonKey: 'offline_sync.teacher_url_public_denied' };
  }

  return { ok: true, url: cleaned };
}

/**
 * Read and validate localStorage teacherSyncUrl. Fail closed.
 */
export function getValidatedTeacherSyncUrl(): TeacherSyncUrlValidation {
  if (typeof localStorage === 'undefined') {
    return { ok: false, reasonKey: 'offline_sync.teacher_url_missing' };
  }
  return validateTeacherSyncUrl(localStorage.getItem('teacherSyncUrl'));
}
