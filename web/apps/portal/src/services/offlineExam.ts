/**
 * Offline Exam Engine for PlannedEducation
 * Handles fully offline exam execution with IndexedDB persistence,
 * local timer, SEB integration, auto-submit on time expiry,
 * and cryptographic sealing for three-way immutable storage.
 * 
 * Storage Model (Three-Way Immutable):
 * 1. Student Local: Encrypted, sealed, integrity-verified
 * 2. Teacher Device: Encrypted copy, integrity-verified  
 * 3. Server (Deployed): Encrypted copy, integrity-verified
 * 
 * All three must match for verification - prevents cheating by any party.
 */

import { openDB, type DBSchema, type IDBPDatabase } from 'idb';
import { apiClient } from '../api';
import { getValidatedTeacherSyncUrl } from '../lib/teacherSyncUrl';
import {
  CRYPTO_ALGORITHM,
  SALT_LENGTH,
  SEAL_CRYPTO_VERSION,
  TAG_LENGTH,
  type EncryptedPayload,
  assertEncryptedPayload,
  buildSealPlaintext,
  bytesToBase64,
  canonicalJSON,
  computeHash,
  decryptPayload,
  deriveKey,
  encryptPayload,
  generateSessionKey,
  importMasterWrappingKey,
  unwrapSessionKey,
  wrapSessionKey,
} from './offlineExamCrypto';
import {
  createMasterWithExportableRaw,
  persistMasterPrfWrapFromCredential,
  recoverMasterFromPrfWrap,
  prfEvalExtension,
} from './offlineExamPlatformKey';

export {
  CRYPTO_ALGORITHM,
  SEAL_CRYPTO_VERSION,
  TAG_LENGTH,
  canonicalJSON,
  computeHash,
  decryptPayload,
  deriveKey,
  encryptPayload,
  type EncryptedPayload,
};

// ── Types ────────────────────────────────────────────────────────────────────

export interface ExamPackage {
  examId: string;
  title: string;
  duration_minutes: number;
  instructions: string;
  questions: ExamQuestion[];
  settings: ExamSettings;
  seb_config_key?: string;
  started_at: number; // Server timestamp when exam was started
  expires_at: number; // Server timestamp when exam must be submitted by
}

export interface ExamQuestion {
  question_id: string;
  question_type: 'multiple_choice' | 'essay' | 'dynamic_math';
  text: string;
  options: string[] | null;
  points: number;
  correct_answer?: string; // Only included if teacher allows
  rubric?: string;
}

export interface SpecialCharacterSet {
  category: string;
  chars: string[];
}

export interface ExamSettings {
  shuffle_questions: boolean;
  shuffle_options: boolean;
  show_results_immediately: boolean;
  allow_review: boolean;
  require_seb: boolean;
  time_multiplier: number;
  passing_score: number;
  delivery_mode?: 'classroom' | 'different_location';
  allow_digital_hand_raise?: boolean;
  special_characters?: SpecialCharacterSet[];
}

/**
 * SealedExamSubmission - Immutable, encrypted, integrity-verified submission
 * This is the core data structure for three-way storage.
 */
export interface SealedExamSubmission {
  // Identity
  submissionId: string;
  examId: string;
  studentId: string;
  /** Encrypted student display name (AES-GCM payload). */
  studentName: EncryptedPayload;

  // Timing (immutable once sealed)
  startedAt: number; // Local timestamp
  completedAt: number; // Local timestamp when sealed
  durationMs: number; // Actual time spent
  timeLimitMs: number; // Configured time limit
  autoSubmitted: boolean; // True if timer expired

  // Answers (each field-encrypted)
  answers: SealedAnswer[];

  // Integrity
  contentHash: string; // SHA-256 of canonical plaintext JSON (before encryption)
  sealVersion: number; // Protocol version
  sealedAt: number; // Timestamp when cryptographically sealed

  // Encryption metadata for the sealed envelope
  encryption: {
    algorithm: string; // 'AES-GCM'
    ciphertext: string; // Base64 — required; fail closed if missing
    iv: string; // Base64
    version: number;
    aad: string;
    salt: string; // Base64
    keyId: string; // Key derivation identifier
  };

  // Three-way sync metadata
  sync: {
    localSealed: boolean;
    teacherSynced: boolean;
    serverSynced: boolean;
    lastSyncAttempt: number;
    syncHash: string; // Hash for cross-verification
  };
}

export interface SealedAnswer {
  questionId: string;
  encrypted: EncryptedPayload;
  responseHash: string; // SHA-256 of plaintext for verification
  answeredAt: number;
  timeSpentMs: number;
}

/**
 * OfflineExamState - Runtime state during exam (not sealed).
 * `answers` is plaintext only in memory; IndexedDB stores `answersEncrypted`.
 */
export interface OfflineExamState {
  id: string; // `${examId}-${studentId}`
  examId: string;
  studentId: string;
  studentName: string;
  package: ExamPackage | null;
  answers: Record<string, string>; // questionId -> response (plaintext in memory)
  /** Present only in IndexedDB rows — never leave plaintext answers at rest. */
  answersEncrypted?: EncryptedPayload | null;
  answerTimestamps: Record<string, number>; // questionId -> when answered
  currentQuestionIndex: number;
  timeRemainingMs: number;
  timerState: 'running' | 'paused' | 'expired' | 'completed';
  lastTimerTick: number;
  startedAt: number;
  lastHeartbeat: number;
  isComplete: boolean;
  submissionId?: string;
  sebViolations: SEBViolation[];
  lastUpdated: number;

  // Sealed submission (once completed)
  sealedSubmission?: SealedExamSubmission;
}

export interface SEBViolation {
  type: 'exit' | 'minimize' | 'focus_loss' | 'shortcut_blocked' | 'process_detected';
  timestamp: number;
  details?: string;
}

export interface HeartbeatPayload {
  examId: string;
  studentId: string;
  timeRemainingMs: number;
  currentQuestionIndex: number;
  answersCount: number;
  sebViolations: SEBViolation[];
  clientTimestamp: number;
}

