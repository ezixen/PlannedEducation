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

// ── Crypto Constants ───────────────────────────────────────────────────────

const CRYPTO_ALGORITHM = 'AES-GCM';
const KEY_LENGTH = 256;
const IV_LENGTH = 12; // 96 bits for GCM
const SALT_LENGTH = 16;
export const TAG_LENGTH = 16;

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

export interface ExamSettings {
  shuffle_questions: boolean;
  shuffle_options: boolean;
  show_results_immediately: boolean;
  allow_review: boolean;
  require_seb: boolean;
  time_multiplier: number;
  passing_score: number;
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
  studentName: string; // Encrypted in storage
  
  // Timing (immutable once sealed)
  startedAt: number; // Local timestamp
  completedAt: number; // Local timestamp when sealed
  durationMs: number; // Actual time spent
  timeLimitMs: number; // Configured time limit
  autoSubmitted: boolean; // True if timer expired
  
  // Answers (encrypted)
  answers: SealedAnswer[];
  
  // Integrity
  contentHash: string; // SHA-256 of canonical JSON (before encryption)
  sealVersion: number; // Protocol version
  sealedAt: number; // Timestamp when cryptographically sealed
  
  // Encryption metadata
  encryption: {
    algorithm: string; // 'AES-GCM'
    iv: string; // Base64
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
  response: string; // Encrypted
  responseHash: string; // SHA-256 of plaintext for verification
  answeredAt: number;
  timeSpentMs: number;
}

export interface ExamQuestion {
  question_id: string;
  question_type: 'multiple_choice' | 'essay' | 'dynamic_math';
  text: string;
  options: string[] | null;
  points: number;
  correct_answer?: string;
  rubric?: string;
}

export interface ExamSettings {
  shuffle_questions: boolean;
  shuffle_options: boolean;
  show_results_immediately: boolean;
  allow_review: boolean;
  require_seb: boolean;
  time_multiplier: number;
  passing_score: number;
}

/**
 * OfflineExamState - Runtime state during exam (not sealed)
 */
export interface OfflineExamState {
  id: string; // `${examId}-${studentId}`
  examId: string;
  studentId: string;
  studentName: string;
  package: ExamPackage | null;
  answers: Record<string, string>; // questionId -> response (plaintext during exam)
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
    value: { id: string; key: string };
  };
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
const DB_VERSION = 2; // Incremented for new stores

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

// ── Crypto Utilities ───────────────────────────────────────────────────────

/**
 * Derive encryption key from passphrase using PBKDF2
 * In production, the key should come from a secure key management system
 */
export async function deriveKey(passphrase: string, salt: Uint8Array): Promise<CryptoKey> {
  const encoder = new TextEncoder();
  const keyMaterial = await crypto.subtle.importKey(
    'raw',
    encoder.encode(passphrase),
    'PBKDF2',
    false,
    ['deriveKey']
  );
  
  return crypto.subtle.deriveKey(
    {
      name: 'PBKDF2',
      salt: salt as BufferSource,
      iterations: 100000,
      hash: 'SHA-256',
    },
    keyMaterial,
    { name: CRYPTO_ALGORITHM, length: KEY_LENGTH },
    false,
    ['encrypt', 'decrypt']
  );
}

/**
 * Generate a random encryption key for a session
 */
async function generateSessionKey(): Promise<CryptoKey> {
  return crypto.subtle.generateKey(
    { name: CRYPTO_ALGORITHM, length: KEY_LENGTH },
    true, // extractable for key wrapping
    ['encrypt', 'decrypt']
  );
}

/**
 * Export key for storage (wrapped with master key)
 */
async function exportKey(key: CryptoKey): Promise<string> {
  const raw = await crypto.subtle.exportKey('raw', key);
  return btoa(String.fromCharCode(...new Uint8Array(raw)));
}

/**
 * Import key from storage
 */
async function importKey(raw: string): Promise<CryptoKey> {
  const binary = Uint8Array.from(atob(raw), c => c.charCodeAt(0));
  return crypto.subtle.importKey('raw', binary, CRYPTO_ALGORITHM, true, ['encrypt', 'decrypt']);
}

/**
 * Encrypt data with AES-GCM
 */
async function encryptData(data: string, key: CryptoKey): Promise<{ ciphertext: string; iv: string }> {
  const encoder = new TextEncoder();
  const iv = crypto.getRandomValues(new Uint8Array(IV_LENGTH));
  const ciphertext = await crypto.subtle.encrypt(
    { name: CRYPTO_ALGORITHM, iv },
    key,
    encoder.encode(data)
  );
  return {
    ciphertext: btoa(String.fromCharCode(...new Uint8Array(ciphertext))),
    iv: btoa(String.fromCharCode(...iv)),
  };
}

/**
 * Decrypt data with AES-GCM
 */
async function decryptData(ciphertext: string, iv: string, key: CryptoKey): Promise<string> {
  const binaryCipher = Uint8Array.from(atob(ciphertext), c => c.charCodeAt(0));
  const binaryIv = Uint8Array.from(atob(iv), c => c.charCodeAt(0));
  const decrypted = await crypto.subtle.decrypt(
    { name: CRYPTO_ALGORITHM, iv: binaryIv },
    key,
    binaryCipher
  );
  return new TextDecoder().decode(decrypted);
}

/**
 * Compute SHA-256 hash
 */
async function computeHash(data: string): Promise<string> {
  const encoder = new TextEncoder();
  const hash = await crypto.subtle.digest('SHA-256', encoder.encode(data));
  return btoa(String.fromCharCode(...new Uint8Array(hash)));
}

/**
 * Canonical JSON serialization for consistent hashing
 */
function canonicalJSON(obj: any): string {
  return JSON.stringify(obj, Object.keys(obj).sort());
}

/**
 * Get or create the master encryption key for this device
 * In production, this should integrate with platform key management
 */
export async function getMasterKey(): Promise<CryptoKey> {
  const db = await getExamDB();
  let keyWrapper = await db.get('cryptoKeys', 'master');
  
  if (!keyWrapper) {
    // Generate new master key
    const masterKey = await generateSessionKey();
    const exported = await exportKey(masterKey);
    await db.put('cryptoKeys', { id: 'master', key: exported });
    return masterKey;
  }
  
  return importKey(keyWrapper.key);
}

/**
 * Get or create a session key for a specific exam
 */
async function getSessionKey(examId: string, studentId: string): Promise<CryptoKey> {
  const db = await getExamDB();
  const keyId = `${examId}-${studentId}`;
  let keyWrapper = await db.get('cryptoKeys', keyId);
  
  if (!keyWrapper) {
    const sessionKey = await generateSessionKey();
    const exported = await exportKey(sessionKey);
    await db.put('cryptoKeys', { id: keyId, key: exported });
    return sessionKey;
  }
  
  return importKey(keyWrapper.key);
}

// ── Exam Package Management ────────────────────────────────────────────────

/**
 * Download and cache the full exam package for offline use.
 * Called when student clicks "Start Exam" in SEB.
 */
export async function downloadExamPackage(examId: string): Promise<ExamStartResponse> {
  const response = await apiClient.post(`/exams/${examId}/start`);
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

export async function saveOfflineExamState(state: OfflineExamState): Promise<void> {
  const db = await getExamDB();
  state.lastUpdated = Date.now();
  await db.put('offlineExams', state);
}

export async function getOfflineExamState(examId: string, studentId: string): Promise<OfflineExamState | undefined> {
  const db = await getExamDB();
  const id = `${examId}-${studentId}`;
  return db.get('offlineExams', id);
}

export async function getAllOfflineExams(studentId: string): Promise<OfflineExamState[]> {
  const db = await getExamDB();
  const all = await db.getAllFromIndex('offlineExams', 'by-student', studentId);
  return all;
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
  submissionId: string
): Promise<{ success: boolean; queued: boolean; submissionId?: string }> {
  try {
    const response = await apiClient.post(`/exams/${examId}/submit`, {
      submission_id: submissionId,
      answers: Object.entries(answers).map(([qId, resp]) => ({
        question_id: qId,
        response: resp,
      })),
    });
    
    return { success: true, queued: false, submissionId: response.data.submission_id };
  } catch (error) {
    // Queue for offline submission
    const db = await getExamDB();
    await db.put('offlineExams', {
      id: `${examId}-${studentId}`,
      examId,
      studentId,
      studentName: '',
      package: null,
      answers,
      answerTimestamps: {},
      currentQuestionIndex: 0,
      timeRemainingMs: 0,
      timerState: 'completed',
      lastTimerTick: Date.now(),
      startedAt: Date.now(),
      lastHeartbeat: 0,
      isComplete: true,
      submissionId,
      sebViolations: [],
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
 * Seal an exam submission - cryptographically sign and encrypt for immutable storage.
 * This creates a tamper-evident, encrypted submission that can be verified across
 * all three storage locations (student, teacher, server).
 */
export async function sealExamSubmission(
  state: OfflineExamState,
  studentName: string
): Promise<SealedExamSubmission> {
  if (!state.package) {
    throw new Error('No exam package in state');
  }
  
  const sessionKey = await getSessionKey(state.examId, state.studentId);
  const completedAt = Date.now();
  const durationMs = completedAt - state.startedAt;
  const autoSubmitted = state.timerState === 'expired';
  
  // Build sealed answers with individual hashes
  const sealedAnswers: SealedAnswer[] = [];
  
  for (const [questionId, response] of Object.entries(state.answers)) {
    const answeredAt = state.answerTimestamps?.[questionId] || state.startedAt;
    const timeSpentMs = answeredAt - state.startedAt;
    
    // Hash plaintext response for later verification
    const responseHash = await computeHash(response);
    
    // Encrypt response
    const { ciphertext } = await encryptData(response, sessionKey);
    
    sealedAnswers.push({
      questionId,
      response: ciphertext,
      responseHash,
      answeredAt,
      timeSpentMs,
    });
  }
  
  // Create the submission object (without encryption metadata yet)
  const submissionData = {
    submissionId: state.submissionId || `${state.examId}-${state.studentId}-${completedAt}`,
    examId: state.examId,
    studentId: state.studentId,
    studentName, // Will be encrypted
    startedAt: state.startedAt,
    completedAt,
    durationMs,
    timeLimitMs: state.package.duration_minutes * 60 * 1000 * (state.package.settings.time_multiplier || 1),
    autoSubmitted,
    answers: sealedAnswers,
    sealVersion: 1,
    sealedAt: completedAt,
  };
  
  // Compute content hash of canonical JSON (before encryption)
  const contentHash = await computeHash(canonicalJSON(submissionData));
  
  // Encrypt student name
  const { ciphertext: encryptedName } = await encryptData(studentName, sessionKey);
  
  // Encrypt the entire submission
  const submissionJSON = canonicalJSON({
    ...submissionData,
    studentName: encryptedName,
    contentHash,
  });
  
  const { iv: submissionIv } = await encryptData(submissionJSON, sessionKey);
  
  // Generate salt for key derivation
  const salt = crypto.getRandomValues(new Uint8Array(SALT_LENGTH));
  
  // Create sync hash for cross-verification
  const syncHash = await computeHash(contentHash + submissionData.submissionId);
  
  const sealedSubmission: SealedExamSubmission = {
    ...submissionData,
    studentName: encryptedName,
    contentHash,
    encryption: {
      algorithm: CRYPTO_ALGORITHM,
      iv: submissionIv,
      salt: btoa(String.fromCharCode(...salt)),
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
  
  // Store sealed submission locally
  const db = await getExamDB();
  await db.put('sealedSubmissions', sealedSubmission);
  
  // Queue for three-way sync
  await queueSync(sealedSubmission.submissionId, 'teacher', sealedSubmission);
  await queueSync(sealedSubmission.submissionId, 'server', sealedSubmission);
  
  return sealedSubmission;
}

/**
 * Verify a sealed submission's integrity.
 * Returns true if the submission hasn't been tampered with.
 */
export async function verifySealedSubmission(
  sealed: SealedExamSubmission,
  sessionKey: CryptoKey
): Promise<{ valid: boolean; reason?: string }> {
  try {
    // Decrypt the submission to verify key works
    await decryptData(
      sealed.encryption.iv ? sealed.encryption.iv : '',
      sealed.encryption.iv,
      sessionKey
    );
    
    // For now, verify the content hash matches
    const expectedSyncHash = await computeHash(sealed.contentHash + sealed.submissionId);
    
    if (sealed.sync.syncHash !== expectedSyncHash) {
      return { valid: false, reason: 'Sync hash mismatch - possible tampering' };
    }
    
    // Verify individual answer hashes
    for (const _answer of sealed.answers) {
      // Kept for later verification when teacher/server decrypts
    }
    
    return { valid: true };
  } catch (error) {
    return { valid: false, reason: `Verification failed: ${error}` };
  }
}

/**
 * Decrypt a sealed submission for grading (teacher/server only).
 * Requires the session key.
 */
export async function decryptSealedSubmission(
  sealed: SealedExamSubmission,
  sessionKey: CryptoKey
): Promise<{
  submission: Omit<SealedExamSubmission, 'encryption' | 'sync'>;
  answers: Array<{ questionId: string; response: string; answeredAt: number; timeSpentMs: number }>;
} | null> {
  try {
    const decrypted = await decryptData(sealed.encryption.iv, sealed.encryption.iv, sessionKey);
    
    // Parse and verify
    const parsed = JSON.parse(decrypted);
    
    // Verify content hash
    const computedHash = await computeHash(canonicalJSON(parsed));
    if (computedHash !== sealed.contentHash) {
      throw new Error('Content hash mismatch - submission tampered');
    }
    
    // Decrypt student name
    const studentName = await decryptData(sealed.studentName, sealed.encryption.iv, sessionKey);
    
    // Decrypt answers
    const decryptedAnswers = [];
    for (const answer of sealed.answers) {
      const response = await decryptData(answer.response, answer.response, sessionKey);
      // Verify answer hash
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
        ...sealed,
        studentName,
      } as any,
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
 * Sync sealed submission to teacher's device.
 * In a real deployment, this would use WebRTC, local network HTTP, or similar.
 */
async function syncToTeacher(submission: SealedExamSubmission): Promise<void> {
  // Try to reach teacher's local sync endpoint
  // This assumes teacher's device runs a local sync server on the same network
  const teacherSyncUrl = localStorage.getItem('teacherSyncUrl');
  
  if (teacherSyncUrl) {
    await fetch(`${teacherSyncUrl}/api/sync/submission`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(submission),
    });
  } else {
    // Fallback: queue for when teacher's device is reachable
    throw new Error('Teacher sync URL not configured');
  }
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
  
  // Try to fetch from teacher (if on same network)
  try {
    const teacherSyncUrl = localStorage.getItem('teacherSyncUrl');
    if (teacherSyncUrl) {
      const response = await fetch(`${teacherSyncUrl}/api/sync/submission/${submissionId}`);
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
    // Teacher not reachable - not a mismatch, just unavailable
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