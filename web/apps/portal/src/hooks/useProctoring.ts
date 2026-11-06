import { useState, useRef, useEffect, useCallback } from 'react';
import { proctoringService, ProctoringEventType, type ProctoringConsentRequest, type ProctoringSessionStartRequest } from '../services/proctoring';

interface ProctoringConfig {
  examId: string;
  submissionId: string;
  onConsentGiven?: () => void;
  onSessionStarted?: (sessionId: string) => void;
  onSessionEnded?: () => void;
  onViolation?: (event: any) => void;
}

export interface ProctoringMediaOptions {
  cameraEnabled: boolean;
  microphoneEnabled: boolean;
  screenRecordingEnabled: boolean;
}

interface ProctoringState {
  consentGiven: boolean;
  sessionActive: boolean;
  sessionId: string | null;
  cameraEnabled: boolean;
  microphoneEnabled: boolean;
  screenRecordingEnabled: boolean;
  error: string | null;
  events: any[];
  violationCount: number;
  maxFaces: number;
  /** Face/gaze ML is not available; camera is preview-only / manual review. */
  faceDetectionMode: 'unavailable' | 'manual_review';
}

export function useProctoring(config: ProctoringConfig) {
  const [state, setState] = useState<ProctoringState>({
    consentGiven: false,
    sessionActive: false,
    sessionId: null,
    cameraEnabled: false,
    microphoneEnabled: false,
    screenRecordingEnabled: false,
    error: null,
    events: [],
    violationCount: 0,
    maxFaces: 1,
    faceDetectionMode: 'unavailable',
  });

  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const audioMonitorIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const audioAnalyserRef = useRef<AnalyserNode | null>(null);
  const eventQueueRef = useRef<any[]>([]);
  const batchIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Check for existing consent on mount
  useEffect(() => {
    checkExistingConsent();
  }, [config.examId]);

  // F-019: always attach stream to video element when both are available
  useEffect(() => {
    const video = videoRef.current;
    const stream = streamRef.current;
    if (video && stream && state.cameraEnabled) {
      if (video.srcObject !== stream) {
        video.srcObject = stream;
      }
    }
  }, [state.cameraEnabled, state.sessionActive]);

  const checkExistingConsent = async () => {
    try {
      const consent = await proctoringService.getConsent(config.examId);
      if (consent.consent_given && !consent.withdrawn) {
        setState(prev => ({ ...prev, consentGiven: true }));
      }
    } catch {
      // No consent found, that's fine
    }
  };

  const giveConsent = async (consentData: Omit<ProctoringConsentRequest, 'exam_id'>) => {
    try {
      setState(prev => ({ ...prev, error: null }));
      const request: ProctoringConsentRequest = {
        exam_id: config.examId,
        ...consentData,
      };
      await proctoringService.giveConsent(request);
      setState(prev => ({ ...prev, consentGiven: true }));
      config.onConsentGiven?.();
    } catch (err: any) {
      setState(prev => ({ ...prev, error: err.response?.data?.detail || 'Failed to give consent' }));
      throw err;
    }
  };

  const withdrawConsent = async () => {
    try {
      await proctoringService.withdrawConsent(config.examId);
      setState(prev => ({ ...prev, consentGiven: false, sessionActive: false, sessionId: null }));
    } catch (err: any) {
      setState(prev => ({ ...prev, error: err.response?.data?.detail || 'Failed to withdraw consent' }));
      throw err;
    }
  };

  const startSession = async (options: ProctoringMediaOptions) => {
    if (!state.consentGiven) {
      throw new Error('Consent required before starting session');
    }

    try {
      setState(prev => ({ ...prev, error: null }));
      const request: ProctoringSessionStartRequest = {
        exam_id: config.examId,
        submission_id: config.submissionId,
        camera_enabled: options.cameraEnabled,
        microphone_enabled: options.microphoneEnabled,
        screen_recording_enabled: options.screenRecordingEnabled,
      };
      const session = await proctoringService.startSession(request);

      setState(prev => ({
        ...prev,
        sessionActive: true,
        sessionId: session.id,
        cameraEnabled: options.cameraEnabled,
        microphoneEnabled: options.microphoneEnabled,
        screenRecordingEnabled: options.screenRecordingEnabled,
        faceDetectionMode: options.cameraEnabled ? 'manual_review' : 'unavailable',
      }));

      // Start media streams if enabled
      if (options.cameraEnabled || options.microphoneEnabled) {
        await startMediaStreams(options.cameraEnabled, options.microphoneEnabled);
      }

      // F-019: pass options explicitly — do not read stale React state
      startEventRecording(session.id, options);

      config.onSessionStarted?.(session.id);
    } catch (err: any) {
      setState(prev => ({ ...prev, error: err.response?.data?.detail || 'Failed to start session' }));
      throw err;
    }
  };

  const startMediaStreams = async (camera: boolean, microphone: boolean) => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: camera,
        audio: microphone,
      });
      streamRef.current = stream;
      if (videoRef.current && camera) {
        videoRef.current.srcObject = stream;
      }

      if (microphone) {
        setupAudioAnalysis(stream);
      }
    } catch (err) {
      console.error('Media stream error:', err);
      setState(prev => ({ ...prev, error: 'Camera/Microphone access denied' }));
      throw err;
    }
  };

  const setupAudioAnalysis = (stream: MediaStream) => {
    try {
      audioContextRef.current = new AudioContext();
      const source = audioContextRef.current.createMediaStreamSource(stream);
      audioAnalyserRef.current = audioContextRef.current.createAnalyser();
      audioAnalyserRef.current.fftSize = 2048;
      source.connect(audioAnalyserRef.current);
    } catch (err) {
      console.error('Audio analysis setup failed:', err);
    }
  };

  const startEventRecording = (sessionId: string, options: ProctoringMediaOptions) => {
    queueEvent({
      session_id: sessionId,
      event_type: ProctoringEventType.SESSION_START,
      severity: 'info',
      event_data: {
        timestamp: new Date().toISOString(),
        camera_enabled: options.cameraEnabled,
        microphone_enabled: options.microphoneEnabled,
        screen_recording_enabled: options.screenRecordingEnabled,
        face_detection_mode: options.cameraEnabled ? 'manual_review' : 'unavailable',
      },
    });

    // F-019: do not simulate face/gaze with Math.random.
    // Emit a single labeled unavailable/manual-review notice; no fake violation evidence.
    if (options.cameraEnabled) {
      queueEvent({
        session_id: sessionId,
        event_type: ProctoringEventType.FACE_DETECTED,
        severity: 'info',
        event_data: {
          face_detection_mode: 'manual_review',
          available: false,
          note: 'Automated face/gaze detection is unavailable; camera preview is for manual teacher review only.',
        },
      });
    }

    if (options.microphoneEnabled) {
      startAudioLevelMonitor(sessionId);
    }

    batchIntervalRef.current = setInterval(() => {
      flushEventQueue(sessionId);
    }, 5000);
  };

  const startAudioLevelMonitor = (sessionId: string) => {
    const checkAudio = () => {
      if (!audioAnalyserRef.current) return;
      const dataArray = new Uint8Array(audioAnalyserRef.current.frequencyBinCount);
      audioAnalyserRef.current.getByteFrequencyData(dataArray);
      const averageVolume = dataArray.reduce((a, b) => a + b, 0) / dataArray.length;

      // Volume telemetry only — not fabricated face/gaze evidence.
      if (averageVolume > 180) {
        queueEvent({
          session_id: sessionId,
          event_type: ProctoringEventType.AUDIO_ANOMALY,
          severity: 'warning',
          event_data: {
            volume_level: Math.round(averageVolume),
            timestamp: new Date().toISOString(),
          },
        });
      }
    };

    audioMonitorIntervalRef.current = setInterval(checkAudio, 2000);
  };

  const queueEvent = (event: any) => {
    const queued = {
      ...event,
      timestamp: new Date().toISOString(),
    };
    eventQueueRef.current.push(queued);
    setState(prev => ({
      ...prev,
      events: [...prev.events, queued],
    }));
  };

  const flushEventQueue = async (sessionId: string) => {
    if (eventQueueRef.current.length === 0) return;

    const events = [...eventQueueRef.current];
    eventQueueRef.current = [];

    try {
      await proctoringService.recordEventsBatch({
        session_id: sessionId,
        events,
      });
    } catch (err) {
      console.error('Failed to send event batch:', err);
      eventQueueRef.current.unshift(...events);
    }
  };

  const endSession = async () => {
    if (!state.sessionId) return;

    try {
      queueEvent({
        session_id: state.sessionId,
        event_type: ProctoringEventType.SESSION_END,
        severity: 'info',
        event_data: { timestamp: new Date().toISOString() },
      });

      await flushEventQueue(state.sessionId);

      if (audioMonitorIntervalRef.current) {
        clearInterval(audioMonitorIntervalRef.current);
        audioMonitorIntervalRef.current = null;
      }
      if (batchIntervalRef.current) {
        clearInterval(batchIntervalRef.current);
        batchIntervalRef.current = null;
      }

      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track: MediaStreamTrack) => track.stop());
        streamRef.current = null;
      }
      if (videoRef.current) {
        videoRef.current.srcObject = null;
      }

      if (audioContextRef.current) {
        await audioContextRef.current.close();
        audioContextRef.current = null;
        audioAnalyserRef.current = null;
      }

      await proctoringService.endSession(state.sessionId);

      setState(prev => ({
        ...prev,
        sessionActive: false,
        sessionId: null,
        cameraEnabled: false,
        microphoneEnabled: false,
        screenRecordingEnabled: false,
        faceDetectionMode: 'unavailable',
      }));

      config.onSessionEnded?.();
    } catch (err: any) {
      setState(prev => ({ ...prev, error: err.response?.data?.detail || 'Failed to end session' }));
      throw err;
    }
  };

  const recordTabSwitch = useCallback((newTabUrl: string) => {
    if (!state.sessionId || !state.sessionActive) return;
    queueEvent({
      session_id: state.sessionId,
      event_type: ProctoringEventType.TAB_SWITCH,
      severity: 'warning',
      event_data: { new_tab: newTabUrl },
    });
  }, [state.sessionId, state.sessionActive]);

  const recordWindowBlur = useCallback(() => {
    if (!state.sessionId || !state.sessionActive) return;
    queueEvent({
      session_id: state.sessionId,
      event_type: ProctoringEventType.WINDOW_BLUR,
      severity: 'warning',
      event_data: { timestamp: new Date().toISOString() },
    });
  }, [state.sessionId, state.sessionActive]);

  const recordFullscreenExit = useCallback(() => {
    if (!state.sessionId || !state.sessionActive) return;
    queueEvent({
      session_id: state.sessionId,
      event_type: ProctoringEventType.FULLSCREEN_EXIT,
      severity: 'violation',
      event_data: { timestamp: new Date().toISOString() },
    });
    setState(prev => ({ ...prev, violationCount: prev.violationCount + 1 }));
    config.onViolation?.({ type: 'fullscreen_exit' });
  }, [state.sessionId, state.sessionActive, config]);

  const recordSEBViolation = useCallback((details: any) => {
    if (!state.sessionId || !state.sessionActive) return;
    queueEvent({
      session_id: state.sessionId,
      event_type: ProctoringEventType.SEB_VIOLATION,
      severity: 'violation',
      event_data: details,
    });
    setState(prev => ({ ...prev, violationCount: prev.violationCount + 1 }));
    config.onViolation?.({ type: 'seb_violation', details });
  }, [state.sessionId, state.sessionActive, config]);

  useEffect(() => {
    return () => {
      if (audioMonitorIntervalRef.current) {
        clearInterval(audioMonitorIntervalRef.current);
      }
      if (batchIntervalRef.current) {
        clearInterval(batchIntervalRef.current);
      }
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track: MediaStreamTrack) => track.stop());
      }
      if (audioContextRef.current) {
        audioContextRef.current.close();
      }
    };
  }, []);

  return {
    ...state,
    videoRef,
    giveConsent,
    withdrawConsent,
    startSession,
    endSession,
    recordTabSwitch,
    recordWindowBlur,
    recordFullscreenExit,
    recordSEBViolation,
  };
}