export interface ExamStartResponse {
  exam_package: ExamPackage;
  submission_id: string;
  server_time: number;
}

// ── IndexedDB Schema ────────────────────────────────────────────────────────

interface OfflineExamSchema extends DBSchema {
  offlineExams: {
    key: string;
    value: OfflineExamState;
    indexes: { 'by-exam': string; 'by-student': string; 'by-status': string };
  };
  examPackages: {
    key: string;
    value: ExamPackage;
    indexes: { 'by-exam': string };
  };
  heartbeatQueue: {
    key: number;
    value: HeartbeatQueueItem;
    indexes: { 'by-exam': string };
  };
  // Sealed submissions store (immutable, append-only)
  sealedSubmissions: {
    key: string;
    value: SealedExamSubmission;
    indexes: { 'by-exam': string; 'by-student': string; 'by-sealed': number };
  };
  // Sync queue for three-way replication
  syncQueue: {
    key: number;
    value: SyncQueueItem;
    indexes: { 'by-target': string; 'by-status': string };
  };
  cryptoKeys: {
    key: string;
    value: StoredCryptoKeyRecord;
  };
}

/**
 * Master: non-extractable CryptoKey (structured-clone) preferred.
 * Legacy base64 `key` is migrated away on first load.
 * Session: wrapped by master (never raw beside ciphertext).
 */
interface StoredCryptoKeyRecord {
  id: string;
  /** Non-extractable master CryptoKey persisted via IndexedDB structured clone. */
  cryptoKey?: CryptoKey;
  /** @deprecated Legacy base64 raw master — migrated to cryptoKey. */
  key?: string;
  /** Wrapped session key payload (AES-GCM wrap). */
  wrapped?: EncryptedPayload;
}

interface HeartbeatQueueItem {
  id?: number;
  examId: string;
  studentId: string;
  payload: HeartbeatPayload;
  createdAt: number;
  attempts: number;
}

interface SyncQueueItem {
  id?: number;
  submissionId: string;
  target: 'teacher' | 'server';
  payload: SealedExamSubmission;
  status: 'pending' | 'synced' | 'failed' | 'verified';
  createdAt: number;
  attempts: number;
  syncedAt?: number;
  verifiedAt?: number;
  verifiedBy?: string;
}

const DB_NAME = 'plannededucation-offline-exam';
const DB_VERSION = 3;

/** Non-extractable session keys held only in memory for the page lifetime. */
const sessionKeyCache = new Map<string, CryptoKey>();
let masterKeyPromise: Promise<CryptoKey> | null = null;

let dbInstance: IDBPDatabase<OfflineExamSchema> | null = null;

async function getExamDB(): Promise<IDBPDatabase<OfflineExamSchema>> {
  if (dbInstance) return dbInstance;
  
  dbInstance = await openDB<OfflineExamSchema>(DB_NAME, DB_VERSION, {
    upgrade(db, oldVersion) {
      // Offline Exam State Store
      const examStore = db.createObjectStore('offlineExams', { keyPath: 'id' });
      examStore.createIndex('by-exam', 'examId');
      examStore.createIndex('by-student', 'studentId');
      examStore.createIndex('by-status', 'timerState');
      
      // Exam Packages Store (cached for offline use)
      db.createObjectStore('examPackages', { keyPath: 'examId' });
      
      // Heartbeat Queue (for when online)
      const heartbeatStore = db.createObjectStore('heartbeatQueue', { keyPath: 'id', autoIncrement: true });
      heartbeatStore.createIndex('by-exam', 'examId');
      
      if (oldVersion < 2) {
        // Sealed Submissions Store (immutable, append-only)
        const sealedStore = db.createObjectStore('sealedSubmissions', { keyPath: 'submissionId' });
        sealedStore.createIndex('by-exam', 'examId');
        sealedStore.createIndex('by-student', 'studentId');
        sealedStore.createIndex('by-sealed', 'sealedAt');
        
        // Sync Queue for three-way replication
        const syncStore = db.createObjectStore('syncQueue', { keyPath: 'id', autoIncrement: true });
        syncStore.createIndex('by-target', 'target');
        syncStore.createIndex('by-status', 'status');
      }

      if (!db.objectStoreNames.contains('cryptoKeys')) {
        db.createObjectStore('cryptoKeys', { keyPath: 'id' });
      }
    },
  });

  return dbInstance;
}

// ── Key Hierarchy ──────────────────────────────────────────────────────────

/** In-memory only: raw master for a one-shot WebAuthn PRF wrap (never persisted). */
let pendingMasterRawForPrf: string | null = null;

/**
 * Device master wrapping key. Used only to wrap/unwrap session keys.
 * Stored as a non-extractable CryptoKey in IndexedDB (structured clone).
 * F-017: when a platform authenticator returns WebAuthn PRF results, a second
 * AES-GCM wrap (`master-prf-wrap`) is stored for OS-backed recovery.
 */
export async function getMasterKey(): Promise<CryptoKey> {
  if (!masterKeyPromise) {
    masterKeyPromise = (async () => {
      const db = await getExamDB();
      const stored = await db.get('cryptoKeys', 'master');

      if (stored?.cryptoKey instanceof CryptoKey) {
        return stored.cryptoKey;
      }

      // Migrate legacy extractable/base64 master → non-extractable CryptoKey in IDB.
      if (stored?.key) {
        const migrated = await importMasterWrappingKey(stored.key);
        pendingMasterRawForPrf = stored.key;
        await db.put('cryptoKeys', { id: 'master', cryptoKey: migrated });
        return migrated;
      }

      const { masterKey, rawBase64 } = await createMasterWithExportableRaw();
      pendingMasterRawForPrf = rawBase64;
      await db.put('cryptoKeys', { id: 'master', cryptoKey: masterKey });
      return masterKey;
    })();
  }
  return masterKeyPromise;
}

/** Client extension blob to merge into WebAuthn create/get options (F-017). */
export function offlineMasterPrfExtension(): AuthenticationExtensionsClientInputs {
  return prfEvalExtension();
}

