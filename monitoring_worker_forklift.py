from argparse import ArgumentParser
from pathlib import Path
from datetime import datetime
import math
import cv2
from ultralytics import YOLO


# =========================
# DEFAULT PATHS
# =========================

DEFAULT_FORKLIFT_MODEL = r"C:\Users\dalab\Desktop\azimjaan21\SafeFactory System\#Project_Safety_AI\2.2 Forklift-Worker Detection\#backup\weights\best.pt"

DEFAULT_POSE_MODEL = "yolo11s-pose.pt"

DEFAULT_SOURCE = r"C:\Users\dalab\Desktop\azimjaan21\SafeFactory System\#Project_Safety_AI\2.2 Forklift-Worker Detection\test.mp4"

DEFAULT_OUTPUT_DIR = r"C:\Users\dalab\Desktop\azimjaan21\SafeFactory System\#Project_Safety_AI\2.2 Forklift-Worker Detection\outputs"


# =========================
# ARGUMENTS
# =========================

def parse_args():
    parser = ArgumentParser(
        description="Forklift-worker safety monitoring using forklift detector + YOLO11 pose"
    )

    parser.add_argument(
        "--forklift-weights",
        type=Path,
        default=DEFAULT_FORKLIFT_MODEL,
        help="Path to forklift detection model",
    )

    parser.add_argument(
        "--pose-weights",
        type=str,
        default=DEFAULT_POSE_MODEL,
        help="Path/name of YOLO pose model",
    )

    parser.add_argument(
        "--source",
        type=str,
        default=DEFAULT_SOURCE,
        help="Video/image/webcam source",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory to save output video",
    )

    parser.add_argument(
        "--forklift-conf",
        type=float,
        default=0.35,
        help="Forklift detection confidence threshold",
    )

    parser.add_argument(
        "--pose-conf",
        type=float,
        default=0.35,
        help="Pose/person detection confidence threshold",
    )

    parser.add_argument(
        "--warning-dist",
        type=float,
        default=400,
        help="Pixel distance threshold for WARNING",
    )

    parser.add_argument(
        "--danger-dist",
        type=float,
        default=200,
        help="Pixel distance threshold for DANGER",
    )

    return parser.parse_args()


# =========================
# UTILS
# =========================

def point_to_bbox_distance(point, box):
    """
    Distance from worker body point to forklift bbox.
    If point is inside forklift bbox, distance = 0.
    """
    px, py = point
    x1, y1, x2, y2 = box

    dx = max(x1 - px, px - x2, 0)
    dy = max(y1 - py, py - y2, 0)

    return math.sqrt(dx * dx + dy * dy)


def bbox_center(box):
    x1, y1, x2, y2 = box
    return int((x1 + x2) / 2), int((y1 + y2) / 2)


def bbox_bottom_center(box):
    x1, y1, x2, y2 = box
    return int((x1 + x2) / 2), int(y2)


def get_safety_status(distance, warning_dist, danger_dist):
    if distance <= danger_dist:
        return "DANGER", (0, 0, 255)       # red
    elif distance <= warning_dist:
        return "WARNING", (0, 255, 255)    # yellow
    else:
        return "SAFE", (0, 255, 0)         # green


