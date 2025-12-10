"""Stats admin configuration."""

from django.contrib import admin
from django.utils.html import format_html

from .models import (
    ChannelStatsSnapshot,
    DailyChannelStats,
    GlobalStatsSnapshot,
    PostStats,
)


@admin.register(ChannelStatsSnapshot)
class ChannelStatsSnapshotAdmin(admin.ModelAdmin):
    """Admin for ChannelStatsSnapshot model."""

    list_display = [
        "channel",
        "timestamp",
        "subscribers_count",
        "views_last_10_posts",
        "er_display",
        "err_display",
    ]
    list_filter = ["channel__group", "channel", "timestamp"]
    search_fields = ["channel__title", "channel__username"]
    ordering = ["-timestamp"]
    date_hierarchy = "timestamp"
    raw_id_fields = ["channel"]

    fieldsets = (
        (None, {"fields": ("channel", "timestamp")}),
        (
            "Subscriber Metrics",
            {"fields": ("subscribers_count",)},
        ),
        (
            "Post Metrics",
            {
                "fields": (
                    "views_last_10_posts",
                    "avg_views_per_post",
                    "total_posts_count",
                    "posts_last_24h",
                    "posts_last_7d",
                )
            },
        ),
        (
            "Engagement Metrics",
            {"fields": ("er_last_10_posts", "err_last_10_posts")},
        ),
        (
            "Metadata",
            {"fields": ("meta",), "classes": ("collapse",)},
        ),
    )
    readonly_fields = ["timestamp", "created_at", "updated_at"]

    def er_display(self, obj):
        return f"{obj.er_last_10_posts:.2f}%"

    er_display.short_description = "ER"

    def err_display(self, obj):
        return f"{obj.err_last_10_posts:.2f}%"

    err_display.short_description = "ERR"


@admin.register(GlobalStatsSnapshot)
class GlobalStatsSnapshotAdmin(admin.ModelAdmin):
    """Admin for GlobalStatsSnapshot model."""

    list_display = [
        "group",
        "timestamp",
        "total_subscribers",
        "active_channels_count",
        "avg_er_display",
        "avg_err_display",
    ]
    list_filter = ["group", "timestamp"]
    search_fields = ["group__name"]
    ordering = ["-timestamp"]
    date_hierarchy = "timestamp"
    raw_id_fields = ["group"]

    fieldsets = (
        (None, {"fields": ("group", "timestamp")}),
        (
            "Aggregated Metrics",
            {
                "fields": (
                    "total_subscribers",
                    "total_views_last_10_posts",
                    "active_channels_count",
                    "total_posts_count",
                )
            },
        ),
        (
            "Engagement Metrics",
            {"fields": ("avg_er", "avg_err")},
        ),
        (
            "Breakdown",
            {"fields": ("meta",), "classes": ("collapse",)},
        ),
    )
    readonly_fields = ["timestamp", "created_at", "updated_at"]

    def avg_er_display(self, obj):
        return f"{obj.avg_er:.2f}%"

    avg_er_display.short_description = "Avg ER"

    def avg_err_display(self, obj):
        return f"{obj.avg_err:.2f}%"

    avg_err_display.short_description = "Avg ERR"


@admin.register(PostStats)
class PostStatsAdmin(admin.ModelAdmin):
    """Admin for PostStats model."""

    list_display = [
        "channel_post",
        "timestamp",
        "views",
        "reactions_count",
        "comments_count",
        "forwards",
        "er_display",
        "err_display",
    ]
    list_filter = [
        "channel_post__channel__group",
        "channel_post__channel",
        "timestamp",
    ]
    search_fields = [
        "channel_post__multi_post__internal_title",
        "channel_post__channel__title",
    ]
    ordering = ["-timestamp"]
    date_hierarchy = "timestamp"
    raw_id_fields = ["channel_post"]

    fieldsets = (
        (None, {"fields": ("channel_post", "timestamp")}),
        (
            "View Metrics",
            {"fields": ("views", "forwards")},
        ),
        (
            "Reactions",
            {"fields": ("reactions_count", "reactions_breakdown")},
        ),
        (
            "Comments",
            {"fields": ("comments_count",)},
        ),
        (
            "Engagement Metrics",
            {"fields": ("er", "err")},
        ),
        (
            "Metadata",
            {"fields": ("meta",), "classes": ("collapse",)},
        ),
    )
    readonly_fields = ["timestamp", "created_at", "updated_at"]

    def er_display(self, obj):
        return f"{obj.er:.2f}%"

    er_display.short_description = "ER"

    def err_display(self, obj):
        return f"{obj.err:.2f}%"

    err_display.short_description = "ERR"


@admin.register(DailyChannelStats)
class DailyChannelStatsAdmin(admin.ModelAdmin):
    """Admin for DailyChannelStats model."""

    list_display = [
        "channel",
        "date",
        "subscribers_end",
        "subscribers_change_display",
        "posts_count",
        "total_views",
        "avg_er_display",
    ]
    list_filter = ["channel__group", "channel", "date"]
    search_fields = ["channel__title", "channel__username"]
    ordering = ["-date"]
    date_hierarchy = "date"
    raw_id_fields = ["channel"]

    fieldsets = (
        (None, {"fields": ("channel", "date")}),
        (
            "Subscribers",
            {
                "fields": (
                    "subscribers_start",
                    "subscribers_end",
                    "subscribers_change",
                    "subscribers_change_pct",
                )
            },
        ),
        (
            "Posts",
            {
                "fields": (
                    "posts_count",
                    "total_views",
                    "avg_views_per_post",
                )
            },
        ),
        (
            "Engagement",
            {
                "fields": (
                    "total_reactions",
                    "total_comments",
                    "total_forwards",
                    "avg_er",
                    "avg_err",
                )
            },
        ),
    )

    def subscribers_change_display(self, obj):
        if obj.subscribers_change > 0:
            return format_html(
                '<span style="color: green;">+{} ({:.1f}%)</span>',
                obj.subscribers_change,
                obj.subscribers_change_pct,
            )
        elif obj.subscribers_change < 0:
            return format_html(
                '<span style="color: red;">{} ({:.1f}%)</span>',
                obj.subscribers_change,
                obj.subscribers_change_pct,
            )
        return "0"

    subscribers_change_display.short_description = "Subs Change"

    def avg_er_display(self, obj):
        return f"{obj.avg_er:.2f}%"

    avg_er_display.short_description = "Avg ER"