/**
 * After passkey register/login, bind or recover the offline master via PRF.
 * Safe no-op when the authenticator does not support PRF.
 */
export async function syncOfflineMasterWithPasskeyPrf(
  extensionResults: AuthenticationExtensionsClientOutputs | undefined
): Promise<'bound' | 'recovered' | 'skipped'> {
  const db = await getExamDB();
  const existingWrap = await db.get('cryptoKeys', 'master-prf-wrap');
  const wrappedPayload = existingWrap?.wrapped as EncryptedPayload | undefined;

  // Prefer recovery when IDB master is missing but PRF wrap exists.
  const masterRow = await db.get('cryptoKeys', 'master');
  if (!(masterRow?.cryptoKey instanceof CryptoKey) && wrappedPayload) {
    const recovered = await recoverMasterFromPrfWrap(wrappedPayload, extensionResults);
    if (recovered) {
      await db.put('cryptoKeys', { id: 'master', cryptoKey: recovered });
      masterKeyPromise = Promise.resolve(recovered);
      pendingMasterRawForPrf = null;
      return 'recovered';
    }
  }

  await getMasterKey();
  if (!pendingMasterRawForPrf) {
    return 'skipped';
  }
  const bound = await persistMasterPrfWrapFromCredential(
    extensionResults,
    async () => pendingMasterRawForPrf as string,
    async (payload) => {
      await db.put('cryptoKeys', { id: 'master-prf-wrap', wrapped: payload });
      pendingMasterRawForPrf = null;
    }
  );
  return bound ? 'bound' : 'skipped';
}

/**
 * Get or create a non-extractable session content key.
 * Persisted only as a wrapped blob under the master key — never raw next to ciphertext.
 */
export async function getSessionKey(examId: string, studentId: string): Promise<CryptoKey> {
  const keyId = `${examId}-${studentId}`;
  const cached = sessionKeyCache.get(keyId);
  if (cached) return cached;

  const db = await getExamDB();
  const masterKey = await getMasterKey();
  const wrapAad = `session-wrap:${keyId}`;
  const stored = await db.get('cryptoKeys', keyId);

  if (stored?.wrapped) {
    const sessionKey = await unwrapSessionKey(stored.wrapped, masterKey);
    sessionKeyCache.set(keyId, sessionKey);
    return sessionKey;
  }

  // Migrate legacy plaintext raw session keys into wrapped form.
  if (stored?.key) {
    const legacyRaw = stored.key;
    const extractable = await crypto.subtle.importKey(
      'raw',
      Uint8Array.from(atob(legacyRaw), (c) => c.charCodeAt(0)) as BufferSource,
      CRYPTO_ALGORITHM,
      true,
      ['encrypt', 'decrypt']
    );
    const wrapped = await wrapSessionKey(extractable, masterKey, wrapAad);
    await db.put('cryptoKeys', { id: keyId, wrapped });
    const sessionKey = await unwrapSessionKey(wrapped, masterKey);
    sessionKeyCache.set(keyId, sessionKey);
    return sessionKey;
  }

  const extractable = await generateSessionKey(true);
  const wrapped = await wrapSessionKey(extractable, masterKey, wrapAad);
  await db.put('cryptoKeys', { id: keyId, wrapped });
  const sessionKey = await unwrapSessionKey(wrapped, masterKey);
  sessionKeyCache.set(keyId, sessionKey);
  return sessionKey;
}

function answersAad(examId: string, studentId: string): string {
  return `offline-answers:${examId}:${studentId}`;
}

// ── Exam Package Management ────────────────────────────────────────────────

/**
 * Download and cache the full exam package for offline use.
 * Called when student clicks "Start Exam" in SEB.
 */
export async function downloadExamPackage(
  examId: string,
  options?: { testMode?: boolean; randomSeed?: string | null }
): Promise<ExamStartResponse> {
  const params = new URLSearchParams();
  if (options?.testMode) params.set('test_mode', 'true');
  if (options?.randomSeed) params.set('random_seed', options.randomSeed);
  const qs = params.toString();
  const response = await apiClient.post(`/exams/${examId}/start${qs ? `?${qs}` : ''}`);
  return response.data;
}

export async function cacheExamPackage(pkg: ExamPackage): Promise<void> {
  const db = await getExamDB();
  await db.put('examPackages', pkg);
}

export async function getCachedExamPackage(examId: string): Promise<ExamPackage | undefined> {
  const db = await getExamDB();
  return db.get('examPackages', examId);
}

export async function removeCachedExamPackage(examId: string): Promise<void> {
  const db = await getExamDB();
  await db.delete('examPackages', examId);
}

// ── Offline Exam State Management ──────────────────────────────────────────

/**
 * Persist exam state with answers encrypted at rest (AES-GCM).
 * Runtime callers keep plaintext `answers` in memory; IndexedDB never stores them.
 */
export async function saveOfflineExamState(state: OfflineExamState): Promise<void> {
  const db = await getExamDB();
  const sessionKey = await getSessionKey(state.examId, state.studentId);
  const aad = answersAad(state.examId, state.studentId);
  const answersEncrypted = await encryptPayload(JSON.stringify(state.answers ?? {}), sessionKey, aad);

  const toStore: OfflineExamState = {
    ...state,
    answers: {},
    answersEncrypted,
    lastUpdated: Date.now(),
  };
  await db.put('offlineExams', toStore);
}

async function hydrateOfflineExamState(
  stored: OfflineExamState | undefined
): Promise<OfflineExamState | undefined> {
  if (!stored) return undefined;

  const sessionKey = await getSessionKey(stored.examId, stored.studentId);

  if (stored.answersEncrypted) {
    try {
      const plaintext = await decryptPayload(stored.answersEncrypted, sessionKey);
      const answers = JSON.parse(plaintext) as Record<string, string>;
      const { answersEncrypted: _drop, ...rest } = stored;
      return { ...rest, answers, answersEncrypted: null };
    } catch (error) {
      console.error('[offlineExam] Failed to decrypt answers at rest:', error);
      throw new Error('Failed to decrypt offline exam answers — fail closed');
    }
  }

  // Legacy plaintext rows: return for UX, re-encrypt on next save.
  const legacyAnswers = stored.answers ?? {};
  if (Object.keys(legacyAnswers).length > 0) {
    await saveOfflineExamState({ ...stored, answers: legacyAnswers, answersEncrypted: null });
  }

  return { ...stored, answers: legacyAnswers, answersEncrypted: null };
}

