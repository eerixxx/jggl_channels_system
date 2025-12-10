"""Stats URL configuration."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ChannelStatsSnapshotViewSet,
    DailyChannelStatsViewSet,
    GlobalStatsSnapshotViewSet,
    PostStatsViewSet,
    channel_growth,
    group_comparison,
    stats_overview,
)

app_name = "stats"

router = DefaultRouter()
router.register(r"channel-snapshots", ChannelStatsSnapshotViewSet, basename="channel-snapshot")
router.register(r"global-snapshots", GlobalStatsSnapshotViewSet, basename="global-snapshot")
router.register(r"post-stats", PostStatsViewSet, basename="post-stats")
router.register(r"daily", DailyChannelStatsViewSet, basename="daily-stats")

urlpatterns = [
    path("", include(router.urls)),
    path("overview/", stats_overview, name="stats-overview"),
    path("channel/<int:channel_id>/growth/", channel_growth, name="channel-growth"),
    path("group/<int:group_id>/comparison/", group_comparison, name="group-comparison"),
]

