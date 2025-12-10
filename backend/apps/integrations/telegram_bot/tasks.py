"""Telegram Bot integration Celery tasks."""

import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def sync_channel_info(self, channel_id: int):
    """
    Sync channel information from the bot service.
    """
    from apps.telegram_channels.models import Channel

    try:
        channel = Channel.objects.get(pk=channel_id)
    except Channel.DoesNotExist:
        logger.error(f"Channel {channel_id} not found")
        return

    try:
        from .client import TelegramBotClient

        client = TelegramBotClient()
        info = client.get_channel_info_sync(channel.telegram_chat_id)

        if info:
            # Update channel info
            channel.title = info.get("title", channel.title)
            channel.username = info.get("username", channel.username) or ""
            channel.description = info.get("description", channel.description) or ""
            channel.member_count = info.get("member_count", channel.member_count)
            channel.photo_url = info.get("photo_url", channel.photo_url) or ""
            channel.invite_link = info.get("invite_link", channel.invite_link) or ""
            channel.last_synced_at = timezone.now()
            channel.meta = {**channel.meta, "raw_info": info.get("raw_response")}
            channel.save()

            logger.info(f"Synced info for channel {channel_id}")

    except Exception as e:
        logger.exception(f"Failed to sync channel {channel_id}: {e}")
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def verify_bot_permissions(self, channel_id: int):
    """
    Verify bot permissions in a channel.
    """
    from apps.telegram_channels.models import Channel

    try:
        channel = Channel.objects.get(pk=channel_id)
    except Channel.DoesNotExist:
        logger.error(f"Channel {channel_id} not found")
        return

    try:
        from .client import TelegramBotClient

        client = TelegramBotClient()
        permissions = client.verify_bot_permissions_sync(channel.telegram_chat_id)

        if permissions:
            channel.bot_admin = permissions.get("is_admin", False)
            channel.bot_can_post = permissions.get("can_post_messages", False)
            channel.bot_can_edit = permissions.get("can_edit_messages", False)
            channel.bot_can_delete = permissions.get("can_delete_messages", False)
            channel.bot_can_read = permissions.get("can_read_messages", False)
            channel.last_synced_at = timezone.now()
            channel.save(
                update_fields=[
                    "bot_admin",
                    "bot_can_post",
                    "bot_can_edit",
                    "bot_can_delete",
                    "bot_can_read",
                    "last_synced_at",
                    "updated_at",
                ]
            )

            logger.info(
                f"Verified permissions for channel {channel_id}: "
                f"admin={channel.bot_admin}, can_post={channel.bot_can_post}"
            )

    except Exception as e:
        logger.exception(f"Failed to verify permissions for channel {channel_id}: {e}")
        raise self.retry(exc=e)


@shared_task
def sync_all_channels():
    """
    Sync info for all active channels.
    """
    from apps.telegram_channels.models import Channel

    channels = Channel.objects.filter(is_active=True)
    count = 0

    for channel in channels:
        sync_channel_info.delay(channel.pk)
        count += 1

    logger.info(f"Scheduled sync for {count} channels")


@shared_task
def verify_all_channel_permissions():
    """
    Verify bot permissions for all active channels.
    """
    from apps.telegram_channels.models import Channel

    channels = Channel.objects.filter(is_active=True)
    count = 0

    for channel in channels:
        verify_bot_permissions.delay(channel.pk)
        count += 1

    logger.info(f"Scheduled permission verification for {count} channels")

