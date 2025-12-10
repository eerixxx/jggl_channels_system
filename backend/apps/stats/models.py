"""Statistics models for tracking channel and post metrics."""

from django.db import models
from django.utils import timezone
from datetime import timedelta

from apps.core.models import TimestampedModel
from apps.telegram_channels.models import Channel, ChannelGroup
from apps.posts.models import ChannelPost


class ChannelStatsSnapshot(TimestampedModel):
    """
    Snapshot of channel statistics at a specific point in time.
    Used for tracking historical data and calculating growth.
    """

    channel = models.ForeignKey(
        Channel,
        on_delete=models.CASCADE,
        related_name="stats_snapshots",
    )
    timestamp = models.DateTimeField(
        db_index=True,
        help_text="When this snapshot was taken",
    )

    # Subscriber metrics
    subscribers_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of subscribers at this time",
    )

    # Post metrics (calculated from last 10 posts)
    views_last_10_posts = models.PositiveIntegerField(
        default=0,
        help_text="Total views on last 10 posts",
    )
    avg_views_per_post = models.FloatField(
        default=0,
        help_text="Average views per post (last 10)",
    )

    # Engagement metrics
    er_last_10_posts = models.FloatField(
        default=0,
        help_text="Engagement Rate (last 10 posts): (likes+comments+forwards)/subscribers*100",
    )
    err_last_10_posts = models.FloatField(
        default=0,
        help_text="Engagement Rate by Reach (last 10 posts): (likes+comments)/views*100",
    )

    # Additional metrics
    total_posts_count = models.PositiveIntegerField(
        default=0,
        help_text="Total number of posts in channel",
    )
    posts_last_24h = models.PositiveIntegerField(
        default=0,
        help_text="Posts published in last 24 hours",
    )
    posts_last_7d = models.PositiveIntegerField(
        default=0,
        help_text="Posts published in last 7 days",
    )

    # Raw data
    meta = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional metadata from the source",
    )

    class Meta:
        ordering = ["-timestamp"]
        verbose_name = "Channel Stats Snapshot"
        verbose_name_plural = "Channel Stats Snapshots"
        indexes = [
            models.Index(fields=["channel", "-timestamp"]),
            models.Index(fields=["timestamp"]),
        ]

    def __str__(self):
        return f"{self.channel} - {self.timestamp.strftime('%Y-%m-%d %H:%M')}"

    @classmethod
    def get_latest_for_channel(cls, channel: Channel):
        """Get the most recent snapshot for a channel."""
        return cls.objects.filter(channel=channel).order_by("-timestamp").first()

    @classmethod
    def get_growth(cls, channel: Channel, days: int = 7):
        """
        Calculate subscriber growth over a period.
        Returns (absolute_change, percentage_change).
        """
        now = timezone.now()
        current = cls.get_latest_for_channel(channel)
        past = cls.objects.filter(
            channel=channel,
            timestamp__lte=now - timedelta(days=days),
        ).order_by("-timestamp").first()

        if not current or not past:
            return 0, 0.0

        absolute = current.subscribers_count - past.subscribers_count
        percentage = (
            (absolute / past.subscribers_count * 100)
            if past.subscribers_count > 0
            else 0.0
        )

        return absolute, round(percentage, 2)


