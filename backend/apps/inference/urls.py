from django.urls import path

from .views import (
    DemoConnectView,
    InferenceFrameView,
    InferencePauseView,
    InferenceResultsView,
    InferenceResumeView,
    InferenceStartView,
    InferenceStopView,
    InferenceStreamView,
    SettingsView,
    SnapshotView,
    SourceConnectView,
    ZonesView,
)


urlpatterns = [
    path("source/connect/", SourceConnectView.as_view(), name="source-connect"),
    path("source/connect-demo/", DemoConnectView.as_view(), name="source-connect-demo"),
    path("inference/start/", InferenceStartView.as_view(), name="inference-start"),
    path("inference/pause/", InferencePauseView.as_view(), name="inference-pause"),
    path("inference/resume/", InferenceResumeView.as_view(), name="inference-resume"),
    path("inference/stop/", InferenceStopView.as_view(), name="inference-stop"),
    path("inference/frame/", InferenceFrameView.as_view(), name="inference-frame"),
    path("inference/stream/", InferenceStreamView.as_view(), name="inference-stream"),
    path("inference/results/", InferenceResultsView.as_view(), name="inference-results"),
    path("zones/save/", ZonesView.as_view(), name="zones-save"),
    path("zones/", ZonesView.as_view(), name="zones-list"),
    path("snapshot/", SnapshotView.as_view(), name="snapshot"),
    path("settings/", SettingsView.as_view(), name="settings"),
]
