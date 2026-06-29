from __future__ import annotations

from typing import Iterable


def normalize_points(points):
    return [{"x": float(point["x"]), "y": float(point["y"])} for point in points]


def denormalize_points(points, frame_width, frame_height):
    return [
        [int(round(point["x"] * frame_width)), int(round(point["y"] * frame_height))]
        for point in points
    ]


def point_in_polygon(point, polygon):
    x, y = point
    inside = False
    if len(polygon) < 3:
        return False

    px1, py1 = polygon[0]
    for index in range(len(polygon) + 1):
        px2, py2 = polygon[index % len(polygon)]
        if y > min(py1, py2):
            if y <= max(py1, py2):
                if x <= max(px1, px2):
                    if py1 != py2:
                        xinters = (y - py1) * (px2 - px1) / (py2 - py1 + 1e-6) + px1
                        if px1 == px2 or x <= xinters:
                            inside = not inside
        px1, py1 = px2, py2
    return inside


def get_worker_anchor(keypoints_xy, keypoints_conf=None, fallback_box=None):
    valid_points = []
    for index in [15, 16]:
        if index >= len(keypoints_xy):
            continue
        x, y = keypoints_xy[index]
        if x <= 0 or y <= 0:
            continue
        if keypoints_conf is not None and keypoints_conf[index] <= 0.3:
            continue
        valid_points.append((x, y))
    if valid_points:
        return _average_point(valid_points)

    valid_points = []
    for index in [11, 12]:
        if index >= len(keypoints_xy):
            continue
        x, y = keypoints_xy[index]
        if x <= 0 or y <= 0:
            continue
        if keypoints_conf is not None and keypoints_conf[index] <= 0.3:
            continue
        valid_points.append((x, y))
    if valid_points:
        return _average_point(valid_points)

    if fallback_box:
        x1, _, x2, y2 = fallback_box
        return int((x1 + x2) / 2), int(y2)

    return None


def _average_point(points: Iterable[tuple[float, float]]):
    points = list(points)
    return (
        int(sum(point[0] for point in points) / len(points)),
        int(sum(point[1] for point in points) / len(points)),
    )


class ZoneAnalyzer:
    def analyze(self, workers, danger_zones=None, work_zones=None):
        danger_zones = danger_zones or []
        work_zones = work_zones or []
        work_zone_counts = [0 for _ in work_zones]
        worker_statuses = []

        for worker in workers:
            anchor = worker.get("anchor")
            if anchor is None:
                continue

            in_danger = False
            in_work_zone = False
            danger_zone_id = None
            work_zone_id = None

            for index, polygon in enumerate(danger_zones):
                if point_in_polygon(anchor, polygon):
                    in_danger = True
                    danger_zone_id = index
                    break

            if work_zones and not in_danger:
                for index, polygon in enumerate(work_zones):
                    if point_in_polygon(anchor, polygon):
                        in_work_zone = True
                        work_zone_id = index
                        work_zone_counts[index] += 1
                        break

            if in_danger:
                status = "DANGER"
            elif in_work_zone:
                status = "SAFE"
            elif work_zones:
                status = "WARNING"
            else:
                status = "SAFE"

            worker_statuses.append(
                {
                    **worker,
                    "status": status,
                    "in_danger": in_danger,
                    "in_work_zone": in_work_zone,
                    "danger_zone_id": danger_zone_id,
                    "work_zone_id": work_zone_id,
                }
            )

        return worker_statuses, work_zone_counts
