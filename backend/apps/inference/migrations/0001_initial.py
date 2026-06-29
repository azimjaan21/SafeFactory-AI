from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Source",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("source_type", models.CharField(choices=[("rtsp", "RTSP"), ("image", "Image"), ("video", "Video")], max_length=20)),
                ("name", models.CharField(blank=True, max_length=255)),
                ("rtsp_url", models.TextField(blank=True)),
                ("file", models.FileField(blank=True, null=True, upload_to="uploads/")),
                ("status", models.CharField(choices=[("connected", "Connected"), ("disconnected", "Disconnected"), ("running", "Running"), ("paused", "Paused"), ("stopped", "Stopped"), ("completed", "Completed"), ("error", "Error")], default="connected", max_length=20)),
                ("frame_width", models.PositiveIntegerField(default=0)),
                ("frame_height", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name="DetectionEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("session_id", models.CharField(blank=True, max_length=64)),
                ("event_type", models.CharField(max_length=100)),
                ("model_key", models.CharField(max_length=50)),
                ("severity", models.CharField(max_length=20)),
                ("confidence", models.FloatField(blank=True, null=True)),
                ("label", models.CharField(max_length=255)),
                ("details", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("source", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="events", to="inference.source")),
            ],
            options={"ordering": ["-created_at", "-id"]},
        ),
        migrations.CreateModel(
            name="Snapshot",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("image", models.ImageField(upload_to="snapshots/")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("source", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="snapshots", to="inference.source")),
            ],
        ),
        migrations.CreateModel(
            name="Zone",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("zone_type", models.CharField(choices=[("danger_zone", "Danger Zone"), ("work_zone", "Work Zone")], max_length=32)),
                ("points", models.JSONField(default=list)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("source", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="zones", to="inference.source")),
            ],
        ),
    ]
