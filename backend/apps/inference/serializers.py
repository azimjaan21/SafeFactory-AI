from rest_framework import serializers

from .models import DetectionEvent, Snapshot, Source, Zone


MODEL_KEYS = {
    "ppe",
    "pose_anchor",
    "work_situation",
    "smoke_fire",
    "worker_forklift",
    "danger_zone",
    "work_zone",
    "fall_detection",
    "running_detection",
    "inactivity_detection",
}


class SourceConnectSerializer(serializers.Serializer):
    source_type = serializers.ChoiceField(choices=Source.TYPE_CHOICES)
    rtsp_url = serializers.CharField(required=False, allow_blank=True)
    file = serializers.FileField(required=False)

    def validate(self, attrs):
        source_type = attrs["source_type"]
        file = attrs.get("file")
        rtsp_url = attrs.get("rtsp_url", "").strip()

        if source_type == Source.TYPE_RTSP and not rtsp_url:
            raise serializers.ValidationError({"rtsp_url": "RTSP URL is required."})

        if source_type in {Source.TYPE_IMAGE, Source.TYPE_VIDEO} and not file:
            raise serializers.ValidationError({"file": "Uploaded file is required."})

        return attrs


class SourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Source
        fields = [
            "id",
            "source_type",
            "name",
            "rtsp_url",
            "status",
            "frame_width",
            "frame_height",
            "created_at",
            "updated_at",
        ]


class InferenceStartSerializer(serializers.Serializer):
    source_id = serializers.IntegerField()
    enabled_models = serializers.ListField(
        child=serializers.CharField(),
        allow_empty=False,
    )

    def validate_enabled_models(self, value):
        invalid = [item for item in value if item not in MODEL_KEYS]
        if invalid:
            raise serializers.ValidationError(f"Unsupported models: {', '.join(invalid)}")
        return value


class ZoneSerializer(serializers.ModelSerializer):
    source_id = serializers.IntegerField(source="source.id", read_only=True)

    class Meta:
        model = Zone
        fields = ["id", "source_id", "zone_type", "points", "created_at", "updated_at"]


class ZoneSaveSerializer(serializers.Serializer):
    source_id = serializers.IntegerField()
    zone_type = serializers.ChoiceField(choices=Zone.TYPE_CHOICES)
    points = serializers.ListField(child=serializers.DictField(), min_length=3)

    def validate_points(self, value):
        normalized = []
        for point in value:
            x = point.get("x")
            y = point.get("y")
            if x is None or y is None:
                raise serializers.ValidationError("Each point must include x and y.")
            x_value = float(x)
            y_value = float(y)
            if not 0 <= x_value <= 1 or not 0 <= y_value <= 1:
                raise serializers.ValidationError("Zone points must be normalized between 0 and 1.")
            normalized.append({"x": x_value, "y": y_value})
        return normalized


class SnapshotSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Snapshot
        fields = ["id", "source", "image_url", "created_at"]

    def get_image_url(self, obj):
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(obj.image.url)
        return obj.image.url


class DetectionEventSerializer(serializers.ModelSerializer):
    timestamp = serializers.DateTimeField(source="created_at")
    source_id = serializers.IntegerField(source="source.id", allow_null=True)

    class Meta:
        model = DetectionEvent
        fields = [
            "id",
            "event_type",
            "model_key",
            "severity",
            "confidence",
            "timestamp",
            "label",
            "details",
            "source_id",
        ]