class GlobalStatsSnapshot(TimestampedModel):
    """
    Aggregated statistics for a channel group.
    """

    group = models.ForeignKey(
        ChannelGroup,
        on_delete=models.CASCADE,
        related_name="stats_snapshots",
    )
    timestamp = models.DateTimeField(
        db_index=True,
        help_text="When this snapshot was taken",
    )

    # Aggregated metrics
    total_subscribers = models.PositiveIntegerField(
        default=0,
        help_text="Sum of subscribers across all channels",
    )
    total_views_last_10_posts = models.PositiveIntegerField(
        default=0,
        help_text="Sum of views on last 10 posts per channel",
    )
    avg_er = models.FloatField(
        default=0,
        help_text="Average ER across all channels",
    )
    avg_err = models.FloatField(
        default=0,
        help_text="Average ERR across all channels",
    )

    # Channel counts
    active_channels_count = models.PositiveIntegerField(
        default=0,
    )
    total_posts_count = models.PositiveIntegerField(
        default=0,
    )

    # Raw data
    meta = models.JSONField(
        default=dict,
        blank=True,
        help_text="Detailed breakdown by channel",
    )

    class Meta:
        ordering = ["-timestamp"]
        verbose_name = "Global Stats Snapshot"
        verbose_name_plural = "Global Stats Snapshots"
        indexes = [
            models.Index(fields=["group", "-timestamp"]),
        ]

    def __str__(self):
        return f"{self.group.name} - {self.timestamp.strftime('%Y-%m-%d %H:%M')}"

    @classmethod
    def calculate_for_group(cls, group: ChannelGroup):
        """
        Calculate and create a new global stats snapshot for a group.
        """
        now = timezone.now()
        channels = group.channels.filter(is_active=True)

        total_subscribers = 0
        total_views = 0
        er_sum = 0
        err_sum = 0
        channel_count = 0
        breakdown = {}

        for channel in channels:
            latest = ChannelStatsSnapshot.get_latest_for_channel(channel)
            if latest:
                total_subscribers += latest.subscribers_count
                total_views += latest.views_last_10_posts
                er_sum += latest.er_last_10_posts
                err_sum += latest.err_last_10_posts
                channel_count += 1

                breakdown[str(channel.pk)] = {
                    "title": channel.title,
                    "language": channel.language.code,
                    "subscribers": latest.subscribers_count,
                    "views": latest.views_last_10_posts,
                    "er": latest.er_last_10_posts,
                    "err": latest.err_last_10_posts,
                }

        return cls.objects.create(
            group=group,
            timestamp=now,
            total_subscribers=total_subscribers,
            total_views_last_10_posts=total_views,
            avg_er=er_sum / channel_count if channel_count > 0 else 0,
            avg_err=err_sum / channel_count if channel_count > 0 else 0,
            active_channels_count=channel_count,
            total_posts_count=sum(
                ch.get("posts_count", 0) for ch in breakdown.values()
            ),
            meta={"channels": breakdown},
        )


class PostStats(TimestampedModel):
    """
    Statistics for a single published channel post.
    Multiple records per post allow tracking changes over time.
    """

    channel_post = models.ForeignKey(
        ChannelPost,
        on_delete=models.CASCADE,
        related_name="stats",
    )
    timestamp = models.DateTimeField(
        db_index=True,
        help_text="When this snapshot was taken",
    )

    # Core metrics
    views = models.PositiveIntegerField(
        default=0,
        help_text="Number of views",
    )
    forwards = models.PositiveIntegerField(
        default=0,
        help_text="Number of forwards/shares",
    )

    # Reactions (if available)
    reactions_count = models.PositiveIntegerField(
        default=0,
        help_text="Total reactions count",
    )
    reactions_breakdown = models.JSONField(
        default=dict,
        blank=True,
        help_text="Breakdown of reactions by type (emoji -> count)",
    )

    # Comments (if channel has discussion group)
    comments_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of comments",
    )

    # Calculated metrics
    er = models.FloatField(
        default=0,
        help_text="Engagement Rate: (reactions+comments+forwards)/subscribers*100",
    )
    err = models.FloatField(
        default=0,
        help_text="Engagement Rate by Reach: (reactions+comments)/views*100",
    )

    # Raw data
    meta = models.JSONField(
        default=dict,
        blank=True,
    )

    class Meta:
        ordering = ["-timestamp"]
        verbose_name = "Post Stats"
        verbose_name_plural = "Post Stats"
        indexes = [
            models.Index(fields=["channel_post", "-timestamp"]),
        ]

    def __str__(self):
        return f"{self.channel_post} - {self.timestamp.strftime('%Y-%m-%d %H:%M')}"

    @classmethod
    def get_latest_for_post(cls, channel_post: ChannelPost):
        """Get the most recent stats for a post."""
        return cls.objects.filter(channel_post=channel_post).order_by("-timestamp").first()

    def calculate_engagement(self, subscribers_count: int):
        """
        Calculate ER and ERR metrics.
        """
        total_engagement = self.reactions_count + self.comments_count + self.forwards

        # ER: engagement relative to subscribers
        if subscribers_count > 0:
            self.er = round((total_engagement / subscribers_count) * 100, 2)
        else:
            self.er = 0

        # ERR: engagement relative to views
        if self.views > 0:
            interaction = self.reactions_count + self.comments_count
            self.err = round((interaction / self.views) * 100, 2)
        else:
            self.err = 0

        self.save(update_fields=["er", "err", "updated_at"])


