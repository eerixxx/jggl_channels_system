"""Monitoring views for health checks and readiness probes."""

import logging
from datetime import timedelta

from django.conf import settings
from django.db import connection
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

logger = logging.getLogger(__name__)


@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    """
    Liveness probe endpoint.
    Returns 200 if the application is running.
    """
    return Response({"status": "ok"})


@api_view(["GET"])
@permission_classes([AllowAny])
def ready(request):
    """
    Readiness probe endpoint.
    Returns 200 if all dependencies are healthy.
    """
    checks = {
        "database": check_database(),
        "redis": check_redis(),
        "celery": check_celery(),
    }

    all_healthy = all(check["healthy"] for check in checks.values())

    return Response(
        {"status": "ready" if all_healthy else "not_ready", "checks": checks},
        status=status.HTTP_200_OK if all_healthy else status.HTTP_503_SERVICE_UNAVAILABLE,
    )


def check_database() -> dict:
    """Check database connectivity."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return {"healthy": True, "message": "Connected"}
    except Exception as e:
        logger.error(f"Database check failed: {e}")
        return {"healthy": False, "message": str(e)}


def check_redis() -> dict:
    """Check Redis connectivity."""
    try:
        from django.core.cache import cache

        cache.set("health_check", "ok", timeout=10)
        value = cache.get("health_check")
        if value == "ok":
            return {"healthy": True, "message": "Connected"}
        return {"healthy": False, "message": "Cache read/write failed"}
    except Exception as e:
        logger.error(f"Redis check failed: {e}")
        return {"healthy": False, "message": str(e)}


def check_celery() -> dict:
    """Check Celery worker connectivity."""
    try:
        from backend.celery import app

        # Check if there are active workers
        inspect = app.control.inspect()
        active = inspect.active()

        if active:
            worker_count = len(active)
            return {"healthy": True, "message": f"{worker_count} worker(s) active"}
        return {"healthy": False, "message": "No active workers"}
    except Exception as e:
        logger.error(f"Celery check failed: {e}")
        return {"healthy": False, "message": str(e)}


@api_view(["GET"])
@permission_classes([AllowAny])
def status_view(request):
    """
    Detailed system status for debugging.
    """
    from apps.telegram_channels.models import Channel, ChannelGroup
    from apps.posts.models import MultiChannelPost, ChannelPost

    try:
        # Get basic stats
        stats = {
            "channel_groups": ChannelGroup.objects.count(),
            "channels": {
                "total": Channel.objects.count(),
                "active": Channel.objects.filter(is_active=True).count(),
                "bot_configured": Channel.objects.filter(
                    bot_admin=True, bot_can_post=True
                ).count(),
            },
            "posts": {
                "total": MultiChannelPost.objects.count(),
                "published": MultiChannelPost.objects.filter(status="published").count(),
                "draft": MultiChannelPost.objects.filter(status="draft").count(),
            },
            "channel_posts": {
                "total": ChannelPost.objects.count(),
                "published": ChannelPost.objects.filter(status="published").count(),
                "failed": ChannelPost.objects.filter(status="failed").count(),
            },
        }

        # Get recent activity
        recent_cutoff = timezone.now() - timedelta(hours=24)
        stats["recent_24h"] = {
            "posts_created": MultiChannelPost.objects.filter(
                created_at__gte=recent_cutoff
            ).count(),
            "posts_published": ChannelPost.objects.filter(
                published_at__gte=recent_cutoff
            ).count(),
        }

        return Response({
            "status": "ok",
            "timestamp": timezone.now().isoformat(),
            "stats": stats,
        })

    except Exception as e:
        logger.exception(f"Status check failed: {e}")
        return Response(
            {"status": "error", "message": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([AllowAny])
def celery_status(request):
    """
    Get Celery workers status.
    """
    try:
        from backend.celery import app

        inspect = app.control.inspect()

        return Response({
            "status": "ok",
            "active": inspect.active() or {},
            "scheduled": inspect.scheduled() or {},
            "reserved": inspect.reserved() or {},
            "stats": inspect.stats() or {},
        })

    except Exception as e:
        logger.exception(f"Celery status check failed: {e}")
        return Response(
            {"status": "error", "message": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

