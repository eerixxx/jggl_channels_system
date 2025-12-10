"""Stats Celery tasks."""

import logging
from datetime import date, timedelta

from celery import shared_task
from django.utils import timezone

from apps.telegram_channels.models import Channel, ChannelGroup

from .models import (
    ChannelStatsSnapshot,
    DailyChannelStats,
    GlobalStatsSnapshot,
)

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def sync_channel_stats(self, channel_id: int):
    """
    Sync statistics for a single channel from the bot service.
    """
    try:
        channel = Channel.objects.get(pk=channel_id)
    except Channel.DoesNotExist:
        logger.error(f"Channel {channel_id} not found")
        return

    try:
        from apps.integrations.telegram_bot.client import TelegramBotClient

        client = TelegramBotClient()
        stats = client.get_channel_stats_sync(channel.telegram_chat_id)

        if stats:
            # Create new snapshot
            ChannelStatsSnapshot.objects.create(
                channel=channel,
                timestamp=timezone.now(),
                subscribers_count=stats.get("member_count", 0),
                views_last_10_posts=stats.get("views_last_10_posts", 0),
                avg_views_per_post=stats.get("avg_views_per_post", 0),
                er_last_10_posts=stats.get("er", 0),
                err_last_10_posts=stats.get("err", 0),
                total_posts_count=stats.get("total_posts", 0),
                posts_last_24h=stats.get("posts_last_24h", 0),
                posts_last_7d=stats.get("posts_last_7d", 0),
                meta=stats,
            )

            # Update channel's member_count
            channel.member_count = stats.get("member_count", channel.member_count)
            channel.last_synced_at = timezone.now()
            channel.save(update_fields=["member_count", "last_synced_at", "updated_at"])

            logger.info(f"Synced stats for channel {channel_id}")

    except Exception as e:
        logger.exception(f"Failed to sync stats for channel {channel_id}: {e}")
        raise self.retry(exc=e)


@shared_task
def sync_all_channel_stats():
    """
    Sync statistics for all active channels.
    This is typically run as a periodic task.
    """
    channels = Channel.objects.filter(is_active=True, bot_can_read=True)
    count = 0

    for channel in channels:
        sync_channel_stats.delay(channel.pk)
        count += 1

    logger.info(f"Scheduled stats sync for {count} channels")


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def sync_post_stats(self, channel_post_id: int):
    """
    Sync statistics for a single published post.
    """
    from apps.posts.models import ChannelPost, ChannelPostStatus

    try:
        post = ChannelPost.objects.select_related("channel").get(pk=channel_post_id)
    except ChannelPost.DoesNotExist:
        logger.error(f"ChannelPost {channel_post_id} not found")
        return

    if post.status != ChannelPostStatus.PUBLISHED or not post.telegram_message_id:
        logger.warning(f"Post {channel_post_id} is not published or has no message ID")
        return

    try:
        from apps.integrations.telegram_bot.client import TelegramBotClient
        from .models import PostStats

        client = TelegramBotClient()
        stats = client.get_message_stats_sync(
            chat_id=post.channel.telegram_chat_id,
            message_id=post.telegram_message_id,
        )

        if stats:
            # Get current subscriber count for ER calculation
            latest_channel_stats = ChannelStatsSnapshot.get_latest_for_channel(
                post.channel
            )
            subscribers = (
                latest_channel_stats.subscribers_count
                if latest_channel_stats
                else post.channel.member_count
            )

            # Create new stats snapshot
            post_stats = PostStats.objects.create(
                channel_post=post,
                timestamp=timezone.now(),
                views=stats.get("views", 0),
                forwards=stats.get("forwards", 0),
                reactions_count=stats.get("reactions_count", 0),
                reactions_breakdown=stats.get("reactions", {}),
                comments_count=stats.get("comments", 0),
                meta=stats,
            )

            # Calculate engagement
            post_stats.calculate_engagement(subscribers)

            logger.info(f"Synced stats for post {channel_post_id}")

    except Exception as e:
        logger.exception(f"Failed to sync stats for post {channel_post_id}: {e}")
        raise self.retry(exc=e)


@shared_task
def sync_recent_post_stats():
    """
    Sync statistics for recently published posts.
    This is typically run as a periodic task (every 10-15 minutes).
    """
    from apps.posts.models import ChannelPost, ChannelPostStatus

    # Sync posts from last 7 days
    cutoff = timezone.now() - timedelta(days=7)
    posts = ChannelPost.objects.filter(
        status=ChannelPostStatus.PUBLISHED,
        published_at__gte=cutoff,
        telegram_message_id__isnull=False,
    ).exclude(telegram_message_id="")

    count = 0
    for post in posts:
        sync_post_stats.delay(post.pk)
        count += 1

    logger.info(f"Scheduled stats sync for {count} recent posts")


@shared_task
def calculate_global_stats():
    """
    Calculate and save global stats for all active groups.
    This is typically run as a periodic task (daily).
    """
    groups = ChannelGroup.objects.filter(is_active=True)
    count = 0

    for group in groups:
        try:
            GlobalStatsSnapshot.calculate_for_group(group)
            count += 1
        except Exception as e:
            logger.exception(f"Failed to calculate global stats for group {group.pk}: {e}")

    logger.info(f"Calculated global stats for {count} groups")


@shared_task
def calculate_daily_stats(target_date: str = None):
    """
    Calculate daily stats for all channels.
    This is typically run as a periodic task (daily, for previous day).

    Args:
        target_date: Date string in YYYY-MM-DD format. Defaults to yesterday.
    """
    if target_date:
        from datetime import datetime

        stats_date = datetime.strptime(target_date, "%Y-%m-%d").date()
    else:
        stats_date = date.today() - timedelta(days=1)

    channels = Channel.objects.filter(is_active=True)
    count = 0
    errors = 0

    for channel in channels:
        try:
            DailyChannelStats.compute_for_channel(channel, stats_date)
            count += 1
        except Exception as e:
            logger.exception(
                f"Failed to calculate daily stats for channel {channel.pk}: {e}"
            )
            errors += 1

    logger.info(
        f"Calculated daily stats for {count} channels on {stats_date} "
        f"({errors} errors)"
    )


@shared_task
def cleanup_old_stats(days_to_keep: int = 90):
    """
    Clean up old statistics snapshots to prevent database bloat.
    Keeps daily aggregates but removes hourly snapshots older than specified days.
    """
    from apps.posts.models import PostStats as PostStatsModel

    cutoff = timezone.now() - timedelta(days=days_to_keep)

    # Delete old channel snapshots (keep one per day)
    deleted_channel = ChannelStatsSnapshot.objects.filter(
        timestamp__lt=cutoff
    ).delete()

    # Delete old post stats
    deleted_posts = PostStatsModel.objects.filter(
        timestamp__lt=cutoff
    ).delete()

    logger.info(
        f"Cleaned up old stats: {deleted_channel[0]} channel snapshots, "
        f"{deleted_posts[0]} post stats"
    )

