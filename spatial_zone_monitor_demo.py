import cv2
import numpy as np
import json
import os
import time
import uuid
from datetime import datetime
from ultralytics import YOLO
import argparse


# =========================
# DEFAULT SETTINGS
# =========================

DEFAULT_VIDEO = r"C:\Users\dalab\Desktop\azimjaan21\SafeFactory System\#Project_Safety_AI\3. Work Area Detection\zone3.mp4"

DEFAULT_POSE_MODEL = "yolo11m-pose.pt"

DEFAULT_DANGER_ZONES = "danger_zones.json"
DEFAULT_WORK_ZONES = "work_zones.json"
DEFAULT_OUTPUT_DIR = "safety_reports"


# =========================
# POSE SKELETON
# =========================

SKELETON_CONNECTIONS = [
    (0, 1), (0, 2), (1, 3), (2, 4),
    (5, 6), (5, 7), (7, 9),
    (6, 8), (8, 10),
    (5, 11), (6, 12), (11, 12),
    (11, 13), (13, 15),
    (12, 14), (14, 16),
]


# =========================
# BASIC UTILS
# =========================

def load_zones(json_path):
    if not os.path.exists(json_path):
        return None

    with open(json_path, "r") as f:
        return json.load(f)


def save_zones(zones, json_path):
    with open(json_path, "w") as f:
        json.dump(zones, f, indent=2)


def point_in_polygon(point, polygon):
    """
    Ray-casting point-in-polygon check.
    point = [x, y]
    polygon = [[x1, y1], [x2, y2], ...]
    """
    x, y = point
    inside = False
    n = len(polygon)

    if n < 3:
        return False

    px1, py1 = polygon[0]

    for i in range(n + 1):
        px2, py2 = polygon[i % n]

        if y > min(py1, py2):
            if y <= max(py1, py2):
                if x <= max(px1, px2):
                    if py1 != py2:
                        xinters = (y - py1) * (px2 - px1) / (py2 - py1 + 1e-6) + px1
                        if px1 == px2 or x <= xinters:
                            inside = not inside

        px1, py1 = px2, py2

    return inside


def get_worker_anchor(keypoints):
    """
    Worker location anchor point.

    Priority:
    1. Ankles: left ankle 15, right ankle 16
    2. Hips: left hip 11, right hip 12

    This is better than head/center because zone checking should use
    worker ground position.
    """

    # Try ankles first
    ankle_points = []

    for idx in [15, 16]:
        if idx < len(keypoints):
            x, y = keypoints[idx][0], keypoints[idx][1]
            if x > 0 and y > 0:
                ankle_points.append((x, y))

    if ankle_points:
        avg_x = sum(p[0] for p in ankle_points) / len(ankle_points)
        avg_y = sum(p[1] for p in ankle_points) / len(ankle_points)
        return [int(avg_x), int(avg_y)]

    # Fallback to hips
    hip_points = []

    for idx in [11, 12]:
        if idx < len(keypoints):
            x, y = keypoints[idx][0], keypoints[idx][1]
            if x > 0 and y > 0:
                hip_points.append((x, y))

    if hip_points:
        avg_x = sum(p[0] for p in hip_points) / len(hip_points)
        avg_y = sum(p[1] for p in hip_points) / len(hip_points)
        return [int(avg_x), int(avg_y)]

    return None


# =========================
# ZONE DRAWING
# =========================