export async function getOfflineExamState(
  examId: string,
  studentId: string
): Promise<OfflineExamState | undefined> {
  const db = await getExamDB();
  const id = `${examId}-${studentId}`;
  const stored = await db.get('offlineExams', id);
  return hydrateOfflineExamState(stored);
}

export async function getAllOfflineExams(studentId: string): Promise<OfflineExamState[]> {
  const db = await getExamDB();
  const all = await db.getAllFromIndex('offlineExams', 'by-student', studentId);
  const hydrated: OfflineExamState[] = [];
  for (const row of all) {
    const state = await hydrateOfflineExamState(row);
    if (state) hydrated.push(state);
  }
  return hydrated;
}

export async function deleteOfflineExamState(examId: string, studentId: string): Promise<void> {
  const db = await getExamDB();
  const id = `${examId}-${studentId}`;
  await db.delete('offlineExams', id);
}

// ── Timer Management ────────────────────────────────────────────────────────

/**
 * Calculate remaining time based on last timer tick.
 * This works even if the app was closed/restarted.
 */
export function calculateTimeRemaining(state: OfflineExamState): number {
  if (state.timerState !== 'running') {
    return state.timeRemainingMs;
  }
  
  const now = Date.now();
  const elapsed = now - state.lastTimerTick;
  const remaining = Math.max(0, state.timeRemainingMs - elapsed);
  
  return remaining;
}

/**
 * Update timer state with new remaining time.
 * Call this periodically (e.g., every second) while exam is running.
 */
export function tickTimer(state: OfflineExamState): OfflineExamState {
  const remaining = calculateTimeRemaining(state);
  
  const newState = {
    ...state,
    timeRemainingMs: remaining,
    lastTimerTick: Date.now(),
    timerState: remaining <= 0 ? 'expired' : state.timerState,
  };
  
  return newState;
}

/**
 * Start the exam timer.
 */
export function startTimer(state: OfflineExamState, durationMinutes: number, timeMultiplier = 1): OfflineExamState {
  const totalMs = durationMinutes * 60 * 1000 * timeMultiplier;
  
  return {
    ...state,
    timeRemainingMs: totalMs,
    timerState: 'running',
    lastTimerTick: Date.now(),
    startedAt: state.startedAt || Date.now(),
  };
}

/**
 * Pause the timer (e.g., if SEB loses focus but exam isn't failed yet).
 */
export function pauseTimer(state: OfflineExamState): OfflineExamState {
  const remaining = calculateTimeRemaining(state);
  
  return {
    ...state,
    timeRemainingMs: remaining,
    timerState: 'paused',
    lastTimerTick: Date.now(),
  };
}

/**
 * Complete the exam (student clicked submit).
 */
export function completeExam(state: OfflineExamState): OfflineExamState {
  return {
    ...state,
    timerState: 'completed',
    isComplete: true,
    timeRemainingMs: 0,
  };
}

// ── SEB Integration ────────────────────────────────────────────────────────

/**
 * SEB (Safe Exam Browser) integration for cheat detection.
 * Detects: exit, minimize, focus loss, blocked shortcuts, suspicious processes.
 */
export class SEBMonitor {
  private examId: string;
  private onViolation: (violation: SEBViolation) => void;
  private onExamFailed: () => void;
  private visibilityChangeHandler: () => void;
  private beforeUnloadHandler: () => void;
  private keydownHandler: (e: KeyboardEvent) => void;
  private intervalId: number | null = null;
  private isMonitoring = false;
  
  // Blocked shortcuts that could be used to escape SEB
  private blockedShortcuts = [
    { key: 'F4', alt: true },      // Alt+F4 (close window)
    { key: 'Tab', alt: true },     // Alt+Tab (switch apps)
    { key: 'Escape', ctrl: true }, // Ctrl+Escape (Start menu)
    { key: 'Delete', ctrl: true, shift: true }, // Ctrl+Shift+Delete (Task Manager)
    { key: 'F12' },                // F12 (DevTools)
    { key: 'I', ctrl: true, shift: true }, // Ctrl+Shift+I (DevTools)
    { key: 'J', ctrl: true, shift: true }, // Ctrl+Shift+J (DevTools)
    { key: 'C', ctrl: true, shift: true }, // Ctrl+Shift+C (DevTools)
    { key: 'U', ctrl: true },      // Ctrl+U (View Source)
    { key: 'S', ctrl: true },      // Ctrl+S (Save Page)
    { key: 'P', ctrl: true },      // Ctrl+P (Print)
    { key: 'N', ctrl: true },      // Ctrl+N (New Window)
    { key: 'T', ctrl: true },      // Ctrl+T (New Tab)
    { key: 'W', ctrl: true },      // Ctrl+W (Close Tab)
    { key: 'R', ctrl: true },      // Ctrl+R (Reload)
  ];
  
  constructor(
    examId: string,
    onViolation: (violation: SEBViolation) => void,
    onExamFailed: () => void
  ) {
    this.examId = examId;
    this.onViolation = onViolation;
    this.onExamFailed = onExamFailed;
    
    this.visibilityChangeHandler = this.handleVisibilityChange.bind(this);
    this.beforeUnloadHandler = this.handleBeforeUnload.bind(this);
    this.keydownHandler = this.handleKeyDown.bind(this);
  }
  
