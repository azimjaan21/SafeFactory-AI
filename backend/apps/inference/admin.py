from django.contrib import admin

from .models import DetectionEvent, Snapshot, Source, Zone


@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = ("id", "source_type", "status", "frame_width", "frame_height", "created_at")
    list_filter = ("source_type", "status")


@admin.register(Zone)
class ZoneAdmin(admin.ModelAdmin):
    list_display = ("id", "source", "zone_type", "created_at")
    list_filter = ("zone_type",)


@admin.register(Snapshot)
class SnapshotAdmin(admin.ModelAdmin):
    list_display = ("id", "source", "created_at")


@admin.register(DetectionEvent)
class DetectionEventAdmin(admin.ModelAdmin):
    list_display = ("id", "source", "model_key", "event_type", "severity", "created_at")
    list_filter = ("model_key", "severity")
