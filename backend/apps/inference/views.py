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
from .services.model_registry import ModelRegistry
from .services.session_manager import session_manager
from .services.source_manager import SourceManager


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
        session_manager.set_preview(source, handle.first_frame)
        if handle.capture is not None:
            handle.capture.release()

        return Response(
            {
                "source": SourceSerializer(source).data,
                "status": source.status,
            }
        )


class InferenceStartView(APIView):
    def post(self, request):
        serializer = InferenceStartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        source = get_object_or_404(Source, id=serializer.validated_data["source_id"])
        try:
            enabled_models = session_manager.start(source, serializer.validated_data["enabled_models"])
        except (RuntimeError, ValueError) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {
                "status": session_manager.status,
                "session_id": session_manager.session_id,
                "source_id": source.id,
                "enabled_models": enabled_models,
            }
        )


class InferencePauseView(APIView):
    def post(self, request):
        return Response({"status": session_manager.pause()})


class InferenceResumeView(APIView):
    def post(self, request):
        return Response({"status": session_manager.resume()})


class InferenceStopView(APIView):
    def post(self, request):
        session_manager.stop()
        return Response({"status": session_manager.status})


class InferenceFrameView(APIView):
    def get(self, request):
        frame = session_manager.get_latest_frame()
        if not frame:
            return Response({"detail": "No frame available."}, status=status.HTTP_404_NOT_FOUND)
        return HttpResponse(frame, content_type="image/jpeg")


class InferenceStreamView(APIView):
    def get(self, request):
        return StreamingHttpResponse(
            session_manager.stream(),
            content_type="multipart/x-mixed-replace; boundary=frame",
        )


class InferenceResultsView(APIView):
    def get(self, request):
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", settings.SAFEFACTORY_RESULTS_PAGE_SIZE))
        return Response(session_manager.results_payload(page=page, page_size=page_size))


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


class SnapshotView(APIView):
    def post(self, request):
        snapshot = session_manager.save_snapshot()
        serializer = SnapshotSerializer(snapshot, context={"request": request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class SettingsView(APIView):
    def get(self, request):
        registry = ModelRegistry()
        return Response(
            {
                "model_paths": registry.get_public_model_paths(),
                "forklift_warning_distance": settings.SAFEFACTORY_FORKLIFT_WARNING_DISTANCE,
                "forklift_danger_distance": settings.SAFEFACTORY_FORKLIFT_DANGER_DISTANCE,
                "default_confidence": settings.SAFEFACTORY_DEFAULT_CONFIDENCE,
                "result_history_limit": settings.SAFEFACTORY_RESULT_HISTORY_LIMIT,
                "results_page_size": settings.SAFEFACTORY_RESULTS_PAGE_SIZE,
                "max_stream_models": settings.SAFEFACTORY_MAX_STREAM_MODELS,
                "zone_dependencies": {
                    "danger_zone": ["pose_anchor"],
                    "work_zone": ["pose_anchor"],
                    "worker_forklift": ["pose_anchor"],
                },
                "runtime": registry.runtime_info(),
            }
        )
