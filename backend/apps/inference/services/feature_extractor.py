"""
Biomechanical feature extraction from PoseFrame sequences.

Pose format: YOLO11s-pose, 17 COCO joints.
All spatial values are normalized image coordinates [0, 1].
Angles are in degrees.
"""

from collections import deque
from typing import Optional

import numpy as np

from .abnormal_behavior_config import KP, KP_VISIBILITY_THRESHOLD
from .pose_frame import PoseFrame


# ── Low-level geometry ────────────────────────────────────────────────────────

def _xy(kps: np.ndarray, i: int) -> np.ndarray:
    return kps[i, :2]

def _mid(kps: np.ndarray, a: int, b: int) -> np.ndarray:
    return (_xy(kps, a) + _xy(kps, b)) / 2.0

def _angle_deg(v1: np.ndarray, v2: np.ndarray) -> float:
    n1, n2 = np.linalg.norm(v1), np.linalg.norm(v2)
    if n1 < 1e-6 or n2 < 1e-6:
        return 0.0
    cos = np.clip(np.dot(v1, v2) / (n1 * n2), -1.0, 1.0)
    return float(np.degrees(np.arccos(cos)))

def _joint_angle(kps: np.ndarray, a: int, b: int, c: int) -> float:
    return _angle_deg(_xy(kps, a) - _xy(kps, b), _xy(kps, c) - _xy(kps, b))

def _vis(kps: np.ndarray, *indices: int) -> bool:
    return all(kps[i, 2] >= KP_VISIBILITY_THRESHOLD for i in indices)


# ── Per-frame features ────────────────────────────────────────────────────────

def body_tilt_angle(kps: np.ndarray) -> float:
    """Angle of spine (mid_hip → mid_shoulder) from vertical. 0°=upright, 90°=fallen."""
    mid_hip = _mid(kps, KP["l_hip"], KP["r_hip"])
    mid_shoulder = _mid(kps, KP["l_shoulder"], KP["r_shoulder"])
    spine = mid_shoulder - mid_hip
    vertical = np.array([0.0, -1.0])
    return _angle_deg(spine, vertical)

def hip_height_normalized(kps: np.ndarray) -> float:
    """Y-coordinate of mid-hip (0=top, 1=bottom). Large value → hips low → possible fall."""
    return float(_mid(kps, KP["l_hip"], KP["r_hip"])[1])

def pose_aspect_ratio(kps: np.ndarray) -> float:
    """Bounding-box height/width of visible keypoints. Low value → person is horizontal."""
    vis = kps[kps[:, 2] >= KP_VISIBILITY_THRESHOLD, :2]
    if len(vis) < 4:
        return 1.0
    h = vis[:, 1].max() - vis[:, 1].min()
    w = vis[:, 0].max() - vis[:, 0].min()
    return float(h / w) if w > 1e-4 else 5.0

def center_of_mass_xy(kps: np.ndarray) -> np.ndarray:
    vis = kps[kps[:, 2] >= KP_VISIBILITY_THRESHOLD, :2]
    return vis.mean(axis=0) if len(vis) > 0 else kps[:, :2].mean(axis=0)

def left_knee_angle(kps: np.ndarray) -> float:
    return _joint_angle(kps, KP["l_hip"], KP["l_knee"], KP["l_ankle"])

def right_knee_angle(kps: np.ndarray) -> float:
    return _joint_angle(kps, KP["r_hip"], KP["r_knee"], KP["r_ankle"])


# ── Temporal feature buffer ───────────────────────────────────────────────────

class FeatureBuffer:
    """Sliding window of per-frame features with temporal aggregates."""

    def __init__(self, window_frames: int = 30, fps: float = 25.0):
        self.window = window_frames
        self.fps = fps
        self._buf: deque[dict] = deque(maxlen=window_frames)

    def push(self, pose_frame: PoseFrame) -> Optional[dict]:
        if not pose_frame.valid:
            self._buf.append({"valid": False})
            return None

        kps = pose_frame.keypoints
        feat = {
            "valid": True,
            "frame_idx": pose_frame.frame_idx,
            "timestamp": pose_frame.timestamp_sec,
            "body_tilt_angle": body_tilt_angle(kps),
            "hip_height": hip_height_normalized(kps),
            "aspect_ratio": pose_aspect_ratio(kps),
            "com_xy": center_of_mass_xy(kps),
            "l_knee_angle": left_knee_angle(kps),
            "r_knee_angle": right_knee_angle(kps),
            "kps": kps,
        }
        self._buf.append(feat)
        return feat

    def _valid(self) -> list[dict]:
        return [f for f in self._buf if f.get("valid")]

    def fall_velocity(self, window: int = 6) -> float:
        """Hip drop rate over last `window` valid frames (positive = downward)."""
        v = self._valid()
        n = min(window, len(v))
        if n < 2:
            return 0.0
        h = [f["hip_height"] for f in v[-n:]]
        return float((h[-1] - h[0]) / (n - 1))

    def com_horizontal_speed(self) -> float:
        """Mean absolute horizontal CoM displacement per frame."""
        v = self._valid()
        if len(v) < 2:
            return 0.0
        xs = np.array([f["com_xy"][0] for f in v])
        return float(np.abs(np.diff(xs)).mean())

    def com_vertical_oscillation(self) -> float:
        """Std-dev of vertical CoM position (bounce amplitude)."""
        v = self._valid()
        if len(v) < 4:
            return 0.0
        ys = np.array([f["com_xy"][1] for f in v])
        return float(ys.std())

    def step_frequency(self) -> float:
        """Step frequency (Hz) via zero-crossings of (L_knee - R_knee) difference."""
        v = self._valid()
        if len(v) < 6:
            return 0.0
        diff = np.array([f["l_knee_angle"] - f["r_knee_angle"] for f in v])
        zc = np.where(np.diff(np.sign(diff)))[0]
        dur = len(v) / self.fps
        return float(len(zc) / (2.0 * dur)) if dur > 0 else 0.0

    def knee_angle_variance(self) -> float:
        """Combined variance of both knee angles over the window."""
        v = self._valid()
        if len(v) < 4:
            return 0.0
        l = np.array([f["l_knee_angle"] for f in v])
        r = np.array([f["r_knee_angle"] for f in v])
        return float(np.var(l) + np.var(r))

    def mean_keypoint_displacement(self) -> float:
        """Mean per-frame displacement of all visible keypoints. Near-zero → stationary."""
        v = self._valid()
        if len(v) < 2:
            return 0.0
        disps = []
        for i in range(1, len(v)):
            kp0 = v[i - 1]["kps"]
            kp1 = v[i]["kps"]
            mask = (kp0[:, 2] >= KP_VISIBILITY_THRESHOLD) & (kp1[:, 2] >= KP_VISIBILITY_THRESHOLD)
            if mask.sum() == 0:
                continue
            d = np.linalg.norm(kp1[mask, :2] - kp0[mask, :2], axis=1)
            disps.append(d.mean())
        return float(np.mean(disps)) if disps else 0.0

    def current(self) -> Optional[dict]:
        for f in reversed(self._buf):
            if f.get("valid"):
                return f
        return None
