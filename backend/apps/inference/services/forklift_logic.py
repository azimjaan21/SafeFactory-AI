from __future__ import annotations

import math


def bbox_center(box):
    x1, y1, x2, y2 = box
    return int((x1 + x2) / 2), int((y1 + y2) / 2)


def point_to_bbox_distance(point, box):
    px, py = point
    x1, y1, x2, y2 = box
    dx = max(x1 - px, px - x2, 0)
    dy = max(y1 - py, py - y2, 0)
    return math.sqrt(dx * dx + dy * dy)


def get_safety_status(distance, warning_dist, danger_dist):
    if distance <= danger_dist:
        return "DANGER", (0, 0, 255)
    if distance <= warning_dist:
        return "WARNING", (0, 255, 255)
    return "SAFE", (0, 255, 0)


class ForkliftSafetyAnalyzer:
    def __init__(self, warning_distance, danger_distance):
        self.warning_distance = warning_distance
        self.danger_distance = danger_distance

    def analyze(self, workers, forklifts):
        interactions = []
        global_status = "SAFE"

        for worker in workers:
            anchor = worker.get("anchor")
            if anchor is None:
                continue

            for forklift in forklifts:
                distance = point_to_bbox_distance(anchor, forklift["box"])
                status, color = get_safety_status(
                    distance,
                    self.warning_distance,
                    self.danger_distance,
                )

                if status == "DANGER":
                    global_status = "DANGER"
                elif status == "WARNING" and global_status != "DANGER":
                    global_status = "WARNING"

                interactions.append(
                    {
                        "worker_anchor": anchor,
                        "worker_track_id": worker.get("track_id"),
                        "forklift_box": forklift["box"],
                        "forklift_center": bbox_center(forklift["box"]),
                        "distance": distance,
                        "status": status,
                        "color": color,
                    }
                )

        return interactions, global_status
