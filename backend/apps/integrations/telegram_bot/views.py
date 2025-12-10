"""Telegram Bot webhook views for receiving updates from bot service.

Handles webhook callbacks from Telegram Bot Gateway:
- Bot events (added/removed from channels)
- Channel stats updates
- Message stats updates
- Channel info updates
"""

import logging

from django.conf import settings
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .schemas import (
    BotEventPayload,
    ChannelStatsWebhook,
    ChannelUpdateWebhook,
    MessageStatsWebhook,
)

logger = logging.getLogger(__name__)


def verify_bot_token(request) -> bool:
    """
    Verify the bot service token from the request.
    
    Checks both standard Authorization header and X-Bot-Token header
    (used by bot-events webhook).
    """
    # Check Authorization header
    auth_header = request.headers.get("Authorization", "")
    if auth_header:
        expected_token = f"Bearer {settings.TELEGRAM_BOT_SERVICE_TOKEN}"
        if auth_header == expected_token:
            return True

    # Check X-Bot-Token header (used by bot-events)
    bot_token = request.headers.get("X-Bot-Token", "")
    if bot_token and bot_token == settings.TELEGRAM_BOT_SERVICE_TOKEN:
        return True

    return False


@api_view(["POST"])
@permission_classes([AllowAny])
def bot_events_webhook(request):
    """
    Receive bot events from the Telegram Bot Gateway.
    
    Events:
    - bot_added: Bot was added to a channel/group as admin
    - bot_removed: Bot was removed from a channel/group
    - bot_permissions_changed: Bot's permissions were changed
    
    Headers:
    - X-Bot-Token: Authentication token
    - X-Event-Type: Event type (bot_added, bot_removed, bot_permissions_changed)
    - X-Request-ID: Request ID for tracing
    """
    if not verify_bot_token(request):
        return Response(
            {"error": "Invalid token"}, status=status.HTTP_401_UNAUTHORIZED
        )

    try:
        payload = BotEventPayload(**request.data)
    except Exception as e:
        logger.error(f"Invalid bot event payload: {e}")
        return Response(
            {"error": "Invalid payload"}, status=status.HTTP_400_BAD_REQUEST
        )

    event_type = payload.event
    request_id = request.headers.get("X-Request-ID", "unknown")

    logger.info(
        f"Received bot event: {event_type} for chat {payload.chat_id} "
        f"(request_id={request_id})"
    )

    try:
        from apps.telegram_channels.models import Channel, Language

        if event_type == "bot_added":
            # Bot was added to a channel - create or update channel
            # Try to get default language
            default_language = Language.objects.filter(is_default=True).first()
            if not default_language:
                default_language = Language.objects.first()

            permissions = payload.permissions
            channel, created = Channel.objects.update_or_create(
                telegram_chat_id=str(payload.chat_id),
                defaults={
                    "title": payload.chat_title or f"Channel {payload.chat_id}",
                    "username": payload.chat_username or "",
                    "is_active": True,
                    "bot_admin": True,
                    "bot_can_post": permissions.can_post_messages if permissions else False,
                    "bot_can_edit": permissions.can_edit_messages if permissions else False,
                    "bot_can_delete": permissions.can_delete_messages if permissions else False,
                    "bot_can_read": True,  # If bot is admin, it can read
                    "last_synced_at": timezone.now(),
                },
            )

            # Set language if channel was created
            if created and default_language:
                channel.language = default_language
                channel.save(update_fields=["language"])

            action = "created" if created else "updated"
            logger.info(f"Channel {payload.chat_id} {action} (bot_added event)")

            return Response({
                "status": "ok",
                "action": action,
                "channel_id": channel.pk,
            })

        elif event_type == "bot_removed":
            # Bot was removed from a channel - deactivate it
            channel = Channel.objects.filter(
                telegram_chat_id=str(payload.chat_id)
            ).first()

            if channel:
                channel.is_active = False
                channel.bot_admin = False
                channel.bot_can_post = False
                channel.bot_can_edit = False
                channel.bot_can_delete = False
                channel.bot_can_read = False
                channel.last_synced_at = timezone.now()
                channel.save(update_fields=[
                    "is_active",
                    "bot_admin",
                    "bot_can_post",
                    "bot_can_edit",
                    "bot_can_delete",
                    "bot_can_read",
                    "last_synced_at",
                    "updated_at",
                ])
                logger.info(f"Channel {payload.chat_id} deactivated (bot_removed event)")

                return Response({
                    "status": "ok",
                    "action": "deactivated",
                    "channel_id": channel.pk,
                })
            else:
                logger.warning(f"Channel {payload.chat_id} not found for bot_removed event")
                return Response({
                    "status": "ok",
                    "action": "not_found",
                })

        elif event_type == "bot_permissions_changed":
            # Bot's permissions were changed - update channel
            channel = Channel.objects.filter(
                telegram_chat_id=str(payload.chat_id)
            ).first()

            if channel:
                permissions = payload.permissions
                if permissions:
                    channel.bot_can_post = permissions.can_post_messages
                    channel.bot_can_edit = permissions.can_edit_messages
                    channel.bot_can_delete = permissions.can_delete_messages
                    channel.bot_can_read = True
                    channel.last_synced_at = timezone.now()
                    channel.save(update_fields=[
                        "bot_can_post",
                        "bot_can_edit",
                        "bot_can_delete",
                        "bot_can_read",
                        "last_synced_at",
                        "updated_at",
                    ])
                logger.info(f"Channel {payload.chat_id} permissions updated")

                return Response({
                    "status": "ok",
                    "action": "permissions_updated",
                    "channel_id": channel.pk,
                })
            else:
                logger.warning(
                    f"Channel {payload.chat_id} not found for bot_permissions_changed event"
                )
                return Response({
                    "status": "ok",
                    "action": "not_found",
                })

        else:
            logger.warning(f"Unknown bot event type: {event_type}")
            return Response({
                "status": "ok",
                "action": "ignored",
                "reason": f"Unknown event type: {event_type}",
            })

    except Exception as e:
        logger.exception(f"Error processing bot event: {e}")
        return Response(
            {"error": "Internal error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


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
            telegram_chat_id=str(payload.chat_id)
        ).first()

        if not channel:
            logger.warning(f"Channel {payload.chat_id} not found")
            return Response(
                {"error": "Channel not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Create stats snapshot
        ChannelStatsSnapshot.objects.create(
            channel=channel,
            timestamp=timezone.now(),
            subscribers_count=payload.member_count,
            # Note: Telegram Bot API provides limited stats
            # ERR, ER, views etc. require MTProto API or Analytics API
            views_last_10_posts=0,
            avg_views_per_post=0,
            er_last_10_posts=0,
            err_last_10_posts=0,
            total_posts_count=0,
            posts_last_24h=0,
            posts_last_7d=0,
            meta={"source": "webhook", "raw": request.data},
        )

        # Update channel's member_count
        channel.member_count = payload.member_count
        if payload.title:
            channel.title = payload.title
        channel.last_synced_at = timezone.now()
        channel.save(update_fields=["member_count", "title", "last_synced_at", "updated_at"])

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
    
    Note: Telegram Bot API has limited message stats.
    Full stats (views, reactions, etc.) require MTProto API.
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
            channel__telegram_chat_id=str(payload.chat_id),
            telegram_message_id=str(payload.message_id),
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
            timestamp=timezone.now(),
            views=payload.views or 0,
            forwards=payload.forwards or 0,
            reactions_count=0,
            reactions_breakdown={},
            comments_count=0,
            meta={"source": "webhook", "raw": request.data},
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
        from apps.telegram_channels.models import Channel, Language

        # Try to get default language for new channels
        default_language = Language.objects.filter(is_default=True).first()
        if not default_language:
            default_language = Language.objects.first()

        defaults = {
            "last_synced_at": timezone.now(),
        }
        if payload.title:
            defaults["title"] = payload.title
        if payload.username is not None:
            defaults["username"] = payload.username or ""
        if payload.description is not None:
            defaults["description"] = payload.description or ""

        channel, created = Channel.objects.update_or_create(
            telegram_chat_id=str(payload.chat_id),
            defaults=defaults,
        )

        # Set language if channel was created
        if created and default_language:
            channel.language = default_language
            channel.save(update_fields=["language"])

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
