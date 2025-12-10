"""Stats serializers."""

from rest_framework import serializers

from apps.telegram_channels.serializers import ChannelListSerializer, ChannelGroupListSerializer

from .models import (
    ChannelStatsSnapshot,
    DailyChannelStats,
    GlobalStatsSnapshot,
    PostStats,
)


class ChannelStatsSnapshotSerializer(serializers.ModelSerializer):
    """Serializer for ChannelStatsSnapshot model."""

    channel = ChannelListSerializer(read_only=True)

    class Meta:
        model = ChannelStatsSnapshot
        fields = [
            "id",
            "channel",
            "timestamp",
            "subscribers_count",
            "views_last_10_posts",
            "avg_views_per_post",
            "er_last_10_posts",
            "err_last_10_posts",
            "total_posts_count",
            "posts_last_24h",
            "posts_last_7d",
            "meta",
            "created_at",
        ]


class ChannelGrowthSerializer(serializers.Serializer):
    """Serializer for channel growth data."""

    channel_id = serializers.IntegerField()
    channel_title = serializers.CharField()
    current_subscribers = serializers.IntegerField()
    growth_24h = serializers.IntegerField()
    growth_24h_pct = serializers.FloatField()
    growth_7d = serializers.IntegerField()
    growth_7d_pct = serializers.FloatField()
    growth_30d = serializers.IntegerField()
    growth_30d_pct = serializers.FloatField()


class GlobalStatsSnapshotSerializer(serializers.ModelSerializer):
    """Serializer for GlobalStatsSnapshot model."""

    group = ChannelGroupListSerializer(read_only=True)

    class Meta:
        model = GlobalStatsSnapshot
        fields = [
            "id",
            "group",
            "timestamp",
            "total_subscribers",
            "total_views_last_10_posts",
            "avg_er",
            "avg_err",
            "active_channels_count",
            "total_posts_count",
            "meta",
            "created_at",
        ]


class PostStatsSerializer(serializers.ModelSerializer):
    """Serializer for PostStats model."""

    class Meta:
        model = PostStats
        fields = [
            "id",
            "channel_post",
            "timestamp",
            "views",
            "forwards",
            "reactions_count",
            "reactions_breakdown",
            "comments_count",
            "er",
            "err",
            "meta",
            "created_at",
        ]


class DailyChannelStatsSerializer(serializers.ModelSerializer):
    """Serializer for DailyChannelStats model."""

    channel = ChannelListSerializer(read_only=True)

    class Meta:
        model = DailyChannelStats
        fields = [
            "id",
            "channel",
            "date",
            "subscribers_start",
            "subscribers_end",
            "subscribers_change",
            "subscribers_change_pct",
            "posts_count",
            "total_views",
            "avg_views_per_post",
            "total_reactions",
            "total_comments",
            "total_forwards",
            "avg_er",
            "avg_err",
        ]


class StatsOverviewSerializer(serializers.Serializer):
    """Serializer for the stats overview endpoint."""

    total_channel_groups = serializers.IntegerField()
    total_channels = serializers.IntegerField()
    total_subscribers = serializers.IntegerField()
    total_posts = serializers.IntegerField()
    avg_er = serializers.FloatField()
    avg_err = serializers.FloatField()
    top_channels_by_subscribers = ChannelListSerializer(many=True)
    recent_global_stats = GlobalStatsSnapshotSerializer(many=True)

