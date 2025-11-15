"""
URL configuration for balanced plate backend.

"""

from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings
from debug_toolbar.toolbar import debug_toolbar_urls
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
    path("api/", include("core.users.urls")),
    path("api/feed/", include("core.feed.urls")),
    path("api/playback/", include("core.playback.urls")),
    path("api/files/", include("core.file_storage.urls")),
    path("api/wallet/", include("core.wallet.urls")),
    path("api/webhook/", include("core.webhook.urls"))
]

if not settings.PRODUCTION:
    urlpatterns += debug_toolbar_urls()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

