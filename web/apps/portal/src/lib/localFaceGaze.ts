/**
 * Local face + gaze detection (F-019).
 * MediaPipe Face Landmarker runs fully in-browser (WASM) — no cloud ML, no paid APIs.
 * Gaze is estimated from iris landmarks + head-pose compensation.
 */

import { FilesetResolver, FaceLandmarker, type FaceLandmarkerResult } from '@mediapipe/tasks-vision';

export type FaceGazeBackend = 'mediapipe' | 'shape_detection' | 'none';

export interface NormalizedPoint {
  x: number;
  y: number;
  z?: number;
}

export interface GazeEstimate {
  /** Horizontal gaze in [-1, 1] (negative = looking left from subject). */
  x: number;
  /** Vertical gaze in [-1, 1] (negative = looking up). */
  y: number;
  /** True when gaze is outside the on-screen comfort cone. */
  offScreen: boolean;
}

export interface FaceGazeFrame {
  faceCount: number;
  gaze: GazeEstimate | null;
  backend: FaceGazeBackend;
}

/** MediaPipe iris centers (478-landmark set). */
export const IRIS_RIGHT_CENTER = 468;
export const IRIS_LEFT_CENTER = 473;

/** Eye corner / lid landmarks for iris-in-eye ratio. */
export const RIGHT_EYE = { outer: 33, inner: 133, top: 159, bottom: 145 } as const;
export const LEFT_EYE = { outer: 362, inner: 263, top: 386, bottom: 374 } as const;

/** Off-screen thresholds after head-pose compensation (unitless iris ratio). */
export const GAZE_OFF_SCREEN_X = 0.55;
export const GAZE_OFF_SCREEN_Y = 0.5;
/** Head yaw/pitch (degrees) that alone counts as looking away. */
export const HEAD_YAW_OFF_DEG = 28;
export const HEAD_PITCH_OFF_DEG = 22;

function clamp(n: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, n));
}

/**
 * Map iris center into eye box as [-1, 1] for each axis.
 * Pure geometry — unit-tested without WASM.
 */
export function irisInEyeRatio(
  iris: NormalizedPoint,
  outer: NormalizedPoint,
  inner: NormalizedPoint,
  top: NormalizedPoint,
  bottom: NormalizedPoint
): { x: number; y: number } {
  const midX = (outer.x + inner.x) / 2;
  const halfW = Math.max(Math.abs(inner.x - outer.x) / 2, 1e-6);
  const midY = (top.y + bottom.y) / 2;
  const halfH = Math.max(Math.abs(bottom.y - top.y) / 2, 1e-6);
  return {
    x: clamp((iris.x - midX) / halfW, -1.5, 1.5),
    y: clamp((iris.y - midY) / halfH, -1.5, 1.5),
  };
}

/** Extract yaw/pitch (degrees) from a column-major 4×4 facial transform matrix. */
export function headPoseFromMatrix(matrix: number[]): { yawDeg: number; pitchDeg: number } {
  if (!matrix || matrix.length < 16) {
    return { yawDeg: 0, pitchDeg: 0 };
  }
  // Column-major: R = [[m0,m4,m8],[m1,m5,m9],[m2,m6,m10]]
  const r00 = matrix[0];
  const r10 = matrix[1];
  const r20 = matrix[2];
  const r21 = matrix[6];
  const r22 = matrix[10];
  const pitchDeg = (Math.atan2(-r21, r22) * 180) / Math.PI;
  const yawDeg = (Math.atan2(r20, Math.hypot(r00, r10)) * 180) / Math.PI;
  return { yawDeg, pitchDeg };
}

/**
 * Combine binocular iris ratios with head pose → gaze estimate.
 * Subtracts a fraction of head rotation so looking with the head does not
 * double-count as iris "off screen".
 */
