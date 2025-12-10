"""Telegram Bot webhook views for receiving updates from bot service."""

import logging

from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .schemas import (
    ChannelStatsWebhook,
    ChannelUpdateWebhook,
    MessageStatsWebhook,
)

logger = logging.getLogger(__name__)


def verify_bot_token(request) -> bool:
    """
    Verify the bot service token from the request.
    """
    from django.conf import settings

    auth_header = request.headers.get("Authorization", "")
    expected_token = f"Bearer {settings.TELEGRAM_BOT_SERVICE_TOKEN}"
    return auth_header == expected_token


@api_view(["POST"])
@permission_classes([AllowAny])
def channel_stats_webhook(request):
    """
    Receive channel statistics updates from the bot service.
    """
    if not verify_bot_token(request):
        return Response(
            {"error": "Invalid token"}, status=status.HTTP_401_UNAUTHORIZED
        )

    try:
        payload = ChannelStatsWebhook(**request.data)
    except Exception as e:
        logger.error(f"Invalid channel stats payload: {e}")
        return Response(
            {"error": "Invalid payload"}, status=status.HTTP_400_BAD_REQUEST
        )

    try:
        from apps.telegram_channels.models import Channel
        from apps.stats.models import ChannelStatsSnapshot

        channel = Channel.objects.filter(
            telegram_chat_id=payload.chat_id
        ).first()

        if not channel:
            logger.warning(f"Channel {payload.chat_id} not found")
            return Response(
                {"error": "Channel not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Create stats snapshot
        ChannelStatsSnapshot.objects.create(
            channel=channel,
            timestamp=payload.timestamp,
            subscribers_count=payload.member_count,
            views_last_10_posts=payload.views_last_10_posts,
            avg_views_per_post=payload.avg_views_per_post,
            er_last_10_posts=payload.er,
            err_last_10_posts=payload.err,
            total_posts_count=payload.total_posts,
            posts_last_24h=payload.posts_last_24h,
            posts_last_7d=payload.posts_last_7d,
            meta=payload.extra,
        )

        # Update channel's member_count
        channel.member_count = payload.member_count
        channel.last_synced_at = timezone.now()
        channel.save(update_fields=["member_count", "last_synced_at", "updated_at"])

        logger.info(f"Received stats for channel {payload.chat_id}")
        return Response({"status": "ok"})

    except Exception as e:
        logger.exception(f"Error processing channel stats: {e}")
        return Response(
            {"error": "Internal error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["POST"])
@permission_classes([AllowAny])
def message_stats_webhook(request):
    """
    Receive message statistics updates from the bot service.
    """
    if not verify_bot_token(request):
        return Response(
            {"error": "Invalid token"}, status=status.HTTP_401_UNAUTHORIZED
        )

    try:
        payload = MessageStatsWebhook(**request.data)
    except Exception as e:
        logger.error(f"Invalid message stats payload: {e}")
        return Response(
            {"error": "Invalid payload"}, status=status.HTTP_400_BAD_REQUEST
        )

    try:
        from apps.posts.models import ChannelPost
        from apps.stats.models import ChannelStatsSnapshot, PostStats

        post = ChannelPost.objects.filter(
            channel__telegram_chat_id=payload.chat_id,
            telegram_message_id=payload.message_id,
        ).select_related("channel").first()

        if not post:
            logger.warning(
                f"Post not found: chat={payload.chat_id}, msg={payload.message_id}"
            )
            return Response(
                {"error": "Post not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Get subscriber count for ER calculation
        latest_stats = ChannelStatsSnapshot.get_latest_for_channel(post.channel)
        subscribers = (
            latest_stats.subscribers_count
            if latest_stats
            else post.channel.member_count
        )

        # Create post stats
        post_stats = PostStats.objects.create(
            channel_post=post,
            timestamp=payload.timestamp,
            views=payload.views,
            forwards=payload.forwards,
            reactions_count=payload.reactions_count,
            reactions_breakdown=payload.reactions,
            comments_count=payload.comments,
            meta=payload.extra,
        )

        # Calculate engagement metrics
        post_stats.calculate_engagement(subscribers)

        logger.info(f"Received stats for message {payload.message_id}")
        return Response({"status": "ok"})

    except Exception as e:
        logger.exception(f"Error processing message stats: {e}")
        return Response(
            {"error": "Internal error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["POST"])
@permission_classes([AllowAny])
def channel_update_webhook(request):
    """
    Receive channel information updates from the bot service.
    """
    if not verify_bot_token(request):
        return Response(
            {"error": "Invalid token"}, status=status.HTTP_401_UNAUTHORIZED
        )

    try:
        payload = ChannelUpdateWebhook(**request.data)
    except Exception as e:
        logger.error(f"Invalid channel update payload: {e}")
        return Response(
            {"error": "Invalid payload"}, status=status.HTTP_400_BAD_REQUEST
        )

    try:
        from apps.telegram_channels.models import Channel

        channel, created = Channel.objects.update_or_create(
            telegram_chat_id=payload.chat_id,
            defaults={
                "title": payload.title,
                "username": payload.username or "",
                "description": payload.description or "",
                "member_count": payload.member_count,
                "photo_url": payload.photo_url or "",
                "invite_link": payload.invite_link or "",
                "bot_admin": payload.is_admin,
                "bot_can_post": payload.can_post_messages,
                "bot_can_edit": payload.can_edit_messages,
                "bot_can_delete": payload.can_delete_messages,
                "last_synced_at": timezone.now(),
            },
        )

        action = "created" if created else "updated"
        logger.info(f"Channel {payload.chat_id} {action}")

        return Response({
            "status": "ok",
            "action": action,
            "channel_id": channel.pk,
        })

    except Exception as e:
        logger.exception(f"Error processing channel update: {e}")
        return Response(
            {"error": "Internal error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

