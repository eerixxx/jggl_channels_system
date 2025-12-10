"""Telegram Bot integration Celery tasks.

Tasks for syncing channel information and permissions with Telegram Bot Gateway.
"""

import logging

from celery import shared_task
from django.utils import timezone

from .client import TelegramBotClient, TelegramBotGatewayError

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
        client = TelegramBotClient()
        info = client.get_channel_info_sync(channel.telegram_chat_id)

        if info:
            # Update channel info
            channel.title = info.get("title", channel.title)
            channel.username = info.get("username", channel.username) or ""
            channel.description = info.get("description", channel.description) or ""
            channel.member_count = info.get("member_count", channel.member_count)
            
            # Handle photo URL from nested photo object
            photo = info.get("photo")
            if photo and isinstance(photo, dict):
                channel.photo_url = photo.get("big_file_url", "") or photo.get("small_file_url", "") or ""
            
            channel.invite_link = info.get("invite_link", channel.invite_link) or ""
            channel.last_synced_at = timezone.now()
            channel.meta = {**channel.meta, "raw_info": info.get("raw")}
            channel.save()

            logger.info(f"Synced info for channel {channel_id}")

    except TelegramBotGatewayError as e:
        logger.error(f"Gateway error syncing channel {channel_id}: {e.code} - {e.message}")
        if e.code in ("TELEGRAM_RATE_LIMIT", "TELEGRAM_UNAVAILABLE", "TIMEOUT"):
            raise self.retry(exc=e)
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
        client = TelegramBotClient()
        permissions = client.verify_bot_permissions_sync(channel.telegram_chat_id)

        if permissions:
            channel.bot_admin = permissions.get("is_admin", False)
            channel.bot_can_post = permissions.get("can_post_messages", False)
            channel.bot_can_edit = permissions.get("can_edit_messages", False)
            channel.bot_can_delete = permissions.get("can_delete_messages", False)
            channel.bot_can_read = permissions.get("is_member", False)  # If member, can read
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

    except TelegramBotGatewayError as e:
        logger.error(f"Gateway error verifying permissions for channel {channel_id}: {e.code} - {e.message}")
        if e.code in ("TELEGRAM_RATE_LIMIT", "TELEGRAM_UNAVAILABLE", "TIMEOUT"):
            raise self.retry(exc=e)
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


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_bot_updates(self):
    """
    Process pending bot updates from Telegram.
    
    This task processes updates about bot membership in channels/groups.
    When the bot is added or removed from a channel, this creates/updates
    the Channel record automatically.
    
    This is useful for:
    - Initial channel discovery
    - Automatic channel synchronization
    - Keeping channel list up-to-date
    
    The Bot Gateway automatically notifies about bot membership changes
    via webhooks, but this task can also be run periodically as a backup.
    """
    try:
        client = TelegramBotClient()
        result = client.process_updates_sync()

        if result:
            processed = result['processed']
            results = result['results']
            
            # Log summary
            logger.info(f"Processed {processed} bot updates")
            
            # Log details of each update
            for item in results:
                update_type = item.get('type', 'unknown')
                status = item.get('status', 'unknown')
                update_id = item.get('update_id')
                
                if status == 'processed':
                    logger.info(f"  Update #{update_id} ({update_type}): {status}")
                elif status == 'ignored':
                    logger.debug(f"  Update #{update_id} ({update_type}): {status}")
            
            return result
        else:
            logger.info("No bot updates to process")
            return None

    except TelegramBotGatewayError as e:
        logger.error(f"Gateway error processing updates: {e.code} - {e.message}")
        if e.code in ("TELEGRAM_RATE_LIMIT", "TELEGRAM_UNAVAILABLE", "TIMEOUT"):
            raise self.retry(exc=e)
    except Exception as e:
        logger.exception(f"Failed to process bot updates: {e}")
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def sync_bot_info(self):
    """
    Sync bot information.
    
    Logs bot details for debugging and monitoring.
    """
    try:
        client = TelegramBotClient()
        info = client.get_bot_info_sync()

        if info:
            logger.info(
                f"Bot info: @{info.get('username')} (ID: {info.get('bot_id')})"
            )
            return info
        return None

    except TelegramBotGatewayError as e:
        logger.error(f"Gateway error getting bot info: {e.code} - {e.message}")
        if e.code in ("TELEGRAM_RATE_LIMIT", "TELEGRAM_UNAVAILABLE", "TIMEOUT"):
            raise self.retry(exc=e)
    except Exception as e:
        logger.exception(f"Failed to get bot info: {e}")
        raise self.retry(exc=e)
