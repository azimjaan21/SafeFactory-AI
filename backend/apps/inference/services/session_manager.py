from __future__ import annotations

import threading
import time
import uuid
from collections import deque
from datetime import datetime

import cv2
from django.conf import settings
from django.core.files.base import ContentFile

from ..models import DetectionEvent, Snapshot, Source, Zone
from .inference_engine import InferenceEngine
from .source_manager import SourceManager


class SessionManager:
    def __init__(self):
        self.engine = InferenceEngine()
        self.source_manager = SourceManager()
        self._lock = threading.Lock()
        self._reset()

    def _reset(self):
        self.session_id = None
        self.source_id = None
        self.status = "idle"
        self.enabled_models = []
        self.latest_frame = None
        self.latest_jpeg = None
        self.worker_count = 0
        self.events = deque(maxlen=settings.SAFEFACTORY_RESULT_HISTORY_LIMIT)
        self.capture = None
        self.thread = None
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.event_cooldowns = {}

    def start(self, source: Source, enabled_models):
        with self._lock:
            if self.thread and self.thread.is_alive():
                raise RuntimeError("An inference session is already running. Stop it before starting a new one.")
            self.stop()
            handle = self.source_manager.open_source(source)
            self.session_id = uuid.uuid4().hex
            self.source_id = source.id
            self.status = "running"
            self.enabled_models = self.engine.enforce_streaming_limit(source.source_type, enabled_models)
            self.engine.reset_runtime_state()
            self.latest_frame = handle.first_frame.copy()
            self.capture = handle.capture
            self.stop_event = threading.Event()
            self.pause_event = threading.Event()
            self.events = deque(maxlen=settings.SAFEFACTORY_RESULT_HISTORY_LIMIT)
            self.event_cooldowns = {}
            source.status = Source.STATUS_RUNNING
            source.frame_width = handle.frame_width
            source.frame_height = handle.frame_height
            source.save(update_fields=["status", "frame_width", "frame_height", "updated_at"])

            if source.source_type == Source.TYPE_IMAGE:
                result = self.engine.process_frame(handle.first_frame, self.enabled_models, list(source.zones.all()))
                self._store_result(result)
                self.status = "completed"
                source.status = Source.STATUS_COMPLETED
                source.save(update_fields=["status", "updated_at"])
            else:
                self.thread = threading.Thread(target=self._run_stream, args=(source,), daemon=True)
                self.thread.start()
            return self.enabled_models

    def set_preview(self, source: Source, frame):
        self.stop()
        self.session_id = None
        self.source_id = source.id
        self.enabled_models = []
        self.status = source.status
        self._store_preview_frame(frame)

    def _run_stream(self, source: Source):
        while not self.stop_event.is_set():
            if self.pause_event.is_set():
                time.sleep(0.1)
                continue

            ok, frame = self.capture.read()
            if not ok or frame is None:
                self.status = "completed"
                source.status = Source.STATUS_COMPLETED
                source.save(update_fields=["status", "updated_at"])
                break

            zones = list(Zone.objects.filter(source_id=source.id))
            result = self.engine.process_frame(frame, self.enabled_models, zones)
            self._store_result(result)
            time.sleep(0.03)

        if self.capture is not None:
            self.capture.release()
            self.capture = None

    def _store_result(self, result):
        frame = result["frame"]
        self._store_preview_frame(frame)
        self.worker_count = result["worker_count"]
        self._record_events(result["events"])

    def _store_preview_frame(self, frame):
        self.latest_frame = frame
        ok, encoded = cv2.imencode(".jpg", frame)
        if ok:
            self.latest_jpeg = encoded.tobytes()

    def _record_events(self, raw_events):
        now = time.time()
        for event in raw_events:
            event_key = self._build_event_key(event)
            last_timestamp = self.event_cooldowns.get(event_key)
            if last_timestamp and now - last_timestamp < settings.SAFEFACTORY_EVENT_COOLDOWN_SECONDS:
                continue
            self.event_cooldowns[event_key] = now

            event_obj = DetectionEvent.objects.create(
                source_id=self.source_id,
                session_id=self.session_id or "",
                event_type=event["event_type"],
                model_key=event["model_key"],
                severity=event["severity"],
                confidence=event.get("confidence"),
                label=event["label"],
                details=event.get("details", {}),
            )
            self.events.appendleft(
                {
                    "id": event_obj.id,
                    "event_type": event_obj.event_type,
                    "model_key": event_obj.model_key,
                    "severity": event_obj.severity,
                    "confidence": event_obj.confidence,
                    "timestamp": event_obj.created_at.isoformat(),
                    "label": event_obj.label,
                    "details": event_obj.details,
                    "source_id": event_obj.source_id,
                }
            )

    def _build_event_key(self, event):
        details = event.get("details", {})
        subject_id = details.get("subject_id")
        if subject_id:
            return (
                event["model_key"],
                event["event_type"],
                event["severity"],
                subject_id,
            )
        return (
            event["model_key"],
            event["event_type"],
            event["severity"],
            event["label"],
        )

    def pause(self):
        if self.status != "running":
            return self.status
        self.pause_event.set()
        self.status = "paused"
        self._update_source_status(Source.STATUS_PAUSED)
        return self.status

    def resume(self):
        if self.status != "paused":
            return self.status
        self.pause_event.clear()
        self.status = "running"
        self._update_source_status(Source.STATUS_RUNNING)
        return self.status

    def stop(self):
        if hasattr(self, "stop_event") and self.stop_event:
            self.stop_event.set()
        if self.capture is not None:
            self.capture.release()
            self.capture = None
        if self.source_id:
            self._update_source_status(Source.STATUS_STOPPED)
        self.status = "stopped" if self.source_id else "idle"
        self.thread = None

    def _update_source_status(self, status):
        if not self.source_id:
            return
        Source.objects.filter(id=self.source_id).update(status=status)

    def get_latest_frame(self):
        return self.latest_jpeg

    def stream(self):
        while self.status in {"running", "paused", "completed"} or self.latest_jpeg:
            if self.latest_jpeg:
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + self.latest_jpeg + b"\r\n"
                )
            if self.status in {"completed", "stopped", "idle"} and not self.thread:
                break
            time.sleep(0.1)

    def results_payload(self, page=1, page_size=None):
        page_size = page_size or settings.SAFEFACTORY_RESULTS_PAGE_SIZE
        total_events = len(self.events)
        total_pages = max((total_events + page_size - 1) // page_size, 1)
        page = max(1, min(page, total_pages))
        start_index = (page - 1) * page_size
        end_index = start_index + page_size
        return {
            "session_id": self.session_id,
            "source_id": self.source_id,
            "status": self.status,
            "enabled_models": self.enabled_models,
            "worker_count": self.worker_count,
            "events": list(self.events)[start_index:end_index],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_events": total_events,
                "total_pages": total_pages,
            },
        }

    def save_snapshot(self):
        if self.latest_frame is None:
            raise RuntimeError("No annotated frame available.")
        ok, encoded = cv2.imencode(".jpg", self.latest_frame)
        if not ok:
            raise RuntimeError("Failed to encode snapshot.")
        snapshot = Snapshot(source_id=self.source_id)
        filename = f"snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        snapshot.image.save(filename, ContentFile(encoded.tobytes()), save=True)
        return snapshot


session_manager = SessionManager()
