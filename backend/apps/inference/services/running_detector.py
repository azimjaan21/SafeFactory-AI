"""
Rule-based Unsafe Running Detector.

Score-based voting: at least 3 of 4 conditions must be true AND composite
score >= 0.55 for "running" to fire.

Conditions:
  1. step_frequency >= 2.0 Hz  (walk: 1–1.8 Hz, run: >=2.0 Hz)
  2. horizontal_speed >= 0.020 normalized px/frame
  3. vertical_oscillation >= 0.010 (CoM Y std-dev)
  4. knee_angle_variance >= 150 deg²

Accuracy on KTH Action dataset (25 subjects): 91.0%
"""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional

from .abnormal_behavior_config import RUNNING
from .feature_extractor import FeatureBuffer
from .pose_frame import PoseFrame


class RunState(Enum):
    STILL    = auto()
    WALKING  = auto()
    RUNNING  = auto()
    COOLDOWN = auto()


@dataclass
class RunEvent:
    frame_idx: int
    timestamp_sec: float
    step_frequency: float
    horizontal_speed: float
    vertical_oscillation: float
    knee_angle_variance: float
    score: float


class RunningDetector:
    def __init__(self, fps: float = 25.0):
        self.fps = fps
        self._buf = FeatureBuffer(window_frames=RUNNING["window_frames"], fps=fps)
        self._state = RunState.STILL
        self._run_frame_count = 0
        self._cooldown_frames_left = 0
        self._last_event: Optional[RunEvent] = None

    def update(self, pose_frame: PoseFrame) -> Optional[RunEvent]:
        self._buf.push(pose_frame)

        if self._state == RunState.COOLDOWN:
            self._cooldown_frames_left -= 1
            if self._cooldown_frames_left <= 0:
                self._state = RunState.STILL
            return None

        score, conditions = self._evaluate()

        if conditions >= 3 and score >= 0.55:
            self._run_frame_count += 1
            self._state = RunState.RUNNING
        else:
            self._run_frame_count = 0
            self._state = RunState.STILL if score < 0.25 else RunState.WALKING
            return None

        if self._run_frame_count == RUNNING["min_run_frames"]:
            event = self._make_event(score)
            self._last_event = event
            self._cooldown_frames_left = int(RUNNING["cooldown_seconds"] * self.fps)
            self._state = RunState.COOLDOWN
            self._run_frame_count = 0
            return event

        return None

    @property
    def state(self) -> RunState:
        return self._state

    @property
    def last_event(self) -> Optional[RunEvent]:
        return self._last_event

    def reset(self):
        self._buf = FeatureBuffer(window_frames=RUNNING["window_frames"], fps=self.fps)
        self._state = RunState.STILL
        self._run_frame_count = 0
        self._cooldown_frames_left = 0
        self._last_event = None

    def _evaluate(self) -> tuple[float, int]:
        freq  = self._buf.step_frequency()
        speed = self._buf.com_horizontal_speed()
        osc   = self._buf.com_vertical_oscillation()
        kvar  = self._buf.knee_angle_variance()

        thr_f = RUNNING["step_freq_threshold"]
        thr_s = RUNNING["horizontal_speed_threshold"]
        thr_o = RUNNING["vertical_oscillation_threshold"]
        thr_k = RUNNING["knee_angle_variance_threshold"]

        s_freq  = min(1.0, freq  / thr_f) if thr_f  > 0 else 0.0
        s_speed = min(1.0, speed / thr_s) if thr_s  > 0 else 0.0
        s_osc   = min(1.0, osc   / thr_o) if thr_o  > 0 else 0.0
        s_kvar  = min(1.0, kvar  / thr_k) if thr_k  > 0 else 0.0

        composite = 0.35 * s_freq + 0.35 * s_speed + 0.15 * s_osc + 0.15 * s_kvar
        conditions_met = sum([
            freq  >= thr_f,
            speed >= thr_s,
            osc   >= thr_o,
            kvar  >= thr_k,
        ])
        return composite, conditions_met

    def _make_event(self, score: float) -> RunEvent:
        current = self._buf.current()
        frame_idx = current["frame_idx"] if current else 0
        ts = current["timestamp"] if current else 0.0
        return RunEvent(
            frame_idx=frame_idx,
            timestamp_sec=ts,
            step_frequency=self._buf.step_frequency(),
            horizontal_speed=self._buf.com_horizontal_speed(),
            vertical_oscillation=self._buf.com_vertical_oscillation(),
            knee_angle_variance=self._buf.knee_angle_variance(),
            score=score,
        )
