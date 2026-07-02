"""
Thresholds for pose-based abnormal behavior detectors.
Calibrated on UP-Fall dataset (4 subjects, LOOCV) and KTH Action dataset.
"""

KP = {
    "nose": 0,
    "l_eye": 1,  "r_eye": 2,
    "l_ear": 3,  "r_ear": 4,
    "l_shoulder": 5,  "r_shoulder": 6,
    "l_elbow": 7,  "r_elbow": 8,
    "l_wrist": 9,  "r_wrist": 10,
    "l_hip": 11,  "r_hip": 12,
    "l_knee": 13,  "r_knee": 14,
    "l_ankle": 15,  "r_ankle": 16,
}

NUM_JOINTS = 17
KP_VISIBILITY_THRESHOLD = 0.2

# Fall detection thresholds
# Rule A: angle-rate gate — falls are rapid (70–140°/sec), lying-down is slow (2–5°/sec)
# Rule B: geometry confirmation — spine tilt + aspect ratio
# Rule C: Butterworth-filtered hip velocity (secondary confirmation)
FALL = {
    "angle_threshold": 70.0,           # spine degrees from vertical (fallen >= 70°)
    "aspect_ratio_threshold": 0.60,    # bbox height/width (horizontal < 0.60)
    "angle_rate_threshold": 65.0,      # deg/sec — rapid fall discriminator
    "angle_rate_window": 15,           # frames to look back for rate calculation
    "vel_threshold": 0.30,             # normalized units/sec downward hip velocity
    "pos_cutoff_hz": 4.0,
    "vel_cutoff_hz": 8.0,
    "min_fall_frames": 4,              # consecutive triggered frames to confirm
    "cooldown_seconds": 3.0,
}

# Running detection thresholds
# Score-based voting: at least 3 of 4 conditions + composite score >= 0.55
RUNNING = {
    "step_freq_threshold": 2.0,                # Hz (walk: 1–1.8, run: >=2.0)
    "horizontal_speed_threshold": 0.020,       # normalized px/frame
    "vertical_oscillation_threshold": 0.010,   # std-dev of CoM Y
    "knee_angle_variance_threshold": 150.0,    # deg² combined L+R variance
    "window_frames": 30,
    "min_run_frames": 10,
    "cooldown_seconds": 1.5,
}

# Inactivity detection thresholds
# AND-rule: all three features must hold simultaneously for >= timeout
INACTIVITY = {
    "kp_disp_threshold": 0.010,         # mean keypoint displacement per frame
    "body_angle_std_threshold": 5.5,    # std-dev of spine angle (degrees)
    "window_frames": 30,
}
