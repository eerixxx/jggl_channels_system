"""
URL configuration for channels_admin project.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),
    # API v1
    path("api/v1/", include("apps.core.urls")),
    path("api/v1/channels/", include("apps.telegram_channels.urls")),
    path("api/v1/posts/", include("apps.posts.urls")),
    path("api/v1/stats/", include("apps.stats.urls")),
    path("api/v1/bot/", include("apps.integrations.telegram_bot.urls")),
    # Monitoring
    path("", include("apps.monitoring.urls")),
    # Prometheus metrics
    path("", include("django_prometheus.urls")),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

    # Debug toolbar
    try:
        import debug_toolbar

        urlpatterns = [
            path("__debug__/", include(debug_toolbar.urls)),
        ] + urlpatterns
    except ImportError:
        pass

# Customize admin site
admin.site.site_header = "Telegram Channels Admin"
admin.site.site_title = "Channels Admin"
admin.site.index_title = "Dashboard"

