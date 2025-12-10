"""Core app views."""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.reverse import reverse


@api_view(["GET"])
@permission_classes([AllowAny])
def api_root(request, format=None):
    """
    API root view - provides links to main API endpoints.
    """
    return Response(
        {
            "channels": reverse(
                "telegram_channels:channelgroup-list", request=request, format=format
            ),
            "posts": reverse("posts:multi-post-list", request=request, format=format),
            "stats": reverse("stats:stats-overview", request=request, format=format),
            "health": reverse("monitoring:health", request=request, format=format),
        }
    )