class DailyChannelStats(models.Model):
    """
    Daily aggregated statistics for channels.
    Pre-computed for faster dashboard queries.
    """

    channel = models.ForeignKey(
        Channel,
        on_delete=models.CASCADE,
        related_name="daily_stats",
    )
    date = models.DateField(db_index=True)

    # Subscribers
    subscribers_start = models.PositiveIntegerField(default=0)
    subscribers_end = models.PositiveIntegerField(default=0)
    subscribers_change = models.IntegerField(default=0)
    subscribers_change_pct = models.FloatField(default=0)

    # Posts
    posts_count = models.PositiveIntegerField(default=0)
    total_views = models.PositiveIntegerField(default=0)
    avg_views_per_post = models.FloatField(default=0)

    # Engagement
    total_reactions = models.PositiveIntegerField(default=0)
    total_comments = models.PositiveIntegerField(default=0)
    total_forwards = models.PositiveIntegerField(default=0)
    avg_er = models.FloatField(default=0)
    avg_err = models.FloatField(default=0)

    class Meta:
        ordering = ["-date"]
        verbose_name = "Daily Channel Stats"
        verbose_name_plural = "Daily Channel Stats"
        unique_together = ["channel", "date"]
        indexes = [
            models.Index(fields=["channel", "-date"]),
            models.Index(fields=["-date"]),
        ]

    def __str__(self):
        return f"{self.channel} - {self.date}"

    @classmethod
    def compute_for_channel(cls, channel: Channel, date):
        """
        Compute daily stats for a channel on a specific date.
        """
        from datetime import datetime, time

        start_dt = datetime.combine(date, time.min)
        end_dt = datetime.combine(date, time.max)

        # Get subscriber counts
        start_snapshot = ChannelStatsSnapshot.objects.filter(
            channel=channel,
            timestamp__lte=start_dt,
        ).order_by("-timestamp").first()

        end_snapshot = ChannelStatsSnapshot.objects.filter(
            channel=channel,
            timestamp__lte=end_dt,
        ).order_by("-timestamp").first()

        subs_start = start_snapshot.subscribers_count if start_snapshot else 0
        subs_end = end_snapshot.subscribers_count if end_snapshot else 0

        # Get post stats for the day
        from django.db.models import Sum, Avg, Count

        daily_post_stats = PostStats.objects.filter(
            channel_post__channel=channel,
            channel_post__published_at__date=date,
        ).aggregate(
            total_views=Sum("views"),
            total_reactions=Sum("reactions_count"),
            total_comments=Sum("comments_count"),
            total_forwards=Sum("forwards"),
            avg_er=Avg("er"),
            avg_err=Avg("err"),
            posts_count=Count("channel_post", distinct=True),
        )

        posts_count = daily_post_stats["posts_count"] or 0
        total_views = daily_post_stats["total_views"] or 0

        daily, _ = cls.objects.update_or_create(
            channel=channel,
            date=date,
            defaults={
                "subscribers_start": subs_start,
                "subscribers_end": subs_end,
                "subscribers_change": subs_end - subs_start,
                "subscribers_change_pct": (
                    ((subs_end - subs_start) / subs_start * 100)
                    if subs_start > 0
                    else 0
                ),
                "posts_count": posts_count,
                "total_views": total_views,
                "avg_views_per_post": (
                    total_views / posts_count if posts_count > 0 else 0
                ),
                "total_reactions": daily_post_stats["total_reactions"] or 0,
                "total_comments": daily_post_stats["total_comments"] or 0,
                "total_forwards": daily_post_stats["total_forwards"] or 0,
                "avg_er": daily_post_stats["avg_er"] or 0,
                "avg_err": daily_post_stats["avg_err"] or 0,
            },
        )

        return daily

