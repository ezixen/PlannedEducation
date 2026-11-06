/**
 * Offline exam crypto helpers (AES-GCM, key wrap, canonical JSON).
 * Separated from IndexedDB persistence so seal/verify can be unit-tested.
 */

export const CRYPTO_ALGORITHM = 'AES-GCM';
export const KEY_LENGTH = 256;
export const IV_LENGTH = 12;
export const SALT_LENGTH = 16;
export const SEAL_CRYPTO_VERSION = 1;
export const TAG_LENGTH = 16;

/** AES-GCM sealed blob — ciphertext and IV are always distinct. */
export interface EncryptedPayload {
  ciphertext: string; // base64
  iv: string; // base64
  version: number;
  aad: string;
}

export function bytesToBase64(bytes: Uint8Array): string {
  return btoa(String.fromCharCode(...bytes));
}

export function base64ToBytes(value: string): Uint8Array {
  return Uint8Array.from(atob(value), (c) => c.charCodeAt(0));
}

/**
 * Recursive canonical JSON for stable content hashing.
 * Sorts object keys at every level; arrays keep order.
 */
export function canonicalize(value: unknown): unknown {
  if (value === null || typeof value !== 'object') {
    return value;
  }
  if (Array.isArray(value)) {
    return value.map(canonicalize);
  }
  const obj = value as Record<string, unknown>;
  const sorted: Record<string, unknown> = {};
  for (const key of Object.keys(obj).sort()) {
    sorted[key] = canonicalize(obj[key]);
  }
  return sorted;
}

export function canonicalJSON(obj: unknown): string {
  return JSON.stringify(canonicalize(obj));
}

export async function computeHash(data: string): Promise<string> {
  const hash = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(data));
  return bytesToBase64(new Uint8Array(hash));
}

export async function deriveKey(passphrase: string, salt: Uint8Array): Promise<CryptoKey> {
  const keyMaterial = await crypto.subtle.importKey(
    'raw',
    new TextEncoder().encode(passphrase),
    'PBKDF2',
    false,
    ['deriveKey']
  );

  return crypto.subtle.deriveKey(
    {
      name: 'PBKDF2',
      salt: salt as BufferSource,
      iterations: 100_000,
      hash: 'SHA-256',
    },
    keyMaterial,
    { name: CRYPTO_ALGORITHM, length: KEY_LENGTH },
    false,
    ['encrypt', 'decrypt', 'wrapKey', 'unwrapKey']
  );
}

/** Session content key: extractable only long enough to wrap. */
export async function generateSessionKey(extractable = true): Promise<CryptoKey> {
  return crypto.subtle.generateKey(
    { name: CRYPTO_ALGORITHM, length: KEY_LENGTH },
    extractable,
    ['encrypt', 'decrypt']
  );
}

/** Master wrapping key — wrap/unwrap only (not for answer ciphertext). */
export async function generateMasterWrappingKey(): Promise<CryptoKey> {
  return crypto.subtle.generateKey(
    { name: CRYPTO_ALGORITHM, length: KEY_LENGTH },
    true,
    ['wrapKey', 'unwrapKey', 'encrypt', 'decrypt']
  );
}

export async function exportRawKey(key: CryptoKey): Promise<string> {
  const raw = await crypto.subtle.exportKey('raw', key);
  return bytesToBase64(new Uint8Array(raw));
}

export async function importMasterWrappingKey(raw: string): Promise<CryptoKey> {
  return crypto.subtle.importKey(
    'raw',
    base64ToBytes(raw) as BufferSource,
    CRYPTO_ALGORITHM,
    true,
    ['wrapKey', 'unwrapKey', 'encrypt', 'decrypt']
  );
}

/**
 * Wrap a session key with the master key. Never persist raw session key bytes.
 */