def draw_polygon_zones(frame, zones, color, label, alpha=0.25):
    """
    Draw transparent polygon zone.
    """
    if not zones:
        return frame

    overlay = frame.copy()

    for idx, zone in enumerate(zones):
        pts = np.array(zone, np.int32).reshape((-1, 1, 2))

        cv2.fillPoly(overlay, [pts], color)
        cv2.polylines(frame, [pts], True, color, 3)

        x, y = pts[0][0]
        cv2.putText(
            frame,
            f"{label} {idx + 1}",
            (int(x), max(int(y) - 10, 25)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            color,
            2,
        )

    cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
    return frame


def draw_all_zones(frame, danger_zones, work_zones):
    """
    Green work zones first.
    Red danger zones second.
    Danger zone has visual priority.
    """
    frame = draw_polygon_zones(
        frame,
        work_zones,
        color=(0, 255, 0),
        label="WORK ZONE",
        alpha=0.22,
    )

    frame = draw_polygon_zones(
        frame,
        danger_zones,
        color=(0, 0, 255),
        label="DANGER ZONE",
        alpha=0.30,
    )

    return frame


def draw_zones_gui(video_path, zone_name, color):
    """
    GUI for drawing polygon zones on first video frame.

    Controls:
    Left click  = add point
    Right click = finish polygon
    s           = save and exit
    ESC         = cancel
    """

    current_polygon = []
    polygons = []

    window_name = (
        f"Draw {zone_name} Zones | "
        f"L-click add | R-click finish | s save | ESC cancel"
    )

    def mouse_callback(event, x, y, flags, param):
        nonlocal current_polygon, polygons

        if event == cv2.EVENT_LBUTTONDOWN:
            current_polygon.append((x, y))

        elif event == cv2.EVENT_RBUTTONDOWN:
            if len(current_polygon) >= 3:
                polygons.append(current_polygon.copy())
                current_polygon = []

    cap = cv2.VideoCapture(video_path)
    ret, frame = cap.read()
    cap.release()

    if not ret:
        print("Failed to read video for zone drawing.")
        return []

    cv2.namedWindow(window_name)
    cv2.setMouseCallback(window_name, mouse_callback)

    print(f"\nDrawing {zone_name} zones")
    print("Left click  : add point")
    print("Right click : finish polygon")
    print("s           : save and exit")
    print("ESC         : cancel")

    while True:
        display = frame.copy()
        overlay = display.copy()

        for poly in polygons:
            pts = np.array(poly, np.int32).reshape((-1, 1, 2))
            cv2.fillPoly(overlay, [pts], color)
            cv2.polylines(display, [pts], True, color, 3)

        cv2.addWeighted(overlay, 0.25, display, 0.75, 0, display)

        if len(current_polygon) > 0:
            pts = np.array(current_polygon, np.int32).reshape((-1, 1, 2))
            cv2.polylines(display, [pts], False, color, 2)

            for pt in current_polygon:
                cv2.circle(display, pt, 5, color, -1)

        cv2.imshow(window_name, display)

        key = cv2.waitKey(50) & 0xFF

        if key == ord("s"):
            if len(current_polygon) >= 3:
                polygons.append(current_polygon.copy())
            break

        elif key == 27:
            polygons = []
            break

    cv2.destroyAllWindows()
    return polygons


# =========================
# POSE DRAWING + ZONE LOGIC
# =========================

def draw_poses_and_check_zones(
    frame,
    poses,
    danger_zones=None,
    work_zones=None,
    pose_color=(255, 255, 102),
    min_connections=3,
):
    worker_statuses = []
    work_zone_counts = [0 for _ in work_zones] if work_zones else []

    for person in poses:
        keypoints = person.get("keypoints", [])

        # Draw keypoints
        for kpt in keypoints:
            if isinstance(kpt, list) and len(kpt) >= 2:
                x, y = int(kpt[0]), int(kpt[1])

                if x > 0 and y > 0:
                    cv2.circle(frame, (x, y), 2, pose_color, -1)

        # Draw skeleton
        valid_lines = []

        for i, j in SKELETON_CONNECTIONS:
            if i >= len(keypoints) or j >= len(keypoints):
                continue

            x1, y1 = keypoints[i][0], keypoints[i][1]
            x2, y2 = keypoints[j][0], keypoints[j][1]

            if (
                x1 > 0 and y1 > 0 and x2 > 0 and y2 > 0
                and abs(x1 - x2) < 300
                and abs(y1 - y2) < 300
            ):
                valid_lines.append(((int(x1), int(y1)), (int(x2), int(y2))))

        if len(valid_lines) >= min_connections:
            for pt1, pt2 in valid_lines:
                cv2.line(frame, pt1, pt2, pose_color, 1)

        # Worker ground anchor
        anchor = get_worker_anchor(keypoints)

        if anchor is None:
            continue

        in_danger = False
        in_work_zone = False
        danger_zone_id = None
        work_zone_id = None

        # 1. Danger zone check first
        if danger_zones:
            for idx, polygon in enumerate(danger_zones):
                if point_in_polygon(anchor, polygon):
                    in_danger = True
                    danger_zone_id = idx
                    break

        # 2. Work zone check
        if work_zones and not in_danger:
            for idx, polygon in enumerate(work_zones):
                if point_in_polygon(anchor, polygon):
                    in_work_zone = True
                    work_zone_id = idx
                    work_zone_counts[idx] += 1
                    break

        # 3. Final safety logic
        if in_danger:
            status = "DANGER"
            status_color = (0, 0, 255)

        elif in_work_zone:
            status = "SAFE"
            status_color = (0, 255, 0)

        elif work_zones:
            status = "WARNING"
            status_color = (0, 255, 255)

        else:
            status = "SAFE"
            status_color = (0, 255, 0)

        # Draw worker anchor point
        cv2.circle(frame, tuple(anchor), 7, status_color, -1)

        cv2.putText(
            frame,
            status,
            (anchor[0] + 8, anchor[1] - 8),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            status_color,
            2,
        )

        worker_statuses.append(
            {
                "center": anchor,
                "in_danger": in_danger,
                "in_work_zone": in_work_zone,
                "status": status,
                "danger_zone_id": danger_zone_id,
                "work_zone_id": work_zone_id,
            }
        )

    return frame, worker_statuses, work_zone_counts


# =========================
# SAFETY MONITOR CLASS
# =========================

class SafetyMonitor:
    def __init__(self, danger_zones, work_zones, output_dir="safety_reports"):
        self.danger_zones = danger_zones
        self.work_zones = work_zones
        self.output_dir = output_dir
        self.results = []
        self.tracking = {}
        self.frame_count = 0

        os.makedirs(output_dir, exist_ok=True)

        log_name = f"realtime_log_{time.strftime('%Y%m%d_%H%M%S')}.csv"
        self.log_file = open(os.path.join(output_dir, log_name), "w", encoding="utf-8")

        self.log_file.write(
            "timestamp,frame_id,worker_id,pos_x,pos_y,status,"
            "in_danger,in_work_zone,danger_zone_id,work_zone_id\n"
        )

    def update_tracking(self, worker_statuses):
        updated_statuses = []

        for status in worker_statuses:
            min_dist = float("inf")
            best_match = None

            for track_id, track_data in self.tracking.items():
                last_center = track_data.get("last_center", [0, 0])
                dist = np.linalg.norm(
                    np.array(status["center"]) - np.array(last_center)
                )

                if dist < 50 and dist < min_dist:
                    min_dist = dist
                    best_match = track_id

            if best_match is not None:
                track_id = best_match
            else:
                track_id = str(uuid.uuid4())[:8]
                self.tracking[track_id] = {
                    "status_history": [],
                    "first_detected": self.frame_count,
                }

            self.tracking[track_id].update(
                {
                    "last_center": status["center"],
                    "last_update": self.frame_count,
                    "current_status": status["status"],
                }
            )

            self.tracking[track_id]["status_history"].append(
                (
                    self.frame_count,
                    status["center"],
                    status["status"],
                    status["in_danger"],
                    status["in_work_zone"],
                )
            )

            self.log_file.write(
                f"{datetime.now().isoformat()},"
                f"{self.frame_count},"
                f"{track_id},"
                f"{status['center'][0]},"
                f"{status['center'][1]},"
                f"{status['status']},"
                f"{int(status['in_danger'])},"
                f"{int(status['in_work_zone'])},"
                f"{status['danger_zone_id']},"
                f"{status['work_zone_id']}\n"
            )

            updated_statuses.append(
                {
                    "track_id": track_id,
                    **status,
                }
            )

        # Remove stale tracks
        stale_tracks = [
            tid for tid, data in self.tracking.items()
            if self.frame_count - data.get("last_update", 0) > 30
        ]

        for tid in stale_tracks:
            del self.tracking[tid]

        return updated_statuses

    def evaluate_frame(self, worker_statuses, work_zone_counts):
        tracked_workers = self.update_tracking(worker_statuses)

        frame_result = {
            "frame_id": self.frame_count,
            "timestamp": datetime.now().isoformat(),
            "workers": tracked_workers,
            "work_zone_counts": work_zone_counts,
            "total_workers_in_work_zone": sum(work_zone_counts),
            "danger_count": sum(1 for w in tracked_workers if w["in_danger"]),
            "warning_count": sum(1 for w in tracked_workers if w["status"] == "WARNING"),
            "safe_count": sum(1 for w in tracked_workers if w["status"] == "SAFE"),
        }

        self.results.append(frame_result)
        self.frame_count += 1

        return tracked_workers

    def generate_report(self):
        report = {
            "metadata": {
                "evaluation_date": datetime.now().isoformat(),
                "total_frames": self.frame_count,
                "danger_zones": self.danger_zones,
                "work_zones": self.work_zones,
            },
            "frame_results": self.results,
        }

        filename = f"safety_report_{time.strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join(self.output_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

        self.log_file.close()

        print(f"Report saved: {filepath}")
        return filepath


# =========================
# MAIN MONITORING
# =========================

def run_safety_monitoring(
    video_source,
    pose_model_path,
    danger_zones,
    work_zones,
    output_dir="safety_reports",
):
    pose_model = YOLO(pose_model_path)

    monitor = SafetyMonitor(
        danger_zones=danger_zones,
        work_zones=work_zones,
        output_dir=output_dir,
    )

    if isinstance(video_source, int) or (
        isinstance(video_source, str) and video_source.isdigit()
    ):
        video_source = int(video_source)

    cap = cv2.VideoCapture(video_source)

    if not cap.isOpened():
        print(f"Error opening video source: {video_source}")
        return

    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    video_fps = cap.get(cv2.CAP_PROP_FPS)

    if video_fps <= 0:
        video_fps = 30

    output_video_path = os.path.join(
        output_dir,
        f"output_{time.strftime('%Y%m%d_%H%M%S')}.mp4",
    )

    out = cv2.VideoWriter(
        output_video_path,
        cv2.VideoWriter_fourcc(*"mp4v"),
        video_fps,
        (frame_width, frame_height),
    )

    print("Starting industrial spatial awareness monitoring...")
    print("Press q to quit")

    prev_time = time.time()

    while cap.isOpened():
        ret, raw_frame = cap.read()

        if not ret:
            break

        # IMPORTANT:
        # Run pose on original frame, not on overlay frame.
        pose_results = pose_model(raw_frame, verbose=False)

        poses = []

        for result in pose_results:
            if result.keypoints is not None:
                for kpts in result.keypoints.xy.cpu().numpy():
                    person_keypoints = []

                    for kpt in kpts:
                        person_keypoints.append([float(kpt[0]), float(kpt[1])])

                    poses.append({"keypoints": person_keypoints})

        # Draw on separate output frame
        processed_frame = raw_frame.copy()

        # Draw work + danger zones
        processed_frame = draw_all_zones(
            processed_frame,
            danger_zones=danger_zones,
            work_zones=work_zones,
        )

        # Draw poses and classify workers
        processed_frame, worker_statuses, work_zone_counts = draw_poses_and_check_zones(
            frame=processed_frame,
            poses=poses,
            danger_zones=danger_zones,
            work_zones=work_zones,
        )

        tracked_workers = monitor.evaluate_frame(
            worker_statuses=worker_statuses,
            work_zone_counts=work_zone_counts,
        )

        # Draw worker IDs
        for worker in tracked_workers:
            center = worker["center"]
            status = worker["status"]

            if status == "DANGER":
                color = (0, 0, 255)
            elif status == "WARNING":
                color = (0, 255, 255)
            else:
                color = (0, 255, 0)

            cv2.putText(
                processed_frame,
                f"{worker['track_id']}: {status}",
                (center[0], center[1] - 28),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                color,
                2,
            )

        # Display counts
        y_offset = 35

        total_work_zone_workers = sum(work_zone_counts)
        danger_count = sum(1 for w in tracked_workers if w["status"] == "DANGER")
        warning_count = sum(1 for w in tracked_workers if w["status"] == "WARNING")
        safe_count = sum(1 for w in tracked_workers if w["status"] == "SAFE")

        for idx, count in enumerate(work_zone_counts):
            cv2.putText(
                processed_frame,
                f"Work Zone {idx + 1}: {count} workers",
                (10, y_offset),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2,
            )
            y_offset += 30

        cv2.putText(
            processed_frame,
            f"Inside Work Zones: {total_work_zone_workers}",
            (10, y_offset),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2,
        )
        y_offset += 30

        cv2.putText(
            processed_frame,
            f"Safe: {safe_count} | Warning: {warning_count} | Danger: {danger_count}",
            (10, y_offset),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 255) if warning_count > 0 else (255, 255, 255),
            2,
        )

        # FPS
        current_time = time.time()
        fps = 1 / (current_time - prev_time) if current_time > prev_time else 0
        prev_time = current_time

        cv2.putText(
            processed_frame,
            f"FPS: {int(fps)}",
            (10, frame_height - 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2,
        )

        out.write(processed_frame)
        cv2.imshow("Industrial Site Spatial Awareness", processed_frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    out.release()
    cv2.destroyAllWindows()

    monitor.generate_report()

    print(f"Output video saved: {output_video_path}")
    print("Monitoring session ended")


# =========================
# ENTRY POINT
# =========================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Industrial site spatial awareness with danger and work zones"
    )

    parser.add_argument(
        "--video",
        type=str,
        default=DEFAULT_VIDEO,
        help="Path to video file",
    )

    parser.add_argument(
        "--pose_model",
        type=str,
        default=DEFAULT_POSE_MODEL,
        help="YOLO pose model path/name",
    )

    parser.add_argument(
        "--danger_zones",
        type=str,
        default=DEFAULT_DANGER_ZONES,
        help="Path to danger zones JSON",
    )

    parser.add_argument(
        "--work_zones",
        type=str,
        default=DEFAULT_WORK_ZONES,
        help="Path to work zones JSON",
    )

    parser.add_argument(
        "--output_dir",
        type=str,
        default=DEFAULT_OUTPUT_DIR,
        help="Output directory",
    )

    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    # Load or draw danger zones
    danger_zones = load_zones(args.danger_zones)

    if danger_zones is None:
        print("No danger zones found. Draw restricted DANGER zones now.")
        danger_zones = draw_zones_gui(
            video_path=args.video,
            zone_name="DANGER",
            color=(0, 0, 255),
        )

        save_zones(danger_zones, args.danger_zones)
        print(f"Danger zones saved to: {args.danger_zones}")

    # Load or draw work zones
    work_zones = load_zones(args.work_zones)

    if work_zones is None:
        print("No work zones found. Draw allowed WORK zones now.")
        work_zones = draw_zones_gui(
            video_path=args.video,
            zone_name="WORK",
            color=(0, 255, 0),
        )

        save_zones(work_zones, args.work_zones)
        print(f"Work zones saved to: {args.work_zones}")

    run_safety_monitoring(
        video_source=args.video,
        pose_model_path=args.pose_model,
        danger_zones=danger_zones,
        work_zones=work_zones,
        output_dir=args.output_dir,
    )