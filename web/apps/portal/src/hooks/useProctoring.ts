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
  });

  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const faceDetectionIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const audioAnalyserRef = useRef<AnalyserNode | null>(null);
  const eventQueueRef = useRef<any[]>([]);
  const batchIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Check for existing consent on mount
  useEffect(() => {
    checkExistingConsent();
  }, [config.examId]);

  const checkExistingConsent = async () => {
    try {
      const consent = await proctoringService.getConsent(config.examId);
      if (consent.consent_given && !consent.withdrawn) {
        setState(prev => ({ ...prev, consentGiven: true }));
      }
    } catch (err) {
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

  const startSession = async (options: {
    cameraEnabled: boolean;
    microphoneEnabled: boolean;
    screenRecordingEnabled: boolean;
  }) => {
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
      }));

      // Start media streams if enabled
      if (options.cameraEnabled || options.microphoneEnabled) {
        await startMediaStreams(options.cameraEnabled, options.microphoneEnabled);
      }

      // Start event recording
      startEventRecording(session.id);

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

      // Set up audio analysis for background audio monitoring
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

  const startEventRecording = (sessionId: string) => {
    // Record session start event
    queueEvent({
      session_id: sessionId,
      event_type: ProctoringEventType.SESSION_START,
      severity: 'info',
      event_data: { timestamp: new Date().toISOString() },
    });

    // Start face detection if camera enabled
    if (state.cameraEnabled) {
      startFaceDetection(sessionId);
    }

    // Start periodic batch sending
    batchIntervalRef.current = setInterval(() => {
      flushEventQueue(sessionId);
    }, 5000); // Send batch every 5 seconds
  };

  const startFaceDetection = (sessionId: string) => {
    if (!videoRef.current) return;

    const detectFaces = async () => {
      if (!videoRef.current || videoRef.current.readyState < 2) return;

      try {
        // In a real implementation, this would use a face detection library
        // like face-api.js, MediaPipe, or a custom TensorFlow.js model
        // For now, we simulate face detection
        
        // Simulate face detection results
        const faceCount = Math.random() > 0.95 ? 2 : 1; // 5% chance of detecting 2 faces
        const gazeX = Math.random();
        const gazeY = Math.random();
        const gazeOffScreen = gazeX < 0.1 || gazeX > 0.9 || gazeY < 0.1 || gazeY > 0.9;

        // Record face detection event
        queueEvent({
          session_id: sessionId,
          event_type: ProctoringEventType.FACE_DETECTED,
          severity: 'info',
          event_data: {
            face_count: faceCount,
            confidence: 0.9 + Math.random() * 0.1,
            gaze: { x: gazeX, y: gazeY },
          },
        });

        // Record eye movement event
        queueEvent({
          session_id: sessionId,
          event_type: ProctoringEventType.EYE_MOVEMENT,
          severity: 'info',
          event_data: {
            gaze_x: gazeX,
            gaze_y: gazeY,
            timestamp: new Date().toISOString(),
          },
        });

        // Check for gaze off screen
        if (gazeOffScreen) {
          queueEvent({
            session_id: sessionId,
            event_type: ProctoringEventType.GAZE_OFF_SCREEN,
            severity: 'warning',
            event_data: {
              gaze_x: gazeX,
              gaze_y: gazeY,
              duration_ms: 1000,
            },
          });
        }

        // Check for multiple faces
        if (faceCount > 1) {
          queueEvent({
            session_id: sessionId,
            event_type: ProctoringEventType.MULTIPLE_FACES,
            severity: 'violation',
            event_data: {
              face_count: faceCount,
              timestamp: new Date().toISOString(),
            },
          });
          setState(prev => ({ 
            ...prev, 
            violationCount: prev.violationCount + 1,
            maxFaces: Math.max(prev.maxFaces, faceCount),
          }));
          config.onViolation?.({ type: 'multiple_faces', faceCount });
        }

        // Audio anomaly detection
        if (audioAnalyserRef.current) {
          const dataArray = new Uint8Array(audioAnalyserRef.current.frequencyBinCount);
          audioAnalyserRef.current.getByteFrequencyData(dataArray);
          const averageVolume = dataArray.reduce((a, b) => a + b, 0) / dataArray.length;
          
          // Detect unusual audio levels (too loud or sudden spikes)
          if (averageVolume > 180) { // Threshold for anomaly
            queueEvent({
              session_id: sessionId,
              event_type: ProctoringEventType.AUDIO_ANOMALY,
              severity: 'warning',
              event_data: {
                volume_level: averageVolume,
                timestamp: new Date().toISOString(),
              },
            });
          }
        }

      } catch (err) {
        console.error('Face detection error:', err);
      }
    };

    // Run detection every 2 seconds
    faceDetectionIntervalRef.current = setInterval(detectFaces, 2000);
  };

  const queueEvent = (event: any) => {
    eventQueueRef.current.push({
      ...event,
      timestamp: new Date().toISOString(),
    });
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
      // Re-queue events for retry
      eventQueueRef.current.unshift(...events);
    }
  };

  const endSession = async () => {
    if (!state.sessionId) return;

    try {
      // Record session end event
      queueEvent({
        session_id: state.sessionId,
        event_type: ProctoringEventType.SESSION_END,
        severity: 'info',
        event_data: { timestamp: new Date().toISOString() },
      });

      // Flush remaining events
      await flushEventQueue(state.sessionId);

      // Stop intervals
      if (faceDetectionIntervalRef.current) {
        clearInterval(faceDetectionIntervalRef.current);
        faceDetectionIntervalRef.current = null;
      }
      if (batchIntervalRef.current) {
        clearInterval(batchIntervalRef.current);
        batchIntervalRef.current = null;
      }

      // Stop media streams
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track: MediaStreamTrack) => track.stop());
        streamRef.current = null;
      }
      if (videoRef.current) {
        videoRef.current.srcObject = null;
      }

      // Close audio context
      if (audioContextRef.current) {
        await audioContextRef.current.close();
        audioContextRef.current = null;
        audioAnalyserRef.current = null;
      }

      // End session on backend
      await proctoringService.endSession(state.sessionId);

      setState(prev => ({
        ...prev,
        sessionActive: false,
        sessionId: null,
        cameraEnabled: false,
        microphoneEnabled: false,
        screenRecordingEnabled: false,
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

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (faceDetectionIntervalRef.current) {
        clearInterval(faceDetectionIntervalRef.current);
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