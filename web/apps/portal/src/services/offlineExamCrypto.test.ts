/**
 * F-017 offline exam crypto tests (Web Crypto AES-GCM + seal round-trip).
 */
import { describe, expect, it } from 'vitest';
import {
  assertEncryptedPayload,
  canonicalJSON,
  computeHash,
  decryptPayload,
  encryptPayload,
  generateMasterWrappingKey,
  generateSessionKey,
  unwrapSessionKey,
  wrapSessionKey,
} from './offlineExamCrypto';
import {
  buildSealedExamSubmission,
  decryptSealedSubmission,
  verifySealedSubmission,
  type OfflineExamState,
} from './offlineExam';

function sampleState(overrides: Partial<OfflineExamState> = {}): OfflineExamState {
  return {
    id: 'exam-1-student-1',
    examId: 'exam-1',
    studentId: 'student-1',
    studentName: 'Alex Student',
    package: {
      examId: 'exam-1',
      title: 'Unit Test Exam',
      duration_minutes: 30,
      instructions: 'Answer all',
      questions: [],
      settings: {
        shuffle_questions: false,
        shuffle_options: false,
        show_results_immediately: false,
        allow_review: true,
        require_seb: false,
        time_multiplier: 1,
        passing_score: 50,
      },
      started_at: 1_700_000_000_000,
      expires_at: 1_700_001_800_000,
    },
    answers: { q1: '42', q2: 'nested {"b":2,"a":1}' },
    answerTimestamps: { q1: 1_700_000_060_000, q2: 1_700_000_120_000 },
    currentQuestionIndex: 0,
    timeRemainingMs: 1_000_000,
    timerState: 'running',
    lastTimerTick: 1_700_000_120_000,
    startedAt: 1_700_000_000_000,
    lastHeartbeat: 1_700_000_120_000,
    isComplete: false,
    submissionId: 'sub-1',
    sebViolations: [],
    lastUpdated: 1_700_000_120_000,
    ...overrides,
  };
}

describe('offlineExamCrypto canonical JSON', () => {
  it('recursively sorts object keys', () => {
    const a = canonicalJSON({ z: 1, a: { d: 2, c: 3 }, m: [1, { b: 1, a: 2 }] });
    const b = canonicalJSON({ a: { c: 3, d: 2 }, m: [1, { a: 2, b: 1 }], z: 1 });
    expect(a).toBe(b);
  });
});

describe('offlineExamCrypto AES-GCM payload', () => {
  it('round-trips encrypt/decrypt with AAD', async () => {
    const key = await generateSessionKey(false);
    const payload = await encryptPayload('secret-answer', key, 'aad:test');
    expect(payload.ciphertext).toBeTruthy();
    expect(payload.iv).toBeTruthy();
    expect(payload.ciphertext).not.toBe(payload.iv);
    expect(await decryptPayload(payload, key)).toBe('secret-answer');
  });

  it('fails closed when ciphertext is missing', () => {
    expect(() =>
      assertEncryptedPayload({ ciphertext: '', iv: 'abc', version: 1, aad: 'x' }, 'test')
    ).toThrow(/Missing ciphertext/);
  });

  it('rejects tampered ciphertext', async () => {
    const key = await generateSessionKey(false);
    const payload = await encryptPayload('plain', key, 'aad:tamper');
    const tampered = {
      ...payload,
      ciphertext: payload.ciphertext.slice(0, -4) + 'AAAA',
    };
    await expect(decryptPayload(tampered, key)).rejects.toThrow();
  });

  it('rejects wrong AAD', async () => {
    const key = await generateSessionKey(false);
    const payload = await encryptPayload('plain', key, 'aad:correct');
    await expect(
      decryptPayload({ ...payload, aad: 'aad:wrong' }, key)
    ).rejects.toThrow();
  });
});

describe('offlineExamCrypto key wrap', () => {
  it('generates a non-extractable master wrapping key', async () => {
    const master = await generateMasterWrappingKey();
    expect(master.extractable).toBe(false);
    await expect(crypto.subtle.exportKey('raw', master)).rejects.toThrow();
  });

  it('wraps session key and unwraps as non-extractable', async () => {
    const master = await generateMasterWrappingKey();
    const session = await generateSessionKey(true);
    const wrapped = await wrapSessionKey(session, master, 'session-wrap:exam-1');
    expect(wrapped.ciphertext).toBeTruthy();
    expect(wrapped.iv).toBeTruthy();

    const unwrapped = await unwrapSessionKey(wrapped, master);
    expect(unwrapped.extractable).toBe(false);

    const msg = await encryptPayload('hi', unwrapped, 'aad:k');
    expect(await decryptPayload(msg, unwrapped)).toBe('hi');
  });
});

describe('F-017 seal / verify / decrypt', () => {
  it('round-trips seal → verify → decrypt', async () => {
    const key = await generateSessionKey(true);
    const sealed = await buildSealedExamSubmission(sampleState(), 'Alex Student', key, 1_700_000_200_000);

    expect(sealed.encryption.ciphertext).toBeTruthy();
    expect(sealed.encryption.iv).toBeTruthy();
    expect(sealed.encryption.ciphertext).not.toBe(sealed.encryption.iv);
    expect(sealed.answers[0].encrypted.ciphertext).toBeTruthy();
    expect(sealed.answers[0].encrypted.iv).toBeTruthy();

    const verified = await verifySealedSubmission(sealed, key);
    expect(verified).toEqual({ valid: true });

    const decrypted = await decryptSealedSubmission(sealed, key);
    expect(decrypted).not.toBeNull();
    expect(decrypted!.submission.studentName).toBe('Alex Student');
    expect(decrypted!.answers).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ questionId: 'q1', response: '42' }),
        expect.objectContaining({ questionId: 'q2', response: 'nested {"b":2,"a":1}' }),
      ])
    );
  });

  it('fails closed when envelope ciphertext is stripped', async () => {
    const key = await generateSessionKey(true);
    const sealed = await buildSealedExamSubmission(sampleState(), 'Alex Student', key);
    sealed.encryption.ciphertext = '';

    const verified = await verifySealedSubmission(sealed, key);
    expect(verified.valid).toBe(false);
    expect(verified.reason).toMatch(/Missing ciphertext/);

    const decrypted = await decryptSealedSubmission(sealed, key);
    expect(decrypted).toBeNull();
  });

  it('detects answer tampering via responseHash', async () => {
    const key = await generateSessionKey(true);
    const sealed = await buildSealedExamSubmission(sampleState(), 'Alex Student', key);
    sealed.answers[0].responseHash = await computeHash('wrong');

    const verified = await verifySealedSubmission(sealed, key);
    expect(verified.valid).toBe(false);
    expect(verified.reason).toMatch(/Answer hash mismatch/);
  });

  it('uses canonical JSON for contentHash stability', async () => {
    const key = await generateSessionKey(true);
    const sealed = await buildSealedExamSubmission(sampleState(), 'Alex Student', key, 1_700_000_200_000);
    const envelope = {
      ciphertext: sealed.encryption.ciphertext,
      iv: sealed.encryption.iv,
      version: sealed.encryption.version,
      aad: sealed.encryption.aad,
    };
    const plaintext = await decryptPayload(envelope, key);
    expect(await computeHash(plaintext)).toBe(sealed.contentHash);
    // Re-parse and re-canonicalize must match
    expect(await computeHash(canonicalJSON(JSON.parse(plaintext)))).toBe(sealed.contentHash);
  });
});
