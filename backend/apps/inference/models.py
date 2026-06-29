from django.db import models


class Source(models.Model):
    TYPE_RTSP = "rtsp"
    TYPE_IMAGE = "image"
    TYPE_VIDEO = "video"
    TYPE_CHOICES = [
        (TYPE_RTSP, "RTSP"),
        (TYPE_IMAGE, "Image"),
        (TYPE_VIDEO, "Video"),
    ]

    STATUS_CONNECTED = "connected"
    STATUS_DISCONNECTED = "disconnected"
    STATUS_RUNNING = "running"
    STATUS_PAUSED = "paused"
    STATUS_STOPPED = "stopped"
    STATUS_COMPLETED = "completed"
    STATUS_ERROR = "error"

    STATUS_CHOICES = [
        (STATUS_CONNECTED, "Connected"),
        (STATUS_DISCONNECTED, "Disconnected"),
        (STATUS_RUNNING, "Running"),
        (STATUS_PAUSED, "Paused"),
        (STATUS_STOPPED, "Stopped"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_ERROR, "Error"),
    ]

    source_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    name = models.CharField(max_length=255, blank=True)
    rtsp_url = models.TextField(blank=True)
    file = models.FileField(upload_to="uploads/", blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_CONNECTED)
    frame_width = models.PositiveIntegerField(default=0)
    frame_height = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.id}:{self.source_type}:{self.status}"

    @property
    def source_path(self):
        if self.file:
            return self.file.path
        return self.rtsp_url


class Zone(models.Model):
    TYPE_DANGER = "danger_zone"
    TYPE_WORK = "work_zone"
    TYPE_CHOICES = [
        (TYPE_DANGER, "Danger Zone"),
        (TYPE_WORK, "Work Zone"),
    ]

    source = models.ForeignKey(Source, on_delete=models.CASCADE, related_name="zones")
    zone_type = models.CharField(max_length=32, choices=TYPE_CHOICES)
    points = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.source_id}:{self.zone_type}"


class Snapshot(models.Model):
    source = models.ForeignKey(Source, on_delete=models.CASCADE, related_name="snapshots", null=True, blank=True)
    image = models.ImageField(upload_to="snapshots/")
    created_at = models.DateTimeField(auto_now_add=True)


class DetectionEvent(models.Model):
    source = models.ForeignKey(Source, on_delete=models.CASCADE, related_name="events", null=True, blank=True)
    session_id = models.CharField(max_length=64, blank=True)
    event_type = models.CharField(max_length=100)
    model_key = models.CharField(max_length=50)
    severity = models.CharField(max_length=20)
    confidence = models.FloatField(null=True, blank=True)
    label = models.CharField(max_length=255)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
