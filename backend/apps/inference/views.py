from django.conf import settings
from django.http import HttpResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Source, Zone
from .serializers import (
    InferenceStartSerializer,
    SnapshotSerializer,
    SourceConnectSerializer,
    SourceSerializer,
    ZoneSaveSerializer,
    ZoneSerializer,
)
from .services.camera_registry import MAX_SLOTS, get_session
from .services.model_registry import ModelRegistry
from .services.source_manager import SourceManager


def _slot(request) -> int:
    try:
        return max(0, min(MAX_SLOTS - 1, int(request.query_params.get("slot", 0))))
    except (TypeError, ValueError):
        return 0


class SourceConnectView(APIView):
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        serializer = SourceConnectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        source = Source(
            source_type=data["source_type"],
            rtsp_url=data.get("rtsp_url", "").strip(),
            status=Source.STATUS_CONNECTED,
        )
        upload = data.get("file")
        if upload:
            source.file = upload
            source.name = upload.name
        source.save()

        try:
            handle = SourceManager().open_source(source)
        except Exception as exc:
            source.status = Source.STATUS_ERROR
            source.save(update_fields=["status", "updated_at"])
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        source.frame_width = handle.frame_width
        source.frame_height = handle.frame_height
        source.status = Source.STATUS_CONNECTED
        source.save(update_fields=["frame_width", "frame_height", "status", "updated_at"])

        sm = get_session(_slot(request))
        sm.set_preview(source, handle.first_frame)
        if handle.capture is not None:
            handle.capture.release()

        return Response({"source": SourceSerializer(source).data, "status": source.status})


