"""Stats Celery tasks.

Tasks for syncing channel and post statistics from Telegram Bot Gateway.

Note: Telegram Bot API provides limited statistics:
- Member count only for channels
- No detailed message stats (views, reactions, etc.)
For full stats, consider using MTProto API or Telegram Analytics API.
"""

import logging
from datetime import date, timedelta

from celery import shared_task
from django.utils import timezone

from apps.telegram_channels.models import Channel, ChannelGroup
from apps.integrations.telegram_bot.client import TelegramBotClient, TelegramBotGatewayError

from .models import (
    ChannelStatsSnapshot,
    DailyChannelStats,
    GlobalStatsSnapshot,
)

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def sync_channel_stats(self, channel_id: int, use_mtproto: bool = True):
    """
    Sync statistics for a single channel from the bot service.
    
    Args:
        channel_id: Channel database ID
        use_mtproto: Try to use MTProto API for detailed stats (default: True)
    
    If use_mtproto=True and MTProto is available, gets detailed stats.
    Otherwise falls back to Bot API (member count only).
    """
    try:
        channel = Channel.objects.get(pk=channel_id)
    except Channel.DoesNotExist:
        logger.error(f"Channel {channel_id} not found")
        return

    try:
        from django.conf import settings
        client = TelegramBotClient()
        
        # Check if MTProto is available and try to use it
        mtproto_used = False
        if use_mtproto:
            try:
                status = client.get_mtproto_status_sync()
                if status and status.get("enabled") and status.get("connected"):
                    # Use MTProto for detailed stats
                    detailed_stats = client.get_detailed_channel_stats_sync(channel.telegram_chat_id)
                    
                    if detailed_stats:
                        channel_info = detailed_stats.get("channel", {})
                        growth_stats = detailed_stats.get("growth_stats", {})
                        
                        # Calculate ER/ERR from recent posts
                        recent_posts = client.get_recent_posts_stats_sync(
                            channel.telegram_chat_id,
                            limit=10,
                        )
                        
                        if recent_posts:
                            totals = recent_posts.get("totals", {})
                            average = recent_posts.get("average", {})
                            posts_count = recent_posts.get("count", 0)
                            
                            # Calculate engagement metrics
                            subscribers = channel_info.get("participants_count", 0)
                            total_views = totals.get("views", 0)
                            total_reactions = totals.get("reactions", 0)
                            total_replies = totals.get("replies", 0)
                            total_forwards = totals.get("forwards", 0)
                            
                            er = 0.0
                            err = 0.0
                            if subscribers > 0:
                                engagement = total_reactions + total_replies + total_forwards
                                er = round((engagement / subscribers) * 100, 2)
                            if total_views > 0:
                                interaction = total_reactions + total_replies
                                err = round((interaction / total_views) * 100, 2)
                            
                            # Create snapshot with detailed data
                            ChannelStatsSnapshot.objects.create(
                                channel=channel,
                                timestamp=timezone.now(),
                                subscribers_count=subscribers,
                                views_last_10_posts=total_views,
                                avg_views_per_post=average.get("views", 0),
                                er_last_10_posts=er,
                                err_last_10_posts=err,
                                total_posts_count=channel_info.get("participants_count", 0),
                                posts_last_24h=0,  # Not provided by this endpoint
                                posts_last_7d=0,   # Not provided by this endpoint
                                meta={
                                    "source": "mtproto",
                                    "channel_info": channel_info,
                                    "growth_stats": growth_stats,
                                    "recent_posts": recent_posts,
                                },
                            )
                            
                            # Update channel
                            channel.member_count = subscribers
                            channel.title = channel_info.get("title", channel.title)
                            channel.last_synced_at = timezone.now()
                            channel.save(update_fields=["member_count", "title", "last_synced_at", "updated_at"])
                            
                            mtproto_used = True
                            logger.info(
                                f"Synced detailed stats for channel {channel_id} via MTProto: "
                                f"{subscribers} members, ER={er}%, ERR={err}%"
                            )
            except Exception as mtproto_error:
                logger.warning(f"MTProto stats failed, falling back to Bot API: {mtproto_error}")

        # Fallback to Bot API if MTProto not used or failed
        if not mtproto_used:
            stats = client.get_channel_stats_sync(channel.telegram_chat_id)

            if stats:
                # Create new snapshot with limited data
                ChannelStatsSnapshot.objects.create(
                    channel=channel,
                    timestamp=timezone.now(),
                    subscribers_count=stats.get("member_count", 0),
                    views_last_10_posts=0,  # Not available via Bot API
                    avg_views_per_post=0,   # Not available via Bot API
                    er_last_10_posts=0,     # Not available via Bot API
                    err_last_10_posts=0,    # Not available via Bot API
                    total_posts_count=0,    # Not available via Bot API
                    posts_last_24h=0,       # Not available via Bot API
                    posts_last_7d=0,        # Not available via Bot API
                    meta={
                        "source": "bot_api",
                        "raw": stats.get("raw"),
                        "note": "Detailed stats not available via Telegram Bot API",
                    },
                )

                # Update channel's member_count
                channel.member_count = stats.get("member_count", channel.member_count)
                if stats.get("title"):
                    channel.title = stats["title"]
                channel.last_synced_at = timezone.now()
                channel.save(update_fields=["member_count", "title", "last_synced_at", "updated_at"])

                logger.info(f"Synced stats for channel {channel_id} via Bot API: {stats.get('member_count')} members")

    except TelegramBotGatewayError as e:
        logger.error(f"Gateway error syncing stats for channel {channel_id}: {e.code} - {e.message}")
        if e.code in ("TELEGRAM_RATE_LIMIT", "TELEGRAM_UNAVAILABLE", "TIMEOUT"):
            raise self.retry(exc=e)
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
def sync_post_stats(self, channel_post_id: int, use_mtproto: bool = True):
    """
    Sync statistics for a single published post.
    
    Args:
        channel_post_id: ChannelPost database ID
        use_mtproto: Try to use MTProto API for detailed stats (default: True)
    
    If use_mtproto=True and MTProto is available, gets exact views, reactions, etc.
    Otherwise falls back to Bot API (very limited data).
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
        from .models import PostStats

        client = TelegramBotClient()
        
        # Get current subscriber count for ER calculation
        latest_channel_stats = ChannelStatsSnapshot.get_latest_for_channel(
            post.channel
        )
        subscribers = (
            latest_channel_stats.subscribers_count
            if latest_channel_stats
            else post.channel.member_count
        )
        
        # Try MTProto first if enabled
        mtproto_used = False
        if use_mtproto:
            try:
                status = client.get_mtproto_status_sync()
                if status and status.get("enabled") and status.get("connected"):
                    # Use MTProto for detailed stats
                    detailed_stats = client.get_detailed_message_stats_sync(
                        chat_id=post.channel.telegram_chat_id,
                        message_id=int(post.telegram_message_id),
                    )
                    
                    if detailed_stats:
                        reactions_data = detailed_stats.get("reactions", {})
                        reactions_list = reactions_data.get("reactions", []) if reactions_data else []
                        reactions_breakdown = {
                            r.get("emoji"): r.get("count", 0) 
                            for r in reactions_list
                        } if reactions_list else {}
                        
                        # Create detailed stats snapshot
                        post_stats = PostStats.objects.create(
                            channel_post=post,
                            timestamp=timezone.now(),
                            views=detailed_stats.get("views") or 0,
                            forwards=detailed_stats.get("forwards") or 0,
                            reactions_count=reactions_data.get("total_count", 0) if reactions_data else 0,
                            reactions_breakdown=reactions_breakdown,
                            comments_count=detailed_stats.get("replies") or 0,
                            meta={
                                "source": "mtproto",
                                "date": str(detailed_stats.get("date")) if detailed_stats.get("date") else None,
                                "pinned": detailed_stats.get("pinned", False),
                            },
                        )
                        
                        # Calculate engagement
                        post_stats.calculate_engagement(subscribers)
                        
                        mtproto_used = True
                        logger.info(
                            f"Synced detailed stats for post {channel_post_id} via MTProto: "
                            f"{post_stats.views} views, {post_stats.reactions_count} reactions"
                        )
            except Exception as mtproto_error:
                logger.warning(f"MTProto stats failed for post {channel_post_id}, falling back to Bot API: {mtproto_error}")

        # Fallback to Bot API if MTProto not used or failed
        if not mtproto_used:
            stats = client.get_message_stats_sync(
                chat_id=post.channel.telegram_chat_id,
                message_id=int(post.telegram_message_id),
            )

            if stats:
                # Create new stats snapshot with limited data
                post_stats = PostStats.objects.create(
                    channel_post=post,
                    timestamp=timezone.now(),
                    views=stats.get("views") or 0,
                    forwards=stats.get("forwards") or 0,
                    reactions_count=0,  # Not available via Bot API
                    reactions_breakdown=stats.get("reactions") or {},
                    comments_count=stats.get("reply_count") or 0,
                    meta={
                        "source": "bot_api",
                        "raw": stats.get("raw"),
                        "note": "Detailed stats not available via Telegram Bot API",
                    },
                )

                # Calculate engagement (will be minimal with no data)
                post_stats.calculate_engagement(subscribers)

                logger.info(f"Synced stats for post {channel_post_id} via Bot API (limited data)")

    except TelegramBotGatewayError as e:
        logger.error(f"Gateway error syncing stats for post {channel_post_id}: {e.code} - {e.message}")
        if e.code in ("TELEGRAM_RATE_LIMIT", "TELEGRAM_UNAVAILABLE", "TIMEOUT"):
            raise self.retry(exc=e)
    except Exception as e:
        logger.exception(f"Failed to sync stats for post {channel_post_id}: {e}")
        raise self.retry(exc=e)


@shared_task
def sync_recent_post_stats():
    """
    Sync statistics for recently published posts.
    This is typically run as a periodic task (every 10-15 minutes).
    
    Note: Stats will be limited due to Bot API restrictions.
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
    from .models import PostStats as PostStatsModel

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