  start(): void {
    if (this.isMonitoring) return;
    this.isMonitoring = true;
    
    // Page Visibility API - detects minimize, tab switch, SEB exit
    document.addEventListener('visibilitychange', this.visibilityChangeHandler);
    
    // Before unload - detects page close/refresh
    window.addEventListener('beforeunload', this.beforeUnloadHandler);
    
    // Keyboard shortcuts blocking
    document.addEventListener('keydown', this.keydownHandler, true); // Capture phase
    
    // Periodic heartbeat/check
    this.intervalId = window.setInterval(() => this.periodicCheck(), 5000);
    
    console.log('[SEBMonitor] Started monitoring for exam:', this.examId);
  }
  
  stop(): void {
    if (!this.isMonitoring) return;
    this.isMonitoring = false;
    
    document.removeEventListener('visibilitychange', this.visibilityChangeHandler);
    window.removeEventListener('beforeunload', this.beforeUnloadHandler);
    document.removeEventListener('keydown', this.keydownHandler, true);
    
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }
    
    console.log('[SEBMonitor] Stopped monitoring');
  }
  
  private handleVisibilityChange(): void {
    if (document.hidden) {
      // Page was minimized or tab switched
      this.recordViolation({
        type: 'minimize',
        timestamp: Date.now(),
        details: 'Page hidden - possible minimize or tab switch',
      });
      
      // In strict SEB mode, this fails the exam immediately
      this.failExam('Exam failed: Application minimized or tab switched');
    }
  }
  
  private handleBeforeUnload(): void {
    // Page is being closed/refreshed
    this.recordViolation({
      type: 'exit',
      timestamp: Date.now(),
      details: 'Page unload - browser/tab closed',
    });
    
    this.failExam('Exam failed: Browser or tab closed');
  }
  
  private handleKeyDown(e: KeyboardEvent): void {
    // Check if this is a blocked shortcut
    for (const shortcut of this.blockedShortcuts) {
      const keyMatch = e.key === shortcut.key || e.code === shortcut.key;
      const altMatch = shortcut.alt === undefined || e.altKey === shortcut.alt;
      const ctrlMatch = shortcut.ctrl === undefined || e.ctrlKey === shortcut.ctrl;
      const shiftMatch = shortcut.shift === undefined || e.shiftKey === shortcut.shift;
      
      if (keyMatch && altMatch && ctrlMatch && shiftMatch) {
        e.preventDefault();
        e.stopPropagation();
        e.stopImmediatePropagation();
        
        this.recordViolation({
          type: 'shortcut_blocked',
          timestamp: Date.now(),
          details: `Blocked shortcut: ${e.key} (ctrl:${e.ctrlKey}, alt:${e.altKey}, shift:${e.shiftKey})`,
        });
        
        // Don't fail exam for shortcut attempts, just log
        break;
      }
    }
  }
  
  private periodicCheck(): void {
    // Check for suspicious processes (if we have access)
    // This is limited in browser but we can check some things
    
    // Check if we're still in fullscreen (SEB requirement)
    if (document.fullscreenElement === null && this.isMonitoring) {
      // Not in fullscreen - possible SEB exit
      this.recordViolation({
        type: 'exit',
        timestamp: Date.now(),
        details: 'Fullscreen lost - possible SEB exit',
      });
      this.failExam('Exam failed: Fullscreen mode lost');
    }
  }
  
  private recordViolation(violation: SEBViolation): void {
    console.warn('[SEBMonitor] Violation:', violation);
    this.onViolation(violation);
  }
  
  private failExam(reason: string): void {
    console.error('[SEBMonitor] Exam failed:', reason);
    this.stop();
    this.onExamFailed();
  }
}

// ── Heartbeat System ───────────────────────────────────────────────────────

/**
 * Queue heartbeat for sending to server when online.
 * Heartbeats allow teacher to monitor student progress in real-time.
 */
export async function queueHeartbeat(payload: HeartbeatPayload): Promise<void> {
  const db = await getExamDB();
  await db.add('heartbeatQueue', {
    examId: payload.examId,
    studentId: payload.studentId,
    payload,
    createdAt: Date.now(),
    attempts: 0,
  });
}

export async function getPendingHeartbeats(examId: string): Promise<HeartbeatQueueItem[]> {
  const db = await getExamDB();
  return db.getAllFromIndex('heartbeatQueue', 'by-exam', examId);
}

export async function removeHeartbeat(id: number): Promise<void> {
  const db = await getExamDB();
  await db.delete('heartbeatQueue', id);
}

export async function processHeartbeatQueue(): Promise<void> {
  const db = await getExamDB();
  const all = await db.getAll('heartbeatQueue');
  
  for (const item of all) {
    try {
      await apiClient.post(`/exams/${item.examId}/heartbeat`, item.payload);
      await removeHeartbeat(item.id!);
    } catch (error) {
      console.warn('Heartbeat failed, will retry:', error);
      // Update attempts
      await db.put('heartbeatQueue', {
        ...item,
        attempts: item.attempts + 1,
      });
      
      // Remove if too many attempts
      if (item.attempts >= 5) {
        await removeHeartbeat(item.id!);
      }
    }
  }
}

// ── Auto-Submit on Time Expiry ─────────────────────────────────────────────

/**
 * Submit exam answers to server.
 * If offline, queues for later submission.
 */
export async function submitExamOffline(
  examId: string,
  studentId: string,
  answers: Record<string, string>,
  submissionId: string,
  testMode = false
): Promise<{ success: boolean; queued: boolean; submissionId?: string }> {
  try {
    const response = await apiClient.post(`/exams/${examId}/submit${testMode ? '?test_mode=true' : ''}`, {
      submission_id: submissionId,
      answers: Object.entries(answers).map(([qId, resp]) => ({
        question_id: qId,
        response: resp,
      })),
    });
    
    return { success: true, queued: false, submissionId: response.data.submission_id };
  } catch {
    // Queue for offline submission — answers encrypted at rest via saveOfflineExamState
    const existing = await getOfflineExamState(examId, studentId);
    await saveOfflineExamState({
      id: `${examId}-${studentId}`,
      examId,
      studentId,
      studentName: existing?.studentName ?? '',
      package: existing?.package ?? null,
      answers,
      answerTimestamps: existing?.answerTimestamps ?? {},
      currentQuestionIndex: existing?.currentQuestionIndex ?? 0,
      timeRemainingMs: 0,
      timerState: 'completed',
      lastTimerTick: Date.now(),
      startedAt: existing?.startedAt ?? Date.now(),
      lastHeartbeat: existing?.lastHeartbeat ?? 0,
      isComplete: true,
      submissionId,
      sebViolations: existing?.sebViolations ?? [],
      lastUpdated: Date.now(),
    });

    return { success: true, queued: true };
  }
}

