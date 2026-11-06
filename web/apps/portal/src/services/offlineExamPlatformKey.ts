/**
 * F-017: Platform-bound wrap for the offline master key via WebAuthn PRF.
 * When a platform authenticator supports the PRF extension, the master key is
 * also stored as an AES-GCM blob wrapped by a KEK derived from PRF output
 * (OS-backed authenticator secret). IndexedDB still holds a non-extractable
 * CryptoKey for day-to-day use; the PRF wrap enables recovery after profile
 * wipe when the same passkey is presented.
 */

import {
  CRYPTO_ALGORITHM,
  KEY_LENGTH,
  IV_LENGTH,
  SEAL_CRYPTO_VERSION,
  bytesToBase64,
  base64ToBytes,
  type EncryptedPayload,
  assertEncryptedPayload,
  generateMasterWrappingKey,
  importMasterWrappingKey,
  exportRawKey,
} from './offlineExamCrypto';

/** Stable first-input salt for PRF eval (not a secret — authenticator binds output). */
export const PE_OFFLINE_PRF_FIRST = new TextEncoder().encode(
  'plannededucation-offline-master-prf-v1'
);

export function prfEvalExtension(): AuthenticationExtensionsClientInputs {
  return {
    // WebAuthn Level 3 PRF — typed loosely for TS DOM lib variance
    prf: {
      eval: {
        first: PE_OFFLINE_PRF_FIRST.buffer.slice(
          PE_OFFLINE_PRF_FIRST.byteOffset,
          PE_OFFLINE_PRF_FIRST.byteOffset + PE_OFFLINE_PRF_FIRST.byteLength
        ),
      },
    },
  } as AuthenticationExtensionsClientInputs;
}

function getPrfFirstResults(ext: AuthenticationExtensionsClientOutputs | undefined): ArrayBuffer | null {
  if (!ext || typeof ext !== 'object') return null;
  const prf = (ext as { prf?: { results?: { first?: ArrayBuffer } } }).prf;
  const first = prf?.results?.first;
  return first instanceof ArrayBuffer ? first : null;
}

async function deriveKekFromPrf(prfBits: ArrayBuffer): Promise<CryptoKey> {
  const keyMaterial = await crypto.subtle.importKey('raw', prfBits, 'HKDF', false, ['deriveKey']);
  return crypto.subtle.deriveKey(
    {
      name: 'HKDF',
      hash: 'SHA-256',
      salt: new TextEncoder().encode('pe-offline-prf-kek-salt-v1'),
      info: new TextEncoder().encode('pe-offline-master-wrap'),
    },
    keyMaterial,
    { name: CRYPTO_ALGORITHM, length: KEY_LENGTH },
    false,
    ['encrypt', 'decrypt', 'wrapKey', 'unwrapKey']
  );
}

/** Wrap extractable master raw bytes under a PRF-derived KEK. */
export async function wrapMasterWithPrfBits(
  masterRawBase64: string,
  prfBits: ArrayBuffer
): Promise<EncryptedPayload> {
  const kek = await deriveKekFromPrf(prfBits);
  const iv = crypto.getRandomValues(new Uint8Array(IV_LENGTH));
  const aad = 'offline-master-prf-wrap-v1';
  const ciphertext = await crypto.subtle.encrypt(
    { name: CRYPTO_ALGORITHM, iv, additionalData: new TextEncoder().encode(aad) },
    kek,
    base64ToBytes(masterRawBase64) as BufferSource
  );
  return {
    ciphertext: bytesToBase64(new Uint8Array(ciphertext)),
    iv: bytesToBase64(iv),
    version: SEAL_CRYPTO_VERSION,
    aad,
  };
}

/** Unwrap PRF-bound master into a non-extractable CryptoKey. */
export async function unwrapMasterWithPrfBits(
  wrapped: EncryptedPayload,
  prfBits: ArrayBuffer
): Promise<CryptoKey> {
  assertEncryptedPayload(wrapped, 'prf-wrapped master');
  const kek = await deriveKekFromPrf(prfBits);
  const raw = await crypto.subtle.decrypt(
    {
      name: CRYPTO_ALGORITHM,
      iv: base64ToBytes(wrapped.iv) as BufferSource,
      additionalData: new TextEncoder().encode(wrapped.aad),
    },
    kek,
    base64ToBytes(wrapped.ciphertext) as BufferSource
  );
  return importMasterWrappingKey(bytesToBase64(new Uint8Array(raw)));
}

/**
 * After a successful WebAuthn ceremony, persist a PRF-wrapped copy of the
 * current master (or create one). Returns true when PRF wrap was stored.
 */
export async function persistMasterPrfWrapFromCredential(
  extensionResults: AuthenticationExtensionsClientOutputs | undefined,
  getOrCreateMasterRaw: () => Promise<string>,
  putPrfWrap: (payload: EncryptedPayload) => Promise<void>
): Promise<boolean> {
  const prfBits = getPrfFirstResults(extensionResults);
  if (!prfBits) return false;
  const raw = await getOrCreateMasterRaw();
  const wrapped = await wrapMasterWithPrfBits(raw, prfBits);
  await putPrfWrap(wrapped);
  return true;
}

/**
 * Try to recover a non-extractable master from a PRF wrap using credential results.
 */
export async function recoverMasterFromPrfWrap(
  wrapped: EncryptedPayload | undefined,
  extensionResults: AuthenticationExtensionsClientOutputs | undefined
): Promise<CryptoKey | null> {
  if (!wrapped) return null;
  const prfBits = getPrfFirstResults(extensionResults);
  if (!prfBits) return null;
  try {
    return await unwrapMasterWithPrfBits(wrapped, prfBits);
  } catch {
    return null;
  }
}

/**
 * Create a one-time extractable master, export raw for PRF wrap, return
 * non-extractable working key + raw for wrap.
 */
export async function createMasterWithExportableRaw(): Promise<{
  masterKey: CryptoKey;
  rawBase64: string;
}> {
  // Temporary extractable key for PRF wrap export only.
  const extractable = await crypto.subtle.generateKey(
    { name: CRYPTO_ALGORITHM, length: KEY_LENGTH },
    true,
    ['wrapKey', 'unwrapKey', 'encrypt', 'decrypt']
  );
  const rawBase64 = await exportRawKey(extractable);
  const masterKey = await importMasterWrappingKey(rawBase64);
  return { masterKey, rawBase64 };
}

export async function ensureWorkingMasterKey(
  existing: CryptoKey | undefined
): Promise<CryptoKey> {
  if (existing) return existing;
  return generateMasterWrappingKey();
}
