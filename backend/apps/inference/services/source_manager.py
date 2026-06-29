from __future__ import annotations

from dataclasses import dataclass

import cv2

from ..models import Source


@dataclass
class SourceHandle:
    source_type: str
    source_path: str
    first_frame: object
    frame_width: int
    frame_height: int
    capture: object = None
    is_streaming: bool = False


class SourceManager:
    def open_source(self, source: Source):
        source_path = source.source_path

        if source.source_type == Source.TYPE_IMAGE:
            frame = cv2.imread(source_path)
            if frame is None:
                raise ValueError("Failed to read uploaded image.")
            height, width = frame.shape[:2]
            return SourceHandle(
                source_type=source.source_type,
                source_path=source_path,
                first_frame=frame,
                frame_width=width,
                frame_height=height,
                is_streaming=False,
            )

        capture_source = int(source_path) if str(source_path).isdigit() else source_path
        capture = cv2.VideoCapture(capture_source)
        if not capture.isOpened():
            raise ValueError("Failed to open video source.")
        ok, frame = capture.read()
        if not ok or frame is None:
            capture.release()
            raise ValueError("Failed to read first frame from source.")
        height, width = frame.shape[:2]
        capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
        return SourceHandle(
            source_type=source.source_type,
            source_path=str(capture_source),
            first_frame=frame,
            frame_width=width,
            frame_height=height,
            capture=capture,
            is_streaming=True,
        )