/**
 * Check if exam time has expired and auto-submit if needed.
 * Call this periodically or when app regains focus.
 */
export async function checkAndAutoSubmit(
  examId: string,
  studentId: string
): Promise<{ submitted: boolean; reason?: string }> {
  const state = await getOfflineExamState(examId, studentId);
  
  if (!state || state.isComplete || state.timerState !== 'running') {
    return { submitted: false, reason: 'Exam not running or already complete' };
  }
  
  const remaining = calculateTimeRemaining(state);
  
  if (remaining <= 0) {
    // Time expired - auto submit
    await submitExamOffline(
      examId,
      studentId,
      state.answers,
      state.submissionId || ''
    );
    
    // Update state to completed
    await saveOfflineExamState({
      ...state,
      timerState: 'expired',
      isComplete: true,
      timeRemainingMs: 0,
    });
    
    return { submitted: true, reason: 'Time expired - auto-submitted' };
  }
  
  return { submitted: false };
}

// ── Utility Functions ──────────────────────────────────────────────────────

export function formatTimeRemaining(ms: number): string {
  if (ms <= 0) return '00:00';
  
  const totalSeconds = Math.ceil(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  
  return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
}

export function isExamExpired(state: OfflineExamState): boolean {
  return calculateTimeRemaining(state) <= 0;
}

export function getExamProgressPercent(state: OfflineExamState): number {
  if (!state.package || state.package.questions.length === 0) return 0;
  
  const answered = Object.keys(state.answers).filter(
    qId => state.answers[qId] && state.answers[qId].trim() !== ''
  ).length;
  
  return Math.round((answered / state.package.questions.length) * 100);
}

// ── Cryptographic Sealing ──────────────────────────────────────────────────

/**
 * Pure seal (no IndexedDB). Used by sealExamSubmission and unit tests.
 */
export async function buildSealedExamSubmission(
  state: OfflineExamState,
  studentName: string,
  sessionKey: CryptoKey,
  completedAt = Date.now()
): Promise<SealedExamSubmission> {
  if (!state.package) {
    throw new Error('No exam package in state');
  }

  const durationMs = completedAt - state.startedAt;
  const autoSubmitted = state.timerState === 'expired';
  const submissionId =
    state.submissionId || `${state.examId}-${state.studentId}-${completedAt}`;
  const timeLimitMs =
    state.package.duration_minutes *
    60 *
    1000 *
    (state.package.settings.time_multiplier || 1);

  const plaintextAnswers: Array<{
    questionId: string;
    response: string;
    answeredAt: number;
    timeSpentMs: number;
  }> = [];
  const sealedAnswers: SealedAnswer[] = [];

  for (const [questionId, response] of Object.entries(state.answers)) {
    const answeredAt = state.answerTimestamps?.[questionId] || state.startedAt;
    const timeSpentMs = answeredAt - state.startedAt;
    const responseHash = await computeHash(response);
    const encrypted = await encryptPayload(
      response,
      sessionKey,
      `answer:${state.examId}:${submissionId}:${questionId}`
    );

    plaintextAnswers.push({ questionId, response, answeredAt, timeSpentMs });
    sealedAnswers.push({
      questionId,
      encrypted,
      responseHash,
      answeredAt,
      timeSpentMs,
    });
  }

  const plaintext = buildSealPlaintext({
    submissionId,
    examId: state.examId,
    studentId: state.studentId,
    studentName,
    startedAt: state.startedAt,
    completedAt,
    durationMs,
    timeLimitMs,
    autoSubmitted,
    answers: plaintextAnswers,
    sealVersion: SEAL_CRYPTO_VERSION,
    sealedAt: completedAt,
  });

  const plaintextCanonical = canonicalJSON(plaintext);
  const contentHash = await computeHash(plaintextCanonical);

  const envelopeAad = `submission:${state.examId}:${submissionId}`;
  const envelope = await encryptPayload(plaintextCanonical, sessionKey, envelopeAad);
  assertEncryptedPayload(envelope, 'sealed submission envelope');

  const encryptedName = await encryptPayload(
    studentName,
    sessionKey,
    `name:${state.examId}:${submissionId}`
  );

  const salt = crypto.getRandomValues(new Uint8Array(SALT_LENGTH));
  const syncHash = await computeHash(contentHash + submissionId);

  return {
    submissionId,
    examId: state.examId,
    studentId: state.studentId,
    studentName: encryptedName,
    startedAt: state.startedAt,
    completedAt,
    durationMs,
    timeLimitMs,
    autoSubmitted,
    answers: sealedAnswers,
    contentHash,
    sealVersion: SEAL_CRYPTO_VERSION,
    sealedAt: completedAt,
    encryption: {
      algorithm: CRYPTO_ALGORITHM,
      ciphertext: envelope.ciphertext,
      iv: envelope.iv,
      version: envelope.version,
      aad: envelope.aad,
      salt: bytesToBase64(salt),
      keyId: `${state.examId}-${state.studentId}`,
    },
    sync: {
      localSealed: true,
      teacherSynced: false,
      serverSynced: false,
      lastSyncAttempt: 0,
      syncHash,
    },
  };
}

/**
 * Seal an exam submission — AES-GCM envelope + per-answer payloads.
 * Stores real {ciphertext, iv, version, aad} (never IV-as-ciphertext).
 */
export async function sealExamSubmission(
  state: OfflineExamState,
  studentName: string
): Promise<SealedExamSubmission> {
  const sessionKey = await getSessionKey(state.examId, state.studentId);
  const sealedSubmission = await buildSealedExamSubmission(state, studentName, sessionKey);

  const db = await getExamDB();
  await db.put('sealedSubmissions', sealedSubmission);

  await queueSync(sealedSubmission.submissionId, 'teacher', sealedSubmission);
  await queueSync(sealedSubmission.submissionId, 'server', sealedSubmission);

  return sealedSubmission;
}

/**
 * Verify a sealed submission's integrity. Fail closed on missing ciphertext.
 */
export async function verifySealedSubmission(
  sealed: SealedExamSubmission,
  sessionKey: CryptoKey
): Promise<{ valid: boolean; reason?: string }> {
  try {
    if (!sealed.encryption?.ciphertext || !sealed.encryption?.iv) {
      return { valid: false, reason: 'Missing ciphertext — fail closed' };
    }

    const envelope: EncryptedPayload = {
      ciphertext: sealed.encryption.ciphertext,
      iv: sealed.encryption.iv,
      version: sealed.encryption.version ?? SEAL_CRYPTO_VERSION,
      aad: sealed.encryption.aad ?? `submission:${sealed.examId}:${sealed.submissionId}`,
    };

    const decrypted = await decryptPayload(envelope, sessionKey);
    const parsed = JSON.parse(decrypted) as unknown;
    const computedHash = await computeHash(canonicalJSON(parsed));
    if (computedHash !== sealed.contentHash) {
      return { valid: false, reason: 'Content hash mismatch — possible tampering' };
    }

    const expectedSyncHash = await computeHash(sealed.contentHash + sealed.submissionId);
    if (sealed.sync.syncHash !== expectedSyncHash) {
      return { valid: false, reason: 'Sync hash mismatch — possible tampering' };
    }

    for (const answer of sealed.answers) {
      assertEncryptedPayload(answer.encrypted, `answer ${answer.questionId}`);
      const response = await decryptPayload(answer.encrypted, sessionKey);
      const responseHash = await computeHash(response);
      if (responseHash !== answer.responseHash) {
        return {
          valid: false,
          reason: `Answer hash mismatch for question ${answer.questionId}`,
        };
      }
    }

    assertEncryptedPayload(sealed.studentName, 'studentName');
    await decryptPayload(sealed.studentName, sessionKey);

    return { valid: true };
  } catch (error) {
    return { valid: false, reason: `Verification failed: ${error}` };
  }
}

/**
 * Decrypt a sealed submission for grading (teacher/server only).
 * Requires the session key. Returns null on any crypto/integrity failure.
 */
export async function decryptSealedSubmission(
  sealed: SealedExamSubmission,
  sessionKey: CryptoKey
): Promise<{
  submission: {
    submissionId: string;
    examId: string;
    studentId: string;
    studentName: string;
    startedAt: number;
    completedAt: number;
    durationMs: number;
    timeLimitMs: number;
    autoSubmitted: boolean;
    contentHash: string;
    sealVersion: number;
    sealedAt: number;
  };
  answers: Array<{ questionId: string; response: string; answeredAt: number; timeSpentMs: number }>;
} | null> {
  try {
    if (!sealed.encryption?.ciphertext || !sealed.encryption?.iv) {
      throw new Error('Missing ciphertext — fail closed');
    }

    const envelope: EncryptedPayload = {
      ciphertext: sealed.encryption.ciphertext,
      iv: sealed.encryption.iv,
      version: sealed.encryption.version ?? SEAL_CRYPTO_VERSION,
      aad: sealed.encryption.aad ?? `submission:${sealed.examId}:${sealed.submissionId}`,
    };

    const decryptedEnvelope = await decryptPayload(envelope, sessionKey);
    const parsed = JSON.parse(decryptedEnvelope) as Record<string, unknown>;
    const computedHash = await computeHash(canonicalJSON(parsed));
    if (computedHash !== sealed.contentHash) {
      throw new Error('Content hash mismatch - submission tampered');
    }

    assertEncryptedPayload(sealed.studentName, 'studentName');
    const studentName = await decryptPayload(sealed.studentName, sessionKey);

    const decryptedAnswers = [];
    for (const answer of sealed.answers) {
      assertEncryptedPayload(answer.encrypted, `answer ${answer.questionId}`);
      const response = await decryptPayload(answer.encrypted, sessionKey);
      const responseHash = await computeHash(response);
      if (responseHash !== answer.responseHash) {
        throw new Error(`Answer hash mismatch for question ${answer.questionId}`);
      }
      decryptedAnswers.push({
        questionId: answer.questionId,
        response,
        answeredAt: answer.answeredAt,
        timeSpentMs: answer.timeSpentMs,
      });
    }

    return {
      submission: {
        submissionId: sealed.submissionId,
        examId: sealed.examId,
        studentId: sealed.studentId,
        studentName,
        startedAt: sealed.startedAt,
        completedAt: sealed.completedAt,
        durationMs: sealed.durationMs,
        timeLimitMs: sealed.timeLimitMs,
        autoSubmitted: sealed.autoSubmitted,
        contentHash: sealed.contentHash,
        sealVersion: sealed.sealVersion,
        sealedAt: sealed.sealedAt,
      },
      answers: decryptedAnswers,
    };
  } catch (error) {
    console.error('Failed to decrypt sealed submission:', error);
    return null;
  }
}

// ── Three-Way Sync Protocol ────────────────────────────────────────────────

/**
 * Queue a sealed submission for sync to teacher or server.
 */
async function queueSync(
  submissionId: string,
  target: 'teacher' | 'server',
  payload: SealedExamSubmission
): Promise<void> {
  const db = await getExamDB();
  await db.add('syncQueue', {
    submissionId,
    target,
    payload,
    status: 'pending',
    createdAt: Date.now(),
    attempts: 0,
  });
}

/**
 * Process the sync queue - attempt to sync pending submissions.
 * Called when online connectivity is available.
 */
export async function processSyncQueue(): Promise<{ synced: number; failed: number }> {
  const db = await getExamDB();
  const pending = await db.getAllFromIndex('syncQueue', 'by-status', 'pending');
  
  let synced = 0;
  let failed = 0;
  
  for (const item of pending) {
    if (item.attempts >= 5) {
      // Max attempts reached
      await db.put('syncQueue', { ...item, status: 'failed' });
      failed++;
      continue;
    }
    
    try {
      if (item.target === 'teacher') {
        // Sync to teacher's device via local network or WebRTC
        await syncToTeacher(item.payload);
      } else if (item.target === 'server') {
        // Sync to central server
        await syncToServer(item.payload);
      }
      
      // Mark as synced
      await db.put('syncQueue', { 
        ...item, 
        status: 'synced',
        syncedAt: Date.now(),
      });
      
      // Update the sealed submission's sync status
      const sealed = await db.get('sealedSubmissions', item.submissionId);
      if (sealed) {
        sealed.sync[`${item.target}Synced`] = true;
        sealed.sync.lastSyncAttempt = Date.now();
        await db.put('sealedSubmissions', sealed);
      }
      
      synced++;
    } catch (error) {
      console.warn(`Sync to ${item.target} failed:`, error);
      await db.put('syncQueue', { 
        ...item, 
        attempts: item.attempts + 1,
        status: item.attempts >= 4 ? 'failed' : 'pending',
      });
      failed++;
    }
  }
  
  return { synced, failed };
}

/**
 * Sync sealed submission to teacher's device (LAN only).
 * F-048: teacherSyncUrl from localStorage must pass private/LAN allowlist validation.
 */
async function syncToTeacher(submission: SealedExamSubmission): Promise<void> {
  const validated = getValidatedTeacherSyncUrl();
  if (!validated.ok) {
    // Fail closed — do not POST educational records to an unvalidated URL.
    throw new Error(validated.reasonKey);
  }

  await fetch(`${validated.url}/api/sync/submission`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(submission),
  });
}

