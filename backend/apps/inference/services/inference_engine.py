from __future__ import annotations

from collections import defaultdict
from math import hypot

import numpy as np
from django.conf import settings

from .abnormal_behavior_analyzer import AbnormalBehaviorAnalyzer
from .annotator import Annotator
from .forklift_logic import ForkliftSafetyAnalyzer
from .model_registry import ModelRegistry
from .zone_logic import ZoneAnalyzer, denormalize_points, get_worker_anchor


class InferenceEngine:
    def __init__(self):
        self.registry = ModelRegistry()
        self.zone_analyzer = ZoneAnalyzer()
        self.forklift_analyzer = ForkliftSafetyAnalyzer(
            warning_distance=settings.SAFEFACTORY_FORKLIFT_WARNING_DISTANCE,
            danger_distance=settings.SAFEFACTORY_FORKLIFT_DANGER_DISTANCE,
        )
        self.annotator = Annotator()
        self.abnormal_analyzer = AbnormalBehaviorAnalyzer()
        self.reset_runtime_state()

    def reset_runtime_state(self):
        self.worker_tracks = {}
        self.next_worker_track_id = 1
        self.frame_index = 0
        self.abnormal_analyzer.reset()

    _POSE_DEPENDENT = {"danger_zone", "work_zone", "worker_forklift",
                       "fall_detection", "running_detection", "inactivity_detection"}

    def normalize_enabled_models(self, enabled_models):
        normalized = set(enabled_models)
        if normalized & self._POSE_DEPENDENT:
            normalized.add("pose_anchor")
        return sorted(normalized)

    def enforce_streaming_limit(self, source_type, enabled_models):
        normalized = self.normalize_enabled_models(enabled_models)
        if source_type in {"image", "video"}:
            return normalized

        primary_models = [model_key for model_key in normalized
                          if model_key not in {"pose_anchor", "fall_detection", "running_detection", "inactivity_detection"}]
        if len(primary_models) > settings.SAFEFACTORY_MAX_STREAM_MODELS:
            raise ValueError(
                f"Live streams support at most {settings.SAFEFACTORY_MAX_STREAM_MODELS} AI models at once."
            )
        return normalized

    def process_frame(self, frame, enabled_models, zones):
        enabled_models = self.normalize_enabled_models(enabled_models)
        self.frame_index += 1
        detections = []
        events = []
        forklifts = []
        workers = []
        work_zone_counts = []
        global_forklift_status = "SAFE"

        parsed_zones = self._prepare_zones(zones, frame.shape[1], frame.shape[0])

        if "ppe" in enabled_models:
            ppe_detections, ppe_events = self._run_generic_detector(frame, "ppe", "PPE Detection")
            detections.extend(ppe_detections)
            events.extend(ppe_events)

        if "work_situation" in enabled_models:
            ws_detections, ws_events = self._run_generic_detector(frame, "work_situation", "Work Situation")
            detections.extend(ws_detections)
            events.extend(ws_events)

        if "smoke_fire" in enabled_models:
            sf_detections, sf_events = self._run_generic_detector(frame, "smoke_fire", "Smoke & Fire Detection")
            detections.extend(sf_detections)
            events.extend(sf_events)

        if "pose_anchor" in enabled_models:
            workers = self._run_pose_detector(frame)
            workers = self._attach_worker_tracks(workers)

        if "worker_forklift" in enabled_models:
            forklifts, forklift_events = self._run_forklift_detector(frame)
            detections.extend(forklifts)
            events.extend(forklift_events)
            forklift_interactions, global_forklift_status = self.forklift_analyzer.analyze(workers, forklifts)
            for interaction in forklift_interactions:
                if interaction["status"] == "SAFE":
                    continue
                severity = "Danger" if interaction["status"] == "DANGER" else "Warning"
                events.append(
                    {
                        "event_type": "forklift_proximity",
                        "model_key": "worker_forklift",
                        "severity": severity,
                        "confidence": None,
                        "label": "Forklift Near Worker",
                        "details": {
                            "subject_id": f'worker:{interaction["worker_track_id"]}',
                            "worker_track_id": interaction["worker_track_id"],
                            "distance": round(interaction["distance"], 2),
                            "status": interaction["status"],
                        },
                    }
                )
        else:
            forklift_interactions = []

        active_detectors = {k for k in ("fall_detection", "running_detection", "inactivity_detection")
                            if k in enabled_models}
        if active_detectors and workers:
            abnormal_events = self.abnormal_analyzer.analyze(workers, enabled=active_detectors)
            events.extend(abnormal_events)

        if {"danger_zone", "work_zone"} & set(enabled_models):
            workers, work_zone_counts = self.zone_analyzer.analyze(
                workers,
                danger_zones=parsed_zones["danger"],
                work_zones=parsed_zones["work"],
            )

            if "danger_zone" in enabled_models:
                for worker in workers:
                    if worker["in_danger"]:
                        events.append(
                            {
                                "event_type": "worker_in_danger_zone",
                                "model_key": "danger_zone",
                                "severity": "Danger",
                                "confidence": None,
                                "label": "Worker in Danger Zone",
                                "details": {
                                    "subject_id": f'worker:{worker["track_id"]}',
                                    "worker_track_id": worker["track_id"],
                                    "zone_index": worker["danger_zone_id"],
                                    "anchor": worker["anchor"],
                                },
                            }
                        )

            if "work_zone" in enabled_models and sum(work_zone_counts) > 0:
                events.append(
                    {
                        "event_type": "workers_in_work_zone",
                        "model_key": "work_zone",
                        "severity": "Info",
                        "confidence": None,
                        "label": f"{sum(work_zone_counts)} Workers in Work Zone",
                        "details": {"counts": work_zone_counts},
                    }
                )

        annotated = self.annotator.draw(
            frame=frame,
            detections=detections,
            zones=parsed_zones,
            workers=workers,
            work_zone_counts=work_zone_counts,
            forklift_interactions=forklift_interactions,
            global_forklift_status=global_forklift_status,
        )
        return {
            "frame": annotated,
            "events": events,
            "enabled_models": enabled_models,
            "worker_count": sum(work_zone_counts) if work_zone_counts else len(workers),
        }

    def _run_generic_detector(self, frame, model_key, default_title):
        model = self.registry.get_model(model_key)
        with ModelRegistry._infer_lock:
            result = model.predict(
                frame,
                conf=settings.SAFEFACTORY_DEFAULT_CONFIDENCE,
                verbose=False,
                device=self.registry.device,
                half=self.registry.use_half,
            )[0]
        detections = []
        events = []
        for box in result.boxes:
            cls_id = int(box.cls[0])
            confidence = float(box.conf[0])
            class_name = model.names[cls_id]
            xyxy = box.xyxy[0].cpu().numpy().tolist()
            detections.append(
                {
                    "box": xyxy,
                    "label": f"{class_name} {confidence:.2f}",
                    "model_key": model_key,
                    "class_name": class_name,
                    "confidence": confidence,
                }
            )
        if model_key == "ppe":
            events.extend(self._build_ppe_events(detections))
        else:
            for detection in detections:
                event = self._event_for_detection(model_key, detection, default_title)
                if event:
                    events.append(event)
        return detections, events

    def _run_pose_detector(self, frame):
        model = self.registry.get_model("pose_anchor")
        with ModelRegistry._infer_lock:
            result = model.predict(
                frame,
                conf=settings.SAFEFACTORY_POSE_CONFIDENCE,
                verbose=False,
                device=self.registry.device,
                half=False,
            )[0]
        workers = []
        if result.boxes is None or result.keypoints is None:
            return workers

        frame_h, frame_w = frame.shape[:2]

        for index, box in enumerate(result.boxes):
            cls_id = int(box.cls[0])
            class_name = model.names[cls_id].lower()
            if class_name != "person":
                continue
            bbox = box.xyxy[0].cpu().numpy().tolist()
            confidence = float(box.conf[0])
            keypoints_xy = result.keypoints.xy[index].cpu().numpy()
            keypoints_conf = result.keypoints.conf[index].cpu().numpy() if result.keypoints.conf is not None else None
            anchor = get_worker_anchor(keypoints_xy, keypoints_conf, bbox)

            kp_norm = np.zeros((17, 3), dtype=np.float32)
            kp_norm[:, 0] = keypoints_xy[:, 0] / max(frame_w, 1)
            kp_norm[:, 1] = keypoints_xy[:, 1] / max(frame_h, 1)
            kp_norm[:, 2] = keypoints_conf if keypoints_conf is not None else np.ones(17, dtype=np.float32)

            workers.append(
                {
                    "box": bbox,
                    "anchor": anchor,
                    "confidence": confidence,
                    "keypoints_xy": keypoints_xy,
                    "keypoints_norm": kp_norm,
                }
            )
        return workers

    def _attach_worker_tracks(self, workers):
        updated_tracks = {}
        tracked_workers = []
        for worker in workers:
            anchor = worker.get("anchor")
            if anchor is None:
                worker["track_id"] = f"w{self.next_worker_track_id}"
                self.next_worker_track_id += 1
                tracked_workers.append(worker)
                continue

            best_track_id = None
            best_distance = None
            for track_id, track in self.worker_tracks.items():
                if self.frame_index - track["last_frame"] > 150:
                    continue
                distance = hypot(anchor[0] - track["anchor"][0], anchor[1] - track["anchor"][1])
                if distance > 150:
                    continue
                if best_distance is None or distance < best_distance:
                    best_distance = distance
                    best_track_id = track_id

            if best_track_id is None:
                best_track_id = f"w{self.next_worker_track_id}"
                self.next_worker_track_id += 1

            updated_tracks[best_track_id] = {
                "anchor": anchor,
                "last_frame": self.frame_index,
            }
            worker["track_id"] = best_track_id
            tracked_workers.append(worker)

        self.worker_tracks = updated_tracks
        return tracked_workers

    def _run_forklift_detector(self, frame):
        model = self.registry.get_model("worker_forklift")
        with ModelRegistry._infer_lock:
            result = model.predict(
                frame,
                conf=settings.SAFEFACTORY_DEFAULT_CONFIDENCE,
                verbose=False,
                device=self.registry.device,
                half=self.registry.use_half,
            )[0]
        detections = []
        for box in result.boxes:
            cls_id = int(box.cls[0])
            class_name = model.names[cls_id].lower()
            confidence = float(box.conf[0])
            xyxy = box.xyxy[0].cpu().numpy().tolist()
            if class_name != "forklift" and len(model.names) != 1:
                continue
            detection = {
                "box": xyxy,
                "label": f"Forklift {confidence:.2f}",
                "model_key": "worker_forklift",
                "confidence": confidence,
            }
            detections.append(detection)
        return detections, []

    def _prepare_zones(self, zones, frame_width, frame_height):
        grouped = defaultdict(list)
        for zone in zones:
            bucket = "danger" if zone.zone_type == "danger_zone" else "work"
            grouped[bucket].append(denormalize_points(zone.points, frame_width, frame_height))
        return grouped

    def _event_for_detection(self, model_key, detection, default_title):
        class_name = detection["class_name"]
        lowered = class_name.lower()
        confidence = detection.get("confidence")
        if model_key == "smoke_fire":
            if lowered not in {"fire", "smoke"}:
                return None
            return {
                "event_type": f"{lowered}_detected",
                "model_key": model_key,
                "severity": "Danger",
                "confidence": confidence,
                "label": "Fire Detected" if lowered == "fire" else "Smoke Detected",
                "details": {"class_name": lowered},
            }
        if model_key == "work_situation":
            if "without helmet" in lowered:
                return {
                    "event_type": "worker_without_helmet",
                    "model_key": model_key,
                    "severity": "Warning",
                    "confidence": confidence,
                    "label": "Worker Without Helmet",
                    "details": {"class_name": class_name},
                }
            if "throwing_material" in lowered:
                return {
                    "event_type": "unsafe_material_throwing",
                    "model_key": model_key,
                    "severity": "Warning",
                    "confidence": confidence,
                    "label": "Unsafe Material Throwing",
                    "details": {"class_name": class_name},
                }
            return None
        return None

    def _build_ppe_events(self, detections):
        helmet_boxes = [item["box"] for item in detections if item["label"].lower().startswith("helmet ")]
        head_detections = [item for item in detections if item["label"].lower().startswith("head ")]
        events = []
        for head in head_detections:
            if self._has_matching_helmet(head["box"], helmet_boxes):
                continue
            events.append(
                {
                    "event_type": "missing_helmet",
                    "model_key": "ppe",
                    "severity": "Warning",
                    "confidence": None,
                    "label": "Missing Helmet",
                    "details": {
                        "subject_id": self._subject_id_from_box("head", head["box"]),
                        "head_box": [round(value, 2) for value in head["box"]],
                    },
                }
            )
        return events

    def _has_matching_helmet(self, head_box, helmet_boxes):
        hx1, hy1, hx2, hy2 = head_box
        head_area = max((hx2 - hx1), 1) * max((hy2 - hy1), 1)
        for helmet_box in helmet_boxes:
            ix1 = max(hx1, helmet_box[0])
            iy1 = max(hy1, helmet_box[1])
            ix2 = min(hx2, helmet_box[2])
            iy2 = min(hy2, helmet_box[3])
            if ix2 <= ix1 or iy2 <= iy1:
                continue
            overlap_ratio = ((ix2 - ix1) * (iy2 - iy1)) / head_area
            if overlap_ratio >= 0.15:
                return True
        return False

    def _subject_id_from_box(self, prefix, box):
        center_x = int((box[0] + box[2]) / 2)
        center_y = int((box[1] + box[3]) / 2)
        return f"{prefix}:{center_x // 40}:{center_y // 40}"
