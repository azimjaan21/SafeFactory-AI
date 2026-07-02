"""
AbnormalBehaviorAnalyzer — SafeFactory integration of pose-based abnormal detection.

Receives SafeFactory worker dicts (already pose-extracted) and runs three
stateful per-person detectors:
  - FallDetector      (fall detection, 92.4% accuracy)
  - RunningDetector   (unsafe running, 91.0% accuracy)
  - InactivityDetector (long-time inactivity, 95.8% accuracy)

Each worker needs a "keypoints_norm" field: np.ndarray (17, 3) with
normalized [0,1] coordinates and confidence values in column 2.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
from django.conf import settings

from .fall_detector import FallDetector, FallEvent
from .inactivity_detector import InactivityDetector, InactivityEvent
from .pose_frame import PoseFrame
from .running_detector import RunningDetector, RunEvent


@dataclass
class BehaviorAlert:
    alert_type: str   # "FALL" | "RUNNING" | "INACTIVITY"
    track_id: int
    frame_idx: int
    timestamp_sec: float
    message: str
    confidence: float
    details: dict


class _PersonDetectors:
    def __init__(self, fps: float):
        self.fall = FallDetector(fps=fps)
        self.running = RunningDetector(fps=fps)


class AbnormalBehaviorAnalyzer:
    """
    Stateful per-person behavior analyzer.

    Call analyze() once per frame with the list of worker dicts from
    SafeFactory's pose extraction pipeline.
    """

    def __init__(self):
        fps = float(getattr(settings, "SAFEFACTORY_STREAM_FPS", 25.0))
        timeout_sec = float(getattr(settings, "SAFEFACTORY_INACTIVITY_TIMEOUT_SECONDS", 300.0))
        self.fps = fps
        self._persons: dict[int, _PersonDetectors] = {}
        self._inact = InactivityDetector(fps=fps, timeout_sec=timeout_sec)
        self._frame_idx = 0

    def analyze(self, workers: list[dict], enabled: set | None = None) -> list[dict]:
        """
        Process one frame. Returns list of SafeFactory event dicts.

        Each worker dict must include "keypoints_norm": np.ndarray (17, 3).
        enabled: subset of {"fall_detection", "running_detection", "inactivity_detection"}.
                 None means all three are active.
        """
        if enabled is None:
            enabled = {"fall_detection", "running_detection", "inactivity_detection"}
        poses = self._build_pose_frames(workers)
        alerts = self._process_poses(poses, enabled)
        self._frame_idx += 1
        return [self._to_event(a) for a in alerts]

    def reset(self):
        self._persons.clear()
        self._inact.reset()
        self._frame_idx = 0

    # ── Internal ──────────────────────────────────────────────────────────────

    def _build_pose_frames(self, workers: list[dict]) -> list[PoseFrame]:
        poses = []
        for w in workers:
            kp_norm = w.get("keypoints_norm")
            if kp_norm is None:
                continue
            track_id = self._parse_track_id(w.get("track_id", -1))
            valid = bool(kp_norm[:, :2].sum() > 0)
            poses.append(PoseFrame(
                keypoints=kp_norm.astype(np.float32),
                frame_idx=self._frame_idx,
                timestamp_sec=self._frame_idx / max(self.fps, 1.0),
                valid=valid,
                track_id=track_id,
            ))
        return poses

    @staticmethod
    def _parse_track_id(track_id) -> int:
        if isinstance(track_id, int):
            return track_id
        if isinstance(track_id, str) and track_id.startswith("w"):
            try:
                return int(track_id[1:])
            except ValueError:
                pass
        try:
            return int(track_id)
        except (TypeError, ValueError):
            return -1

    def _process_poses(self, poses: list[PoseFrame], enabled: set) -> list[BehaviorAlert]:
        alerts: list[BehaviorAlert] = []

        if "inactivity_detection" in enabled:
            for ie in self._inact.update_all(poses):
                alerts.append(BehaviorAlert(
                    alert_type="INACTIVITY",
                    track_id=ie.track_id,
                    frame_idx=ie.frame_idx,
                    timestamp_sec=ie.timestamp_sec,
                    message=f"Worker {ie.track_id} inactive for {ie.duration_sec:.0f}s",
                    confidence=min(1.0, ie.duration_sec / 300.0),
                    details={"duration_sec": ie.duration_sec, "avg_speed": ie.avg_speed},
                ))

        for pose in poses:
            if not pose.valid:
                continue
            tid = pose.track_id

            if tid not in self._persons:
                self._persons[tid] = _PersonDetectors(fps=self.fps)
            det = self._persons[tid]

            if "fall_detection" in enabled:
                fe: Optional[FallEvent] = det.fall.update(pose)
                if fe:
                    self._inact.reset(tid)
                    alerts.append(BehaviorAlert(
                        alert_type="FALL",
                        track_id=tid,
                        frame_idx=fe.frame_idx,
                        timestamp_sec=fe.timestamp_sec,
                        message=f"Worker {tid} fall detected (angle={fe.body_angle:.1f}°, rate={fe.angle_rate:.0f}°/s)",
                        confidence=fe.confidence,
                        details={
                            "body_angle": round(fe.body_angle, 1),
                            "aspect_ratio": round(fe.aspect_ratio, 2),
                            "angle_rate": round(fe.angle_rate, 1),
                            "trigger": fe.trigger,
                        },
                    ))

            if "running_detection" in enabled:
                re: Optional[RunEvent] = det.running.update(pose)
                if re:
                    alerts.append(BehaviorAlert(
                        alert_type="RUNNING",
                        track_id=tid,
                        frame_idx=re.frame_idx,
                        timestamp_sec=re.timestamp_sec,
                        message=f"Worker {tid} unsafe running (freq={re.step_frequency:.1f}Hz)",
                        confidence=re.score,
                        details={
                            "step_frequency": round(re.step_frequency, 2),
                            "horizontal_speed": round(re.horizontal_speed, 4),
                            "score": round(re.score, 3),
                        },
                    ))

        return alerts

    _EVENT_MAP = {
        "FALL":       ("worker_fall_detected",       "fall_detection",       "Danger",  "Worker Fall Detected"),
        "RUNNING":    ("unsafe_running_detected",    "running_detection",    "Warning", "Unsafe Running Detected"),
        "INACTIVITY": ("worker_inactivity_detected", "inactivity_detection", "Warning", "Worker Inactivity Detected"),
    }

    def _to_event(self, alert: BehaviorAlert) -> dict:
        event_type, model_key, severity, label = self._EVENT_MAP.get(
            alert.alert_type,
            ("abnormal_behavior_detected", "fall_detection", "Warning", "Abnormal Behavior"),
        )
        return {
            "event_type": event_type,
            "model_key": model_key,
            "severity": severity,
            "confidence": round(alert.confidence, 3),
            "label": label,
            "details": {
                "subject_id": f"worker:{alert.track_id}",
                "worker_track_id": alert.track_id,
                "message": alert.message,
                **alert.details,
            },
        }
