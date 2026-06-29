from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

from .frontend import FrontendAppView


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("apps.inference.urls")),
    re_path(
        r"^assets/(?P<path>.*)$",
        serve,
        {"document_root": settings.PROJECT_ROOT / "frontend" / "dist" / "assets"},
    ),
    path("", FrontendAppView.as_view(), name="frontend-root"),
    re_path(r"^(?!api/|admin/|media/|assets/).*$", FrontendAppView.as_view(), name="frontend-spa"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
