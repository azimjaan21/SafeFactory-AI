from pathlib import Path

from django.http import Http404, FileResponse
from django.views import View


class FrontendAppView(View):
    def get(self, request, *args, **kwargs):
        frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
        index_path = frontend_dist / "index.html"
        if not index_path.exists():
            raise Http404("Frontend build not found. Run `npm.cmd run build` in the frontend directory.")
        return FileResponse(index_path.open("rb"), content_type="text/html")
