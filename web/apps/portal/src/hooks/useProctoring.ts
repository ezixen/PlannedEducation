import { useState, useRef, useEffect, useCallback } from 'react';
import { proctoringService, ProctoringEventType, type ProctoringConsentRequest, type ProctoringSessionStartRequest } from '../services/proctoring';
import type { FaceGazeBackend, LocalFaceGazeDetector } from '../lib/localFaceGaze';

interface ProctoringConfig {
  examId: string;
  submissionId: string;
  onConsentGiven?: () => void;
  onSessionStarted?: (sessionId: string) => void;
  onSessionEnded?: () => void;
  onViolation?: (event: unknown) => void;
}

export interface ProctoringMediaOptions {
  cameraEnabled: boolean;
  microphoneEnabled: boolean;
  screenRecordingEnabled: boolean;
}

type FaceDetectionMode = 'unavailable' | 'manual_review' | 'live';

function modeFromBackend(backend: FaceGazeBackend, cameraEnabled: boolean): FaceDetectionMode {
  if (!cameraEnabled) return 'unavailable';
  if (backend === 'none') return 'manual_review';
  return 'live';
}

interface ProctoringState {
  consentGiven: boolean;
  sessionActive: boolean;
  sessionId: string | null;
  cameraEnabled: boolean;
  microphoneEnabled: boolean;
  screenRecordingEnabled: boolean;
  error: string | null;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  events: any[];
  violationCount: number;
  maxFaces: number;
  /** live = local MediaPipe / Shape Detection; manual_review = preview only; unavailable = no camera. */
  faceDetectionMode: FaceDetectionMode;
  /** Latest live face count from local detector (0 when not live). */
  detectedFaceCount: number;
  /** Which local backend is active (mediapipe includes gaze). */
  faceGazeBackend: FaceGazeBackend;
  /** Last gaze sample; null when not estimated. */
  gazeOffScreen: boolean;
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
    detectedFaceCount: 0,
    faceGazeBackend: 'none',
    gazeOffScreen: false,
  });

  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const audioMonitorIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const faceMonitorIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const faceGazeDetectorRef = useRef<LocalFaceGazeDetector | null>(null);
  const lastFaceCountRef = useRef<number | null>(null);
  const lastGazeOffRef = useRef<boolean | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const audioAnalyserRef = useRef<AnalyserNode | null>(null);
  const eventQueueRef = useRef<any[]>([]);
  const batchIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    void checkExistingConsent();
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
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setState(prev => ({ ...prev, error: detail || 'Failed to give consent' }));
      throw err;
    }
  };

  const withdrawConsent = async () => {
    try {
      await proctoringService.withdrawConsent(config.examId);
      setState(prev => ({ ...prev, consentGiven: false, sessionActive: false, sessionId: null }));
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setState(prev => ({ ...prev, error: detail || 'Failed to withdraw consent' }));
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

      let backend: FaceGazeBackend = 'none';
      if (options.cameraEnabled) {
        // Dynamic import keeps MediaPipe out of the default classroom bundle path.
        const { createLocalFaceGazeDetector } = await import('../lib/localFaceGaze');
        const detector = await createLocalFaceGazeDetector();
        faceGazeDetectorRef.current = detector;
        backend = detector.backend;
      } else {
        faceGazeDetectorRef.current = null;
      }
      const faceMode = modeFromBackend(backend, options.cameraEnabled);

      setState(prev => ({
        ...prev,
        sessionActive: true,
        sessionId: session.id,
        cameraEnabled: options.cameraEnabled,
        microphoneEnabled: options.microphoneEnabled,
        screenRecordingEnabled: options.screenRecordingEnabled,
        faceDetectionMode: faceMode,
        faceGazeBackend: backend,
        detectedFaceCount: 0,
        gazeOffScreen: false,
      }));

      if (options.cameraEnabled || options.microphoneEnabled) {
        await startMediaStreams(options.cameraEnabled, options.microphoneEnabled);
      }

      startEventRecording(session.id, options, faceMode, backend);

      config.onSessionStarted?.(session.id);
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setState(prev => ({ ...prev, error: detail || 'Failed to start session' }));
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

  const startEventRecording = (
    sessionId: string,
    options: ProctoringMediaOptions,
    faceMode: FaceDetectionMode,
    backend: FaceGazeBackend
  ) => {
    queueEvent({
      session_id: sessionId,
      event_type: ProctoringEventType.SESSION_START,
      severity: 'info',
      event_data: {
        timestamp: new Date().toISOString(),
        camera_enabled: options.cameraEnabled,
        microphone_enabled: options.microphoneEnabled,
        screen_recording_enabled: options.screenRecordingEnabled,
        face_detection_mode: faceMode,
        face_gaze_backend: backend,
      },
    });

    // F-019: never simulate face/gaze with Math.random — local MediaPipe or Shape Detection only.
    if (options.cameraEnabled && faceMode === 'live') {
      startFaceGazeMonitor(sessionId, backend);
    } else if (options.cameraEnabled) {
      queueEvent({
        session_id: sessionId,
        event_type: ProctoringEventType.FACE_DETECTED,
        severity: 'info',
        event_data: {
          face_detection_mode: 'manual_review',
          available: false,
          note: 'Local face/gaze model unavailable; camera preview is for manual teacher review only.',
        },
      });
    }

    if (options.microphoneEnabled) {
      startAudioLevelMonitor(sessionId);
    }

    batchIntervalRef.current = setInterval(() => {
      void flushEventQueue(sessionId);
    }, 5000);
  };

  const startFaceGazeMonitor = (sessionId: string, backend: FaceGazeBackend) => {
    const detector = faceGazeDetectorRef.current;
    if (!detector) return;

    lastFaceCountRef.current = null;
    lastGazeOffRef.current = null;
    queueEvent({
      session_id: sessionId,
      event_type: ProctoringEventType.FACE_DETECTED,
      severity: 'info',
      event_data: {
        face_detection_mode: 'live',
        face_gaze_backend: backend,
        available: true,
        gaze_enabled: backend === 'mediapipe',
        note:
          backend === 'mediapipe'
            ? 'Local MediaPipe Face Landmarker active (WASM, no cloud). Face count + iris/head-pose gaze.'
            : 'Local Shape Detection API active (face count only; gaze requires MediaPipe assets).',
      },
    });

    const checkFaces = async () => {
      const video = videoRef.current;
      if (!video || video.readyState < 2) return;
      try {
        const frame = await detector.detect(video, performance.now());
        const count = frame.faceCount;
        setState((prev) => ({
          ...prev,
          detectedFaceCount: count,
          gazeOffScreen: frame.gaze?.offScreen ?? false,
        }));

        if (lastFaceCountRef.current !== count) {
          lastFaceCountRef.current = count;
          const overMax = count > 1;
          queueEvent({
            session_id: sessionId,
            event_type: overMax ? ProctoringEventType.MULTIPLE_FACES : ProctoringEventType.FACE_DETECTED,
            severity: overMax ? 'warning' : 'info',
            event_data: {
              face_detection_mode: 'live',
              face_gaze_backend: frame.backend,
              face_count: count,
              timestamp: new Date().toISOString(),
            },
          });
          if (overMax) {
            setState((prev) => ({ ...prev, violationCount: prev.violationCount + 1 }));
            config.onViolation?.({ type: 'face_count', face_count: count });
          }
          if (count === 0) {
            queueEvent({
              session_id: sessionId,
              event_type: ProctoringEventType.FACE_LOST,
              severity: 'warning',
              event_data: {
                face_gaze_backend: frame.backend,
                timestamp: new Date().toISOString(),
              },
            });
          }
        }

        if (frame.gaze) {
          const off = frame.gaze.offScreen;
          if (lastGazeOffRef.current !== off) {
            lastGazeOffRef.current = off;
            queueEvent({
              session_id: sessionId,
              event_type: off ? ProctoringEventType.GAZE_OFF_SCREEN : ProctoringEventType.EYE_MOVEMENT,
              severity: off ? 'warning' : 'info',
              event_data: {
                gaze_x: Number(frame.gaze.x.toFixed(3)),
                gaze_y: Number(frame.gaze.y.toFixed(3)),
                off_screen: off,
                face_gaze_backend: frame.backend,
                timestamp: new Date().toISOString(),
              },
            });
            if (off) {
              setState((prev) => ({ ...prev, violationCount: prev.violationCount + 1 }));
              config.onViolation?.({ type: 'gaze_off_screen', gaze: frame.gaze });
            }
          }
        }
      } catch {
        // Transient detector errors — keep live mode; next tick retries.
      }
    };

    faceMonitorIntervalRef.current = setInterval(() => {
      void checkFaces();
    }, 1000);
  };

  const startAudioLevelMonitor = (sessionId: string) => {
    const checkAudio = () => {
      if (!audioAnalyserRef.current) return;
      const dataArray = new Uint8Array(audioAnalyserRef.current.frequencyBinCount);
      audioAnalyserRef.current.getByteFrequencyData(dataArray);
      const averageVolume = dataArray.reduce((a, b) => a + b, 0) / dataArray.length;

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
        events: events as never,
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
      if (faceMonitorIntervalRef.current) {
        clearInterval(faceMonitorIntervalRef.current);
        faceMonitorIntervalRef.current = null;
      }
      faceGazeDetectorRef.current?.close();
      faceGazeDetectorRef.current = null;
      lastFaceCountRef.current = null;
      lastGazeOffRef.current = null;
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
        faceGazeBackend: 'none',
        detectedFaceCount: 0,
        gazeOffScreen: false,
      }));

      config.onSessionEnded?.();
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setState(prev => ({ ...prev, error: detail || 'Failed to end session' }));
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

  const recordSEBViolation = useCallback((details: unknown) => {
    if (!state.sessionId || !state.sessionActive) return;
    queueEvent({
      session_id: state.sessionId,
      event_type: ProctoringEventType.SEB_VIOLATION,
      severity: 'violation',
      event_data: details as Record<string, unknown>,
    });
    setState(prev => ({ ...prev, violationCount: prev.violationCount + 1 }));
    config.onViolation?.({ type: 'seb_violation', details });
  }, [state.sessionId, state.sessionActive, config]);

  useEffect(() => {
    return () => {
      if (audioMonitorIntervalRef.current) {
        clearInterval(audioMonitorIntervalRef.current);
      }
      if (faceMonitorIntervalRef.current) {
        clearInterval(faceMonitorIntervalRef.current);
      }
      if (batchIntervalRef.current) {
        clearInterval(batchIntervalRef.current);
      }
      faceGazeDetectorRef.current?.close();
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track: MediaStreamTrack) => track.stop());
      }
      if (audioContextRef.current) {
        void audioContextRef.current.close();
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
