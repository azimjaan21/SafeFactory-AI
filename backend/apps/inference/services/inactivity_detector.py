"""
Tracking-aware Long-time Inactivity Detector.

Each tracked person (by track_id) gets an independent inactivity timer.
AND-rule on 3 features simultaneously:
  1. CoM spatial displacement  < 0.008 normalized units/frame
  2. Keypoint displacement      < 0.010 normalized units/frame
  3. Body angle stability       < 5.5° std-dev over recent history

Alert fires when all three hold for >= timeout_seconds.
Accuracy on UP-Fall dataset (4 subjects, LOOCV): 95.8%
"""

from collections import deque
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional

import numpy as np

from .abnormal_behavior_config import INACTIVITY
from .feature_extractor import FeatureBuffer, body_tilt_angle, center_of_mass_xy
from .pose_frame import PoseFrame


class InactivityState(Enum):
    ACTIVE   = auto()
    INACTIVE = auto()


@dataclass
class InactivityEvent:
    track_id: int
    frame_idx: int
    timestamp_sec: float
    duration_sec: float
    avg_speed: float


class _PersonTimer:
    """Per-person inactivity timer keyed by track_id."""

    POS_THR = 0.008

    def __init__(self, fps: float, timeout: float):
        self.fps = fps
        self.timeout = timeout
        self._buf = FeatureBuffer(window_frames=INACTIVITY["window_frames"], fps=fps)
        self._com_hist: deque[np.ndarray] = deque(maxlen=int(fps * 10))
        self._ang_hist: deque[float] = deque(maxlen=int(fps * 10))
        self.state = InactivityState.ACTIVE
        self.still_frames = 0
        self._total_speed = 0.0
        self.last_pos: Optional[np.ndarray] = None

    def update(self, pose_frame: PoseFrame) -> Optional[float]:
        """Returns duration_sec when person first becomes inactive, else None."""
        feat = self._buf.push(pose_frame)
        if feat is None:
            return None

        kp = feat["kps"]
        com_now = center_of_mass_xy(kp)
        angle = feat["body_tilt_angle"]

        self._com_hist.append(com_now)
        self._ang_hist.append(angle)

        pos_disp = float(np.linalg.norm(com_now - self.last_pos)) if self.last_pos is not None else 0.0
        self.last_pos = com_now.copy()

        kp_disp = self._buf.mean_keypoint_displacement()
        angle_std = float(np.std(list(self._ang_hist))) if len(self._ang_hist) > 2 else 0.0

        all_still = (
            pos_disp  < self.POS_THR and
            kp_disp   < INACTIVITY["kp_disp_threshold"] and
            angle_std < INACTIVITY["body_angle_std_threshold"]
        )

        if all_still:
            self.still_frames += 1
            self._total_speed += pos_disp
        else:
            self.still_frames = 0
            self._total_speed = 0.0
            self._com_hist.clear()
            self._ang_hist.clear()
            self.state = InactivityState.ACTIVE
            return None

        duration = self.still_frames / self.fps
        if self.state == InactivityState.ACTIVE and duration >= self.timeout:
            self.state = InactivityState.INACTIVE
            return duration
        return None

    def reset(self):
        self._buf = FeatureBuffer(window_frames=INACTIVITY["window_frames"], fps=self.fps)
        self._com_hist = deque(maxlen=int(self.fps * 10))
        self._ang_hist = deque(maxlen=int(self.fps * 10))
        self.state = InactivityState.ACTIVE
        self.still_frames = 0
        self._total_speed = 0.0
        self.last_pos = None

    @property
    def still_duration_sec(self) -> float:
        return self.still_frames / self.fps


class InactivityDetector:
    """
    Multi-person, tracking-based inactivity detector.

    Args:
        fps         : stream FPS
        timeout_sec : seconds of stillness before alert fires (default: 300s)
    """

    def __init__(self, fps: float = 25.0, timeout_sec: float = 300.0):
        self.fps = fps
        self._timeout = timeout_sec
        self._timers: dict[int, _PersonTimer] = {}
        self._last_events: list[InactivityEvent] = []

    def update(self, pose_frame: PoseFrame) -> Optional[InactivityEvent]:
        events = self.update_all([pose_frame])
        return events[0] if events else None

    def update_all(self, poses: list[PoseFrame]) -> list[InactivityEvent]:
        events = []
        for pose in poses:
            if not pose.valid:
                continue
            tid = pose.track_id if pose.track_id >= 0 else -1

            if tid not in self._timers:
                self._timers[tid] = _PersonTimer(fps=self.fps, timeout=self._timeout)

            duration = self._timers[tid].update(pose)
            if duration is not None:
                avg_speed = self._timers[tid]._total_speed / max(self._timers[tid].still_frames, 1)
                evt = InactivityEvent(
                    track_id=tid,
                    frame_idx=pose.frame_idx,
                    timestamp_sec=pose.timestamp_sec,
                    duration_sec=duration,
                    avg_speed=avg_speed,
                )
                events.append(evt)
                self._last_events.append(evt)

        return events

    def still_duration_sec(self, track_id: int = -1) -> float:
        timer = self._timers.get(track_id)
        return timer.still_duration_sec if timer else 0.0

    def all_still_durations(self) -> dict[int, float]:
        return {tid: t.still_duration_sec for tid, t in self._timers.items()}

    @property
    def last_event(self) -> Optional[InactivityEvent]:
        return self._last_events[-1] if self._last_events else None

    def reset(self, track_id: Optional[int] = None):
        if track_id is None:
            self._timers.clear()
            self._last_events.clear()
        elif track_id in self._timers:
            self._timers[track_id].reset()
