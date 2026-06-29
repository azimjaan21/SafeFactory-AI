from unittest.mock import patch

import numpy as np
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Source
from .services.inference_engine import InferenceEngine
from .services.forklift_logic import get_safety_status, point_to_bbox_distance
from .services.zone_logic import ZoneAnalyzer, get_worker_anchor, point_in_polygon


class ZoneLogicTests(TestCase):
    def test_point_in_polygon(self):
        polygon = [[0, 0], [10, 0], [10, 10], [0, 10]]
        self.assertTrue(point_in_polygon((5, 5), polygon))
        self.assertFalse(point_in_polygon((20, 20), polygon))

    def test_get_worker_anchor_prefers_ankles(self):
        keypoints = [(0, 0)] * 17
        keypoints[15] = (10, 90)
        keypoints[16] = (20, 100)
        self.assertEqual(get_worker_anchor(keypoints), (15, 95))

    def test_zone_analyzer_counts_workers(self):
        analyzer = ZoneAnalyzer()
        workers = [{"anchor": (5, 5)}, {"anchor": (15, 15)}]
        statuses, counts = analyzer.analyze(
            workers,
            danger_zones=[[[0, 0], [8, 0], [8, 8], [0, 8]]],
            work_zones=[[[10, 10], [20, 10], [20, 20], [10, 20]]],
        )
        self.assertTrue(statuses[0]["in_danger"])
        self.assertTrue(statuses[1]["in_work_zone"])
        self.assertEqual(counts, [1])


class ForkliftLogicTests(TestCase):
    def test_distance_and_status(self):
        distance = point_to_bbox_distance((10, 10), [15, 15, 30, 30])
        self.assertGreater(distance, 0)
        self.assertEqual(get_safety_status(100, 400, 200)[0], "DANGER")
        self.assertEqual(get_safety_status(300, 400, 200)[0], "WARNING")
        self.assertEqual(get_safety_status(500, 400, 200)[0], "SAFE")


class InferenceEngineTests(TestCase):
    def test_streaming_model_limit(self):
        engine = InferenceEngine()
        with self.assertRaises(ValueError):
            engine.enforce_streaming_limit("rtsp", ["ppe", "smoke_fire", "work_situation"])

    def test_ppe_events_only_report_missing_helmet(self):
        engine = InferenceEngine()
        detections = [
            {"box": [0, 0, 10, 10], "label": "head 0.91", "model_key": "ppe", "class_name": "head", "confidence": 0.91},
            {"box": [20, 20, 30, 30], "label": "helmet 0.88", "model_key": "ppe", "class_name": "helmet", "confidence": 0.88},
        ]
        events = engine._build_ppe_events(detections)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["label"], "Missing Helmet")

    def test_worker_tracks_persist_for_nearby_anchor(self):
        engine = InferenceEngine()
        first = engine._attach_worker_tracks([{"anchor": (100, 100)}])
        engine.frame_index += 1
        second = engine._attach_worker_tracks([{"anchor": (108, 102)}])
        self.assertEqual(first[0]["track_id"], second[0]["track_id"])


class SessionManagerTests(TestCase):
    def test_event_key_uses_subject_id_not_changing_details(self):
        from .services.session_manager import SessionManager

        manager = SessionManager()
        event_a = {
            "model_key": "worker_forklift",
            "event_type": "forklift_proximity",
            "severity": "Warning",
            "label": "Forklift Near Worker",
            "details": {"subject_id": "worker:w1", "distance": 120},
        }
        event_b = {
            "model_key": "worker_forklift",
            "event_type": "forklift_proximity",
            "severity": "Warning",
            "label": "Forklift Near Worker",
            "details": {"subject_id": "worker:w1", "distance": 80},
        }
        self.assertEqual(manager._build_event_key(event_a), manager._build_event_key(event_b))


class ApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    @patch("apps.inference.views.SourceManager.open_source")
    def test_connect_image_source(self, mock_open_source):
        class Handle:
            frame_width = 1280
            frame_height = 720
            capture = None
            first_frame = np.zeros((720, 1280, 3), dtype=np.uint8)

        mock_open_source.return_value = Handle()
        upload = SimpleUploadedFile("test.jpg", b"fake-image", content_type="image/jpeg")
        response = self.client.post(
            "/api/source/connect/",
            {"source_type": "image", "file": upload},
            format="multipart",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Source.objects.count(), 1)
        self.assertEqual(response.data["source"]["frame_width"], 1280)

    def test_zone_save_round_trip(self):
        source = Source.objects.create(source_type="rtsp", rtsp_url="rtsp://camera")
        payload = {
            "source_id": source.id,
            "zone_type": "danger_zone",
            "points": [{"x": 0.1, "y": 0.1}, {"x": 0.2, "y": 0.1}, {"x": 0.2, "y": 0.2}],
        }
        response = self.client.post("/api/zones/save/", payload, format="json")
        self.assertEqual(response.status_code, 201)
        get_response = self.client.get(f"/api/zones/?source_id={source.id}")
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(len(get_response.data), 1)