export async function wrapSessionKey(
  sessionKey: CryptoKey,
  masterKey: CryptoKey,
  aad: string
): Promise<EncryptedPayload> {
  const iv = crypto.getRandomValues(new Uint8Array(IV_LENGTH));
  const wrapped = await crypto.subtle.wrapKey('raw', sessionKey, masterKey, {
    name: CRYPTO_ALGORITHM,
    iv,
    additionalData: new TextEncoder().encode(aad),
  });
  return {
    ciphertext: bytesToBase64(new Uint8Array(wrapped)),
    iv: bytesToBase64(iv),
    version: SEAL_CRYPTO_VERSION,
    aad,
  };
}

/**
 * Unwrap a session key as non-extractable (in-memory use only).
 */
export async function unwrapSessionKey(
  wrapped: EncryptedPayload,
  masterKey: CryptoKey
): Promise<CryptoKey> {
  assertEncryptedPayload(wrapped, 'wrapped session key');
  return crypto.subtle.unwrapKey(
    'raw',
    base64ToBytes(wrapped.ciphertext) as BufferSource,
    masterKey,
    {
      name: CRYPTO_ALGORITHM,
      iv: base64ToBytes(wrapped.iv) as BufferSource,
      additionalData: new TextEncoder().encode(wrapped.aad),
    },
    { name: CRYPTO_ALGORITHM, length: KEY_LENGTH },
    false, // non-extractable
    ['encrypt', 'decrypt']
  );
}

export function assertEncryptedPayload(
  payload: EncryptedPayload | null | undefined,
  label = 'payload'
): asserts payload is EncryptedPayload {
  if (!payload?.ciphertext || !payload?.iv) {
    throw new Error(`Missing ciphertext for ${label} — fail closed`);
  }
  if (typeof payload.aad !== 'string' || payload.version == null) {
    throw new Error(`Invalid encrypted ${label} metadata — fail closed`);
  }
}

export async function encryptPayload(
  data: string,
  key: CryptoKey,
  aad: string
): Promise<EncryptedPayload> {
  const iv = crypto.getRandomValues(new Uint8Array(IV_LENGTH));
  const ciphertext = await crypto.subtle.encrypt(
    {
      name: CRYPTO_ALGORITHM,
      iv,
      additionalData: new TextEncoder().encode(aad),
    },
    key,
    new TextEncoder().encode(data)
  );
  return {
    ciphertext: bytesToBase64(new Uint8Array(ciphertext)),
    iv: bytesToBase64(iv),
    version: SEAL_CRYPTO_VERSION,
    aad,
  };
}

export async function decryptPayload(
  payload: EncryptedPayload,
  key: CryptoKey
): Promise<string> {
  assertEncryptedPayload(payload);
  const decrypted = await crypto.subtle.decrypt(
    {
      name: CRYPTO_ALGORITHM,
      iv: base64ToBytes(payload.iv) as BufferSource,
      additionalData: new TextEncoder().encode(payload.aad),
    },
    key,
    base64ToBytes(payload.ciphertext) as BufferSource
  );
  return new TextDecoder().decode(decrypted);
}

/** Build plaintext structure used for contentHash before sealing. */
export function buildSealPlaintext(input: {
  submissionId: string;
  examId: string;
  studentId: string;
  studentName: string;
  startedAt: number;
  completedAt: number;
  durationMs: number;
  timeLimitMs: number;
  autoSubmitted: boolean;
  answers: Array<{
    questionId: string;
    response: string;
    answeredAt: number;
    timeSpentMs: number;
  }>;
  sealVersion: number;
  sealedAt: number;
}): Record<string, unknown> {
  return {
    answers: input.answers.map((a) => ({
      answeredAt: a.answeredAt,
      questionId: a.questionId,
      response: a.response,
      timeSpentMs: a.timeSpentMs,
    })),
    autoSubmitted: input.autoSubmitted,
    completedAt: input.completedAt,
    durationMs: input.durationMs,
    examId: input.examId,
    sealVersion: input.sealVersion,
    sealedAt: input.sealedAt,
    startedAt: input.startedAt,
    studentId: input.studentId,
    studentName: input.studentName,
    submissionId: input.submissionId,
    timeLimitMs: input.timeLimitMs,
  };
}