/**
 * Sync sealed submission to central server.
 */
async function syncToServer(submission: SealedExamSubmission): Promise<void> {
  const response = await apiClient.post('/sync/submission', submission);
  return response.data;
}

/**
 * Verify three-way consistency - all three copies must match.
 * Called by teacher during grading to ensure no tampering.
 */
export async function verifyThreeWayConsistency(
  submissionId: string
): Promise<{ consistent: boolean; mismatches: string[] }> {
  const db = await getExamDB();
  const local = await db.get('sealedSubmissions', submissionId);
  
  if (!local) {
    return { consistent: false, mismatches: ['Local copy missing'] };
  }
  
  const mismatches: string[] = [];
  
  // Verify local integrity
  const sessionKey = await getSessionKey(local.examId, local.studentId);
  const localValid = await verifySealedSubmission(local, sessionKey);
  if (!localValid.valid) {
    mismatches.push(`Local: ${localValid.reason}`);
  }
  
  // Try to fetch from teacher (if on same network) — F-048 validated LAN URL only
  try {
    const validated = getValidatedTeacherSyncUrl();
    if (validated.ok) {
      const response = await fetch(`${validated.url}/api/sync/submission/${submissionId}`);
      if (response.ok) {
        const teacherCopy = await response.json();
        if (teacherCopy.contentHash !== local.contentHash) {
          mismatches.push('Teacher copy content hash mismatch');
        }
        if (teacherCopy.sync.syncHash !== local.sync.syncHash) {
          mismatches.push('Teacher copy sync hash mismatch');
        }
      }
    }
  } catch {
    // Teacher not reachable or URL invalid - not a mismatch, just unavailable
  }
  
  // Try to fetch from server
  try {
    const response = await apiClient.get(`/sync/submission/${submissionId}`);
    const serverCopy = response.data;
    if (serverCopy.contentHash !== local.contentHash) {
      mismatches.push('Server copy content hash mismatch');
    }
    if (serverCopy.sync.syncHash !== local.sync.syncHash) {
      mismatches.push('Server copy sync hash mismatch');
    }
  } catch {
    // Server not reachable
  }
  
  return {
    consistent: mismatches.length === 0,
    mismatches,
  };
}

