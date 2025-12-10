"""Stats views."""

from datetime import timedelta

from django.db.models import Avg, Sum
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.telegram_channels.models import Channel, ChannelGroup

from .models import (
    ChannelStatsSnapshot,
    DailyChannelStats,
    GlobalStatsSnapshot,
    PostStats,
)
from .serializers import (
    ChannelGrowthSerializer,
    ChannelStatsSnapshotSerializer,
    DailyChannelStatsSerializer,
    GlobalStatsSnapshotSerializer,
    PostStatsSerializer,
)


class ChannelStatsSnapshotViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for ChannelStatsSnapshot model."""

    queryset = ChannelStatsSnapshot.objects.select_related("channel")
    serializer_class = ChannelStatsSnapshotSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["channel", "channel__group"]
    ordering_fields = ["timestamp", "subscribers_count"]
    ordering = ["-timestamp"]


class GlobalStatsSnapshotViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for GlobalStatsSnapshot model."""

    queryset = GlobalStatsSnapshot.objects.select_related("group")
    serializer_class = GlobalStatsSnapshotSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["group"]
    ordering_fields = ["timestamp", "total_subscribers"]
    ordering = ["-timestamp"]


class PostStatsViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for PostStats model."""

    queryset = PostStats.objects.select_related(
        "channel_post", "channel_post__channel"
    )
    serializer_class = PostStatsSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["channel_post", "channel_post__channel"]
    ordering_fields = ["timestamp", "views", "er", "err"]
    ordering = ["-timestamp"]


class DailyChannelStatsViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for DailyChannelStats model."""

    queryset = DailyChannelStats.objects.select_related("channel")
    serializer_class = DailyChannelStatsSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["channel", "channel__group"]
    ordering_fields = ["date", "subscribers_end", "avg_er"]
    ordering = ["-date"]


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def stats_overview(request):
    """
    Get overall statistics overview for the dashboard.
    """
    # Get totals
    total_groups = ChannelGroup.objects.filter(is_active=True).count()
    total_channels = Channel.objects.filter(is_active=True).count()

    # Get latest stats
    latest_channel_stats = {}
    for channel in Channel.objects.filter(is_active=True):
        latest = ChannelStatsSnapshot.get_latest_for_channel(channel)
        if latest:
            latest_channel_stats[channel.pk] = latest

    total_subscribers = sum(
        s.subscribers_count for s in latest_channel_stats.values()
    )

    # Calculate averages
    er_values = [s.er_last_10_posts for s in latest_channel_stats.values() if s.er_last_10_posts]
    err_values = [s.err_last_10_posts for s in latest_channel_stats.values() if s.err_last_10_posts]

    avg_er = sum(er_values) / len(er_values) if er_values else 0
    avg_err = sum(err_values) / len(err_values) if err_values else 0

    # Get top channels
    top_channels = Channel.objects.filter(
        is_active=True
    ).order_by("-member_count")[:5]

    # Get recent global stats
    recent_global = GlobalStatsSnapshot.objects.select_related("group").order_by(
        "-timestamp"
    )[:10]

    return Response({
        "total_channel_groups": total_groups,
        "total_channels": total_channels,
        "total_subscribers": total_subscribers,
        "avg_er": round(avg_er, 2),
        "avg_err": round(avg_err, 2),
        "top_channels": [
            {
                "id": ch.pk,
                "title": ch.title,
                "username": ch.username,
                "member_count": ch.member_count,
                "language": ch.language.code,
            }
            for ch in top_channels
        ],
        "recent_global_stats": GlobalStatsSnapshotSerializer(
            recent_global, many=True
        ).data,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def channel_growth(request, channel_id):
    """
    Get growth statistics for a specific channel.
    """
    try:
        channel = Channel.objects.get(pk=channel_id)
    except Channel.DoesNotExist:
        return Response({"error": "Channel not found"}, status=404)

    latest = ChannelStatsSnapshot.get_latest_for_channel(channel)
    if not latest:
        return Response({"error": "No stats available for this channel"}, status=404)

    growth_24h, growth_24h_pct = ChannelStatsSnapshot.get_growth(channel, days=1)
    growth_7d, growth_7d_pct = ChannelStatsSnapshot.get_growth(channel, days=7)
    growth_30d, growth_30d_pct = ChannelStatsSnapshot.get_growth(channel, days=30)

    data = {
        "channel_id": channel.pk,
        "channel_title": channel.title,
        "current_subscribers": latest.subscribers_count,
        "growth_24h": growth_24h,
        "growth_24h_pct": growth_24h_pct,
        "growth_7d": growth_7d,
        "growth_7d_pct": growth_7d_pct,
        "growth_30d": growth_30d,
        "growth_30d_pct": growth_30d_pct,
    }

    serializer = ChannelGrowthSerializer(data)
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def group_comparison(request, group_id):
    """
    Compare stats across all channels in a group.
    """
    try:
        group = ChannelGroup.objects.get(pk=group_id)
    except ChannelGroup.DoesNotExist:
        return Response({"error": "Group not found"}, status=404)

    channels_data = []
    for channel in group.channels.filter(is_active=True).select_related("language"):
        latest = ChannelStatsSnapshot.get_latest_for_channel(channel)
        if latest:
            growth_7d, growth_7d_pct = ChannelStatsSnapshot.get_growth(channel, days=7)
            channels_data.append({
                "channel_id": channel.pk,
                "title": channel.title,
                "language": channel.language.code,
                "language_name": channel.language.name,
                "subscribers": latest.subscribers_count,
                "growth_7d": growth_7d,
                "growth_7d_pct": growth_7d_pct,
                "views_last_10": latest.views_last_10_posts,
                "er": latest.er_last_10_posts,
                "err": latest.err_last_10_posts,
            })

    # Sort by subscribers
    channels_data.sort(key=lambda x: x["subscribers"], reverse=True)

    return Response({
        "group_id": group.pk,
        "group_name": group.name,
        "channels": channels_data,
    })

