from django.contrib import admin
from django.urls import path, include, re_path
from django.views.generic import TemplateView
from django.conf import settings
from django.conf.urls.static import static
import os


class ReactSnapView(TemplateView):
    def get_template_names(self):
        path = self.request.path.strip("/")
        if not path:
            return ["index.html"]

        safe_path = os.path.normpath(f"{path}/index.html")
        full_path = os.path.join(settings.BASE_DIR, "frontend", "build", safe_path)

        if os.path.exists(full_path):
            return [safe_path]
        else:
            return ["404.html"]


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("users.api_urls")),
    re_path(r"^(?!admin|api).*", ReactSnapView.as_view()),
]


if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