class InferenceStartView(APIView):
    def post(self, request):
        serializer = InferenceStartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        source = get_object_or_404(Source, id=serializer.validated_data["source_id"])
        sm = get_session(_slot(request))
        try:
            enabled_models = sm.start(source, serializer.validated_data["enabled_models"])
        except (RuntimeError, ValueError) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            import traceback
            return Response(
                {"detail": f"{type(exc).__name__}: {exc}", "trace": traceback.format_exc()},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response({
            "status": sm.status,
            "session_id": sm.session_id,
            "source_id": source.id,
            "enabled_models": enabled_models,
        })


class InferencePauseView(APIView):
    def post(self, request):
        return Response({"status": get_session(_slot(request)).pause()})


class InferenceResumeView(APIView):
    def post(self, request):
        return Response({"status": get_session(_slot(request)).resume()})


class InferenceStopView(APIView):
    def post(self, request):
        sm = get_session(_slot(request))
        sm.stop()
        return Response({"status": sm.status})


class InferenceFrameView(APIView):
    def get(self, request):
        slot = _slot(request)
        source_id = request.query_params.get("source_id")
        session = get_session(slot)
        if source_id and str(getattr(session, "source_id", "")) != str(source_id):
            return Response({"detail": "No frame available for this source."}, status=status.HTTP_404_NOT_FOUND)
        frame = session.get_latest_frame()
        if not frame:
            return Response({"detail": "No frame available."}, status=status.HTTP_404_NOT_FOUND)
        return HttpResponse(frame, content_type="image/jpeg")


class InferenceStreamView(APIView):
    def get(self, request):
        slot = _slot(request)
        source_id = request.query_params.get("source_id")
        session = get_session(slot)
        if source_id and str(getattr(session, "source_id", "")) != str(source_id):
            return HttpResponse(status=status.HTTP_404_NOT_FOUND)
        return StreamingHttpResponse(
            session.stream(),
            content_type="multipart/x-mixed-replace; boundary=frame",
        )


class InferenceResultsView(APIView):
    def get(self, request):
        try:
            page = int(request.query_params.get("page", 1))
            page_size = int(request.query_params.get("page_size", settings.SAFEFACTORY_RESULTS_PAGE_SIZE))
            return Response(get_session(_slot(request)).results_payload(page=page, page_size=page_size))
        except Exception as exc:
            import traceback
            return Response(
                {"detail": f"{type(exc).__name__}: {exc}", "trace": traceback.format_exc()},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ZonesView(APIView):
    def get(self, request):
        source_id = request.query_params.get("source_id")
        queryset = Zone.objects.all()
        if source_id:
            queryset = queryset.filter(source_id=source_id)
        return Response(ZoneSerializer(queryset, many=True).data)

    def post(self, request):
        serializer = ZoneSaveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        source = get_object_or_404(Source, id=serializer.validated_data["source_id"])
        zone = Zone.objects.create(
            source=source,
            zone_type=serializer.validated_data["zone_type"],
            points=serializer.validated_data["points"],
        )
        return Response(ZoneSerializer(zone).data, status=status.HTTP_201_CREATED)

    def delete(self, request):
        source_id = request.query_params.get("source_id")
        if not source_id:
            return Response({"detail": "source_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        queryset = Zone.objects.filter(source_id=source_id)
        zone_type = request.query_params.get("zone_type")
        if zone_type:
            queryset = queryset.filter(zone_type=zone_type)
        deleted_count, _ = queryset.delete()
        return Response({"deleted": deleted_count})


class SnapshotView(APIView):
    def post(self, request):
        snapshot = get_session(_slot(request)).save_snapshot()
        serializer = SnapshotSerializer(snapshot, context={"request": request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class DemoConnectView(APIView):
    def post(self, request):
        import os
        import cv2 as _cv2

        demo_dir = settings.SAFEFACTORY_DEMO_VIDEO_DIR
        try:
            files = sorted(
                f for f in os.listdir(demo_dir)
                if f.lower().endswith((".mp4", ".avi", ".mov", ".mkv"))
            )
        except FileNotFoundError:
            return Response(
                {"detail": f"Demo video directory not found: {demo_dir}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not files:
            return Response({"detail": "No demo videos found."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            demo_index = int(request.data.get("demo_index", 0))
        except (TypeError, ValueError):
            demo_index = 0
        demo_index = demo_index % len(files)
        video_path = str(demo_dir / files[demo_index])

        cap = _cv2.VideoCapture(video_path)
        ok, frame = cap.read()
        if not ok:
            cap.release()
            return Response({"detail": f"Cannot read demo video: {files[demo_index]}"}, status=status.HTTP_400_BAD_REQUEST)
        frame_w = int(cap.get(_cv2.CAP_PROP_FRAME_WIDTH))
        frame_h = int(cap.get(_cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()

        source = Source.objects.create(
            source_type=Source.TYPE_VIDEO,
            name=f"Demo {demo_index + 1}: {files[demo_index]}",
            rtsp_url=video_path,
            status=Source.STATUS_CONNECTED,
            frame_width=frame_w,
            frame_height=frame_h,
        )
        sm = get_session(_slot(request))
        sm.set_preview(source, frame)
        return Response({"source": SourceSerializer(source).data, "status": source.status})


class SettingsView(APIView):
    def get(self, request):
        registry = ModelRegistry()
        return Response({
            "model_paths": registry.get_public_model_paths(),
            "forklift_warning_distance": settings.SAFEFACTORY_FORKLIFT_WARNING_DISTANCE,
            "forklift_danger_distance": settings.SAFEFACTORY_FORKLIFT_DANGER_DISTANCE,
            "default_confidence": settings.SAFEFACTORY_DEFAULT_CONFIDENCE,
            "result_history_limit": settings.SAFEFACTORY_RESULT_HISTORY_LIMIT,
            "results_page_size": settings.SAFEFACTORY_RESULTS_PAGE_SIZE,
            "max_stream_models": settings.SAFEFACTORY_MAX_STREAM_MODELS,
            "max_camera_slots": MAX_SLOTS,
            "zone_dependencies": {
                "danger_zone": ["pose_anchor"],
                "work_zone": ["pose_anchor"],
                "worker_forklift": ["pose_anchor"],
            },
            "runtime": registry.runtime_info(),
        })
