import { apiClient } from '../api';

export interface ProctoringConsentRequest {
  exam_id: string;
  camera_consent: boolean;
  microphone_consent: boolean;
  screen_recording_consent: boolean;
  data_processing_consent: boolean;
  consent_version: string;
}

export interface ProctoringConsentResponse {
  id: string;
  student_id: string;
  exam_id: string;
  consent_given: boolean;
  consent_timestamp: string;
  consent_version: string;
  camera_consent: boolean;
  microphone_consent: boolean;
  screen_recording_consent: boolean;
  data_processing_consent: boolean;
  withdrawn: boolean;
  withdrawn_at: string | null;
}

export interface ProctoringSessionStartRequest {
  exam_id: string;
  submission_id: string;
  camera_enabled: boolean;
  microphone_enabled: boolean;
  screen_recording_enabled: boolean;
}

export interface ProctoringSessionResponse {
  id: string;
  submission_id: string;
  student_id: string;
  exam_id: string;
  consent_given: boolean;
  consent_timestamp: string | null;
  consent_version: string | null;
  camera_enabled: boolean;
  microphone_enabled: boolean;
  screen_recording_enabled: boolean;
  started_at: string;
  ended_at: string | null;
  duration_seconds: number | null;
  total_events: number;
  violation_count: number;
  max_simultaneous_faces: number;
}

export interface ProctoringEventRequest {
  session_id?: string;
  event_type: string;
  severity: 'info' | 'warning' | 'violation';
  event_data?: Record<string, any>;
  screenshot_ref?: string;
  audio_ref?: string;
}

export interface ProctoringEventResponse {
  id: string;
  session_id: string;
  event_type: string;
  timestamp: string;
  severity: string;
  event_data: Record<string, any> | null;
  screenshot_ref: string | null;
  audio_ref: string | null;
}

export interface ProctoringEventBatchRequest {
  session_id: string;
  events: ProctoringEventRequest[];
}

export interface ProctoringStatsResponse {
  total_sessions: number;
  active_sessions: number;
  total_events: number;
  total_violations: number;
  events_by_type: Record<string, number>;
  violations_by_type: Record<string, number>;
}

export interface ProctoringHealthResponse {
  available: boolean;
  service: string;
  features: string[];
}

export const proctoringService = {
  // Consent endpoints
  async giveConsent(request: ProctoringConsentRequest): Promise<ProctoringConsentResponse> {
    const response = await apiClient.post('/proctoring/consent', request);
    return response.data;
  },

  async getConsent(examId: string): Promise<ProctoringConsentResponse> {
    const response = await apiClient.get(`/proctoring/consent/${examId}`);
    return response.data;
  },

  async withdrawConsent(examId: string): Promise<{ status: string; message: string }> {
    const response = await apiClient.delete(`/proctoring/consent/${examId}`);
    return response.data;
  },

  // Session endpoints
  async startSession(request: ProctoringSessionStartRequest): Promise<ProctoringSessionResponse> {
    const response = await apiClient.post('/proctoring/session/start', request);
    return response.data;
  },

  async endSession(sessionId: string): Promise<ProctoringSessionResponse> {
    const response = await apiClient.post(`/proctoring/session/${sessionId}/end`);
    return response.data;
  },

  async getSession(sessionId: string): Promise<ProctoringSessionResponse> {
    const response = await apiClient.get(`/proctoring/session/${sessionId}`);
    return response.data;
  },

  async getSessionBySubmission(submissionId: string): Promise<ProctoringSessionResponse> {
    const response = await apiClient.get(`/proctoring/session/submission/${submissionId}`);
    return response.data;
  },

  // Event endpoints
  async recordEvent(request: ProctoringEventRequest): Promise<ProctoringEventResponse> {
    const response = await apiClient.post('/proctoring/event', request);
    return response.data;
  },

  async recordEventsBatch(request: ProctoringEventBatchRequest): Promise<ProctoringEventResponse[]> {
    const response = await apiClient.post('/proctoring/events/batch', request);
    return response.data;
  },

  async getSessionEvents(
    sessionId: string,
    options?: { event_type?: string; severity?: string; limit?: number; offset?: number }
  ): Promise<ProctoringEventResponse[]> {
    const params = new URLSearchParams();
    if (options?.event_type) params.append('event_type', options.event_type);
    if (options?.severity) params.append('severity', options.severity);
    if (options?.limit) params.append('limit', options.limit.toString());
    if (options?.offset) params.append('offset', options.offset.toString());
    
    const response = await apiClient.get(`/proctoring/session/${sessionId}/events?${params.toString()}`);
    return response.data;
  },

  // Statistics endpoints
  async getStats(examId?: string): Promise<ProctoringStatsResponse> {
    const params = examId ? `?exam_id=${examId}` : '';
    const response = await apiClient.get(`/proctoring/stats${params}`);
    return response.data;
  },

  // Health check
  async healthCheck(): Promise<ProctoringHealthResponse> {
    const response = await apiClient.get('/proctoring/health');
    return response.data;
  },
};

// Event types for proctoring
export const ProctoringEventType = {
  FACE_DETECTED: 'face_detected',
  FACE_LOST: 'face_lost',
  MULTIPLE_FACES: 'multiple_faces',
  EYE_MOVEMENT: 'eye_movement',
  GAZE_OFF_SCREEN: 'gaze_off_screen',
  AUDIO_ANOMALY: 'audio_anomaly',
  TAB_SWITCH: 'tab_switch',
  WINDOW_BLUR: 'window_blur',
  FULLSCREEN_EXIT: 'fullscreen_exit',
  SEB_VIOLATION: 'seb_violation',
  SESSION_START: 'session_start',
  SESSION_END: 'session_end',
} as const;

export type ProctoringEventType = typeof ProctoringEventType[keyof typeof ProctoringEventType];