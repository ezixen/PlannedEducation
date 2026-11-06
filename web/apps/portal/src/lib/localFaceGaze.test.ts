import { describe, expect, it } from 'vitest';
import {
  estimateGazeFromLandmarks,
  headPoseFromMatrix,
  irisInEyeRatio,
  IRIS_LEFT_CENTER,
  IRIS_RIGHT_CENTER,
  LEFT_EYE,
  RIGHT_EYE,
} from './localFaceGaze';

function pt(x: number, y: number, z = 0) {
  return { x, y, z };
}

describe('irisInEyeRatio', () => {
  it('returns near-zero when iris is centered in the eye box', () => {
    const r = irisInEyeRatio(
      pt(0.5, 0.5),
      pt(0.4, 0.5),
      pt(0.6, 0.5),
      pt(0.5, 0.4),
      pt(0.5, 0.6)
    );
    expect(r.x).toBeCloseTo(0, 5);
    expect(r.y).toBeCloseTo(0, 5);
  });

  it('flags strong rightward iris displacement', () => {
    const r = irisInEyeRatio(
      pt(0.58, 0.5),
      pt(0.4, 0.5),
      pt(0.6, 0.5),
      pt(0.5, 0.4),
      pt(0.5, 0.6)
    );
    expect(r.x).toBeGreaterThan(0.5);
  });
});

describe('headPoseFromMatrix', () => {
  it('returns zeros for identity', () => {
    const identity = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1];
    const pose = headPoseFromMatrix(identity);
    expect(pose.yawDeg).toBeCloseTo(0, 5);
    expect(pose.pitchDeg).toBeCloseTo(0, 5);
  });
});

describe('estimateGazeFromLandmarks', () => {
  it('returns null when landmark count is incomplete', () => {
    expect(estimateGazeFromLandmarks([])).toBeNull();
  });

  it('detects off-screen when both irises shift the same way (looking aside)', () => {
    const landmarks = Array.from({ length: 478 }, () => pt(0.5, 0.5));
    landmarks[RIGHT_EYE.outer] = pt(0.3, 0.4);
    landmarks[RIGHT_EYE.inner] = pt(0.45, 0.4);
    landmarks[RIGHT_EYE.top] = pt(0.375, 0.35);
    landmarks[RIGHT_EYE.bottom] = pt(0.375, 0.45);
    landmarks[LEFT_EYE.outer] = pt(0.7, 0.4);
    landmarks[LEFT_EYE.inner] = pt(0.55, 0.4);
    landmarks[LEFT_EYE.top] = pt(0.625, 0.35);
    landmarks[LEFT_EYE.bottom] = pt(0.625, 0.45);
    // Both irises hard toward the subject's right (same signed direction).
    landmarks[IRIS_RIGHT_CENTER] = pt(0.44, 0.4);
    landmarks[IRIS_LEFT_CENTER] = pt(0.69, 0.4);

    const gaze = estimateGazeFromLandmarks(landmarks, null);
    expect(gaze).not.toBeNull();
    expect(Math.abs(gaze!.x)).toBeGreaterThan(0.5);
    expect(gaze!.offScreen).toBe(true);
  });
});
