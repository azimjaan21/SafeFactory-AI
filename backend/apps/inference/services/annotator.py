from __future__ import annotations

import cv2
import numpy as np


MODEL_COLORS = {
    "ppe": (46, 112, 255),
    "work_situation": (148, 72, 255),
    "smoke_fire": (46, 87, 255),
    "worker_forklift": (34, 163, 84),
    "pose_anchor": (255, 255, 0),
}

SKELETON_EDGES = [
    (0, 1), (0, 2), (1, 3), (2, 4),
    (5, 6), (5, 11), (6, 12), (11, 12),
    (5, 7), (7, 9), (6, 8), (8, 10),
    (11, 13), (13, 15), (12, 14), (14, 16),
]

KP_CONF_THRESHOLD = 0.2


class Annotator:
    def draw(self, frame, detections, zones, workers, work_zone_counts, forklift_interactions, global_forklift_status):
        output = frame.copy()
        self._draw_zones(output, zones)
        self._draw_detections(output, detections)
        self._draw_workers(output, workers)
        self._draw_forklift_interactions(output, forklift_interactions)
        self._draw_zone_counts(output, zones.get("work", []), work_zone_counts)
        if forklift_interactions:
            self._draw_global_status(output, global_forklift_status)
        return output

    def _draw_detections(self, frame, detections):
        for detection in detections:
            x1, y1, x2, y2 = map(int, detection["box"])
            color = detection.get("color") or MODEL_COLORS.get(detection["model_key"], (255, 255, 255))
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(
                frame,
                detection["label"],
                (x1, max(y1 - 10, 20)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                color,
                2,
            )

    def _draw_zones(self, frame, zones):
        self._draw_polygon_group(frame, zones.get("work", []), (46, 184, 92), "WORK ZONE", 0.20)
        self._draw_polygon_group(frame, zones.get("danger", []), (46, 46, 255), "DANGER ZONE", 0.25)

    def _draw_polygon_group(self, frame, polygons, color, label, alpha):
        if not polygons:
            return
        overlay = frame.copy()
        for index, polygon in enumerate(polygons, start=1):
            pts = np.array(polygon, dtype=np.int32).reshape((-1, 1, 2))
            cv2.fillPoly(overlay, [pts], color)
            cv2.polylines(frame, [pts], True, color, 3)
            x, y = pts[0][0]
            cv2.putText(
                frame,
                f"{label} {index}",
                (int(x), max(int(y) - 10, 24)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                color,
                2,
            )
        cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)

    def _draw_workers(self, frame, workers):
        for worker in workers:
            status = worker.get("status", "SAFE")
            if status == "DANGER":
                color = (46, 46, 255)
            elif status == "WARNING":
                color = (0, 210, 255)
            else:
                color = (46, 184, 92)

            self._draw_pose_skeleton(frame, worker, color)

            anchor = worker.get("anchor")
            if anchor is None:
                continue
            cv2.circle(frame, anchor, 6, color, -1)
            track_id = worker.get("track_id", "")
            label = f"W{track_id} {status}" if track_id else status
            cv2.putText(
                frame,
                label,
                (anchor[0] + 8, anchor[1] - 8),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                color,
                2,
            )

    def _draw_pose_skeleton(self, frame, worker, color):
        kp_xy = worker.get("keypoints_xy")
        kp_norm = worker.get("keypoints_norm")
        if kp_xy is None or len(kp_xy) < 17:
            return

        for a, b in SKELETON_EDGES:
            ax, ay = float(kp_xy[a][0]), float(kp_xy[a][1])
            bx, by = float(kp_xy[b][0]), float(kp_xy[b][1])
            if not (np.isfinite(ax) and np.isfinite(ay) and np.isfinite(bx) and np.isfinite(by)):
                continue
            xa, ya, xb, yb = int(ax), int(ay), int(bx), int(by)
            if xa <= 0 or ya <= 0 or xb <= 0 or yb <= 0:
                continue
            if kp_norm is not None:
                if kp_norm[a, 2] < KP_CONF_THRESHOLD or kp_norm[b, 2] < KP_CONF_THRESHOLD:
                    continue
            cv2.line(frame, (xa, ya), (xb, yb), color, 2)

        for i in range(len(kp_xy)):
            fx, fy = float(kp_xy[i][0]), float(kp_xy[i][1])
            if not (np.isfinite(fx) and np.isfinite(fy)):
                continue
            x, y = int(fx), int(fy)
            if x <= 0 or y <= 0:
                continue
            if kp_norm is not None and kp_norm[i, 2] < KP_CONF_THRESHOLD:
                continue
            cv2.circle(frame, (x, y), 4, color, -1)

    def _draw_forklift_interactions(self, frame, interactions):
        for interaction in interactions:
            cv2.line(
                frame,
                interaction["worker_anchor"],
                interaction["forklift_center"],
                interaction["color"],
                2,
            )
            mid_x = int((interaction["worker_anchor"][0] + interaction["forklift_center"][0]) / 2)
            mid_y = int((interaction["worker_anchor"][1] + interaction["forklift_center"][1]) / 2)
            cv2.putText(
                frame,
                f'{interaction["status"]} {interaction["distance"]:.0f}px',
                (mid_x, mid_y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                interaction["color"],
                2,
            )

    def _draw_zone_counts(self, frame, work_polygons, work_zone_counts):
        y_offset = 34
        total = sum(work_zone_counts)
        for index, count in enumerate(work_zone_counts, start=1):
            cv2.putText(
                frame,
                f"Work Zone {index}: {count} workers",
                (12, y_offset),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (46, 184, 92),
                2,
            )
            y_offset += 28
        if work_polygons:
            cv2.putText(
                frame,
                f"Workers in Work Zone: {total}",
                (12, y_offset),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (46, 184, 92),
                2,
            )

    def _draw_global_status(self, frame, status):
        if status == "DANGER":
            color = (46, 46, 255)
        elif status == "WARNING":
            color = (0, 210, 255)
        else:
            color = (46, 184, 92)
        cv2.rectangle(frame, (20, 20), (320, 80), color, -1)
        cv2.putText(
            frame,
            f"FORKLIFT STATUS: {status}",
            (34, 58),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 255),
            2,
        )
