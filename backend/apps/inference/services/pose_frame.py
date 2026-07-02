from dataclasses import dataclass

import numpy as np


@dataclass
class PoseFrame:
    keypoints: np.ndarray   # (17, 3): x_norm, y_norm, conf
    frame_idx: int
    timestamp_sec: float
    valid: bool
    track_id: int = -1