def draw_box(frame, box, label, color):
    x1, y1, x2, y2 = map(int, box)

    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

    cv2.putText(
        frame,
        label,
        (x1, max(y1 - 10, 25)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        color,
        2,
    )


def draw_status_panel(frame, status, color):
    cv2.rectangle(frame, (20, 20), (410, 90), color, -1)

    cv2.putText(
        frame,
        f"STATUS: {status}",
        (35, 65),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.1,
        (0, 0, 0),
        3,
    )


def get_worker_anchor_from_pose(person_box, keypoints_xy, keypoints_conf=None):
    """
    COCO keypoint indexes:
    11 = left hip
    12 = right hip
    15 = left ankle
    16 = right ankle

    Priority:
    1. average visible ankles
    2. average visible hips
    3. bbox bottom-center fallback
    """

    valid_points = []

    # Try ankles first
    for idx in [15, 16]:
        if idx < len(keypoints_xy):
            x, y = keypoints_xy[idx]

            if keypoints_conf is None:
                valid_points.append((x, y))
            else:
                if keypoints_conf[idx] > 0.3:
                    valid_points.append((x, y))

    if len(valid_points) > 0:
        avg_x = sum(p[0] for p in valid_points) / len(valid_points)
        avg_y = sum(p[1] for p in valid_points) / len(valid_points)
        return int(avg_x), int(avg_y)

    # If ankles not visible, try hips
    valid_points = []

    for idx in [11, 12]:
        if idx < len(keypoints_xy):
            x, y = keypoints_xy[idx]

            if keypoints_conf is None:
                valid_points.append((x, y))
            else:
                if keypoints_conf[idx] > 0.3:
                    valid_points.append((x, y))

    if len(valid_points) > 0:
        avg_x = sum(p[0] for p in valid_points) / len(valid_points)
        avg_y = sum(p[1] for p in valid_points) / len(valid_points)
        return int(avg_x), int(avg_y)

    # Final fallback
    return bbox_bottom_center(person_box)


def draw_pose_points(frame, keypoints_xy, keypoints_conf=None):
    """
    Draw important lower-body keypoints only.
    """
    important_ids = [11, 12, 15, 16]

    for idx in important_ids:
        if idx >= len(keypoints_xy):
            continue

        if keypoints_conf is not None and keypoints_conf[idx] < 0.3:
            continue

        x, y = keypoints_xy[idx]
        cv2.circle(frame, (int(x), int(y)), 4, (255, 255, 0), -1)


# =========================
# MAIN
# =========================

def main():
    args = parse_args()

    if not args.forklift_weights.exists():
        raise FileNotFoundError(f"Forklift model not found: {args.forklift_weights}")

    print(f"Forklift model: {args.forklift_weights}")
    print(f"Pose model: {args.pose_weights}")
    print(f"Source: {args.source}")

    forklift_model = YOLO(str(args.forklift_weights))
    pose_model = YOLO(args.pose_weights)

    print("Forklift model classes:", forklift_model.names)
    print("Pose model classes:", pose_model.names)

    source = int(args.source) if args.source.isdigit() else args.source
    cap = cv2.VideoCapture(source)

    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video source: {args.source}")

    # =========================
    # AUTO SAVE OUTPUT VIDEO
    # =========================

    args.output_dir.mkdir(parents=True, exist_ok=True)

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 30

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = args.output_dir / f"forklift_worker_pose_safety_{timestamp}.mp4"

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")

    writer = cv2.VideoWriter(
        str(output_path),
        fourcc,
        fps,
        (width, height),
    )

    if not writer.isOpened():
        raise RuntimeError(f"Could not create output video: {output_path}")

    print(f"Output will be saved to: {output_path}")

    while True:
        ret, frame = cap.read()

        if not ret:
            break

        # =========================
        # 1. FORKLIFT DETECTION
        # =========================

        forklift_results = forklift_model.predict(
            frame,
            conf=args.forklift_conf,
            verbose=False,
        )[0]

        forklifts = []

        for box in forklift_results.boxes:
            cls_id = int(box.cls[0])
            cls_name = forklift_model.names[cls_id].lower()
            conf = float(box.conf[0])

            xyxy = box.xyxy[0].cpu().numpy().tolist()

            if cls_name == "forklift" or len(forklift_model.names) == 1:
                forklifts.append((xyxy, conf))

        # =========================
        # 2. PERSON POSE DETECTION
        # =========================

        pose_results = pose_model.predict(
            frame,
            conf=args.pose_conf,
            verbose=False,
        )[0]

        workers = []

        if pose_results.boxes is not None and pose_results.keypoints is not None:
            boxes = pose_results.boxes
            keypoints = pose_results.keypoints

            for i, box in enumerate(boxes):
                cls_id = int(box.cls[0])
                cls_name = pose_model.names[cls_id].lower()
                conf = float(box.conf[0])

                if cls_name != "person":
                    continue

                person_box = box.xyxy[0].cpu().numpy().tolist()

                kpts_xy = keypoints.xy[i].cpu().numpy()
                kpts_conf = None

                if keypoints.conf is not None:
                    kpts_conf = keypoints.conf[i].cpu().numpy()

                anchor = get_worker_anchor_from_pose(
                    person_box,
                    kpts_xy,
                    kpts_conf,
                )

                workers.append((person_box, conf, kpts_xy, kpts_conf, anchor))

        # =========================
        # 3. DRAW DETECTIONS
        # =========================

        for forklift_box, forklift_conf in forklifts:
            draw_box(
                frame,
                forklift_box,
                f"Forklift {forklift_conf:.2f}",
                (255, 0, 0),
            )

        for worker_box, worker_conf, kpts_xy, kpts_conf, anchor in workers:
            draw_box(
                frame,
                worker_box,
                f"Worker {worker_conf:.2f}",
                (255, 255, 255),
            )

            draw_pose_points(frame, kpts_xy, kpts_conf)

            cv2.circle(
                frame,
                anchor,
                6,
                (0, 255, 255),
                -1,
            )

            cv2.putText(
                frame,
                "worker point",
                (anchor[0] + 8, anchor[1] - 8),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 255),
                2,
            )

        # =========================
        # 4. HUMAN-MACHINE SAFETY LOGIC
        # =========================

        global_status = "SAFE"
        global_color = (0, 255, 0)

        for worker_box, _, _, _, worker_anchor in workers:
            for forklift_box, _ in forklifts:
                distance = point_to_bbox_distance(
                    worker_anchor,
                    forklift_box,
                )

                status, color = get_safety_status(
                    distance,
                    args.warning_dist,
                    args.danger_dist,
                )

                if status == "DANGER":
                    global_status = "DANGER"
                    global_color = color

                elif status == "WARNING" and global_status != "DANGER":
                    global_status = "WARNING"
                    global_color = color

                forklift_center = bbox_center(forklift_box)

                cv2.line(
                    frame,
                    worker_anchor,
                    forklift_center,
                    color,
                    2,
                )

                mid_x = int((worker_anchor[0] + forklift_center[0]) / 2)
                mid_y = int((worker_anchor[1] + forklift_center[1]) / 2)

                cv2.putText(
                    frame,
                    f"{status} {distance:.0f}px",
                    (mid_x, mid_y),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    color,
                    2,
                )

        draw_status_panel(frame, global_status, global_color)

        # Save every processed frame
        writer.write(frame)

        cv2.imshow("Forklift + Pose Safety Monitoring", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    writer.release()
    cv2.destroyAllWindows()

    print(f"Saved output video: {output_path}")


if __name__ == "__main__":
    main()