export function estimateGazeFromLandmarks(
  landmarks: NormalizedPoint[],
  transformMatrix?: number[] | null
): GazeEstimate | null {
  if (!landmarks || landmarks.length < 478) return null;
  const rIris = landmarks[IRIS_RIGHT_CENTER];
  const lIris = landmarks[IRIS_LEFT_CENTER];
  if (!rIris || !lIris) return null;

  const right = irisInEyeRatio(
    rIris,
    landmarks[RIGHT_EYE.outer],
    landmarks[RIGHT_EYE.inner],
    landmarks[RIGHT_EYE.top],
    landmarks[RIGHT_EYE.bottom]
  );
  const left = irisInEyeRatio(
    lIris,
    landmarks[LEFT_EYE.outer],
    landmarks[LEFT_EYE.inner],
    landmarks[LEFT_EYE.top],
    landmarks[LEFT_EYE.bottom]
  );

  let x = (right.x + left.x) / 2;
  let y = (right.y + left.y) / 2;

  const { yawDeg, pitchDeg } = headPoseFromMatrix(transformMatrix ?? []);
  // ~1/35 maps degrees into iris-ratio space for compensation.
  x -= yawDeg / 35;
  y -= pitchDeg / 35;
  x = clamp(x, -1.5, 1.5);
  y = clamp(y, -1.5, 1.5);

  const headAway =
    Math.abs(yawDeg) >= HEAD_YAW_OFF_DEG || Math.abs(pitchDeg) >= HEAD_PITCH_OFF_DEG;
  const irisAway = Math.abs(x) >= GAZE_OFF_SCREEN_X || Math.abs(y) >= GAZE_OFF_SCREEN_Y;

  return { x, y, offScreen: headAway || irisAway };
}

interface BrowserFaceDetector {
  detect(image: ImageBitmapSource): Promise<Array<{ boundingBox: DOMRectReadOnly }>>;
}

function createShapeDetector(): BrowserFaceDetector | null {
  const FaceDetectorCtor = (globalThis as unknown as {
    FaceDetector?: new (opts?: { fastMode?: boolean; maxDetectedFaces?: number }) => BrowserFaceDetector;
  }).FaceDetector;
  if (typeof FaceDetectorCtor !== 'function') return null;
  try {
    return new FaceDetectorCtor({ fastMode: true, maxDetectedFaces: 10 });
  } catch {
    return null;
  }
}

export interface LocalFaceGazeDetector {
  backend: FaceGazeBackend;
  detect(video: HTMLVideoElement, timestampMs: number): Promise<FaceGazeFrame>;
  close(): void;
}

const WASM_PATH = '/ml/wasm';
const MODEL_PATH = '/ml/face_landmarker.task';

/**
 * Prefer MediaPipe (cross-browser face + gaze). Fall back to Chrome Shape Detection
 * (face count only). Fail closed to backend "none" — never fabricate detections.
 */
export async function createLocalFaceGazeDetector(): Promise<LocalFaceGazeDetector> {
  try {
    const fileset = await FilesetResolver.forVisionTasks(WASM_PATH);
    const landmarker = await FaceLandmarker.createFromOptions(fileset, {
      baseOptions: {
        modelAssetPath: MODEL_PATH,
        delegate: 'GPU',
      },
      runningMode: 'VIDEO',
      numFaces: 10,
      outputFacialTransformationMatrixes: true,
      outputFaceBlendshapes: false,
    });

    return {
      backend: 'mediapipe',
      async detect(video, timestampMs) {
        if (video.readyState < 2) {
          return { faceCount: 0, gaze: null, backend: 'mediapipe' };
        }
        let result: FaceLandmarkerResult;
        try {
          result = landmarker.detectForVideo(video, timestampMs);
        } catch {
          return { faceCount: 0, gaze: null, backend: 'mediapipe' };
        }
        const faceCount = Math.min(result.faceLandmarks?.length ?? 0, 10);
        let gaze: GazeEstimate | null = null;
        if (faceCount >= 1 && result.faceLandmarks[0]) {
          const matrix = result.facialTransformationMatrixes?.[0]?.data as number[] | undefined;
          gaze = estimateGazeFromLandmarks(result.faceLandmarks[0], matrix ?? null);
        }
        return { faceCount, gaze, backend: 'mediapipe' };
      },
      close() {
        landmarker.close();
      },
    };
  } catch (err) {
    console.warn('[localFaceGaze] MediaPipe unavailable, trying Shape Detection', err);
  }

  const shape = createShapeDetector();
  if (shape) {
    return {
      backend: 'shape_detection',
      async detect(video) {
        if (video.readyState < 2) {
          return { faceCount: 0, gaze: null, backend: 'shape_detection' };
        }
        try {
          const faces = await shape.detect(video);
          return {
            faceCount: Math.min(faces.length, 10),
            gaze: null,
            backend: 'shape_detection',
          };
        } catch {
          return { faceCount: 0, gaze: null, backend: 'shape_detection' };
        }
      },
      close() {
        /* Shape Detection has no dispose */
      },
    };
  }

  return {
    backend: 'none',
    async detect() {
      return { faceCount: 0, gaze: null, backend: 'none' };
    },
    close() {},
  };
}