/**
 * Get sync status for a submission.
 */
export async function getSyncStatus(submissionId: string): Promise<{
  local: boolean;
  teacher: boolean;
  server: boolean;
  lastAttempt: number;
}> {
  const db = await getExamDB();
  const sealed = await db.get('sealedSubmissions', submissionId);
  
  if (!sealed) {
    return { local: false, teacher: false, server: false, lastAttempt: 0 };
  }
  
  return {
    local: sealed.sync.localSealed,
    teacher: sealed.sync.teacherSynced,
    server: sealed.sync.serverSynced,
    lastAttempt: sealed.sync.lastSyncAttempt,
  };
}

/**
 * Export sealed submission for manual transfer (USB, etc.)
 * Returns a portable, encrypted file.
 */
export async function exportSealedSubmission(submissionId: string): Promise<Blob> {
  const db = await getExamDB();
  const sealed = await db.get('sealedSubmissions', submissionId);
  
  if (!sealed) {
    throw new Error('Submission not found');
  }
  
  // Wrap in a container with metadata
  const container = {
    version: 1,
    type: 'plannededucation-sealed-submission',
    exportedAt: Date.now(),
    data: sealed,
  };
  
  return new Blob([JSON.stringify(container, null, 2)], { type: 'application/json' });
}

/**
 * Import sealed submission from portable file.
 */
export async function importSealedSubmission(file: File): Promise<SealedExamSubmission> {
  const text = await file.text();
  const container = JSON.parse(text);
  
  if (container.type !== 'plannededucation-sealed-submission') {
    throw new Error('Invalid file type');
  }
  
  const sealed = container.data as SealedExamSubmission;
  
  // Verify integrity
  const sessionKey = await getSessionKey(sealed.examId, sealed.studentId);
  const valid = await verifySealedSubmission(sealed, sessionKey);
  
  if (!valid.valid) {
    throw new Error(`Imported submission failed verification: ${valid.reason}`);
  }
  
  // Store locally
  const db = await getExamDB();
  await db.put('sealedSubmissions', sealed);
  
  return sealed;
}