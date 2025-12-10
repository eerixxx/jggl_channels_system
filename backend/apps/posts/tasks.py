"""Posts Celery tasks.

Tasks for publishing posts to Telegram channels via Bot Gateway
and requesting translations from LLM Translation Middleware.
"""

import logging

from celery import shared_task

from .models import ChannelPost, ChannelPostStatus, MultiChannelPost

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def request_translations(self, multi_post_id: int):
    """
    Request translations for all non-primary channel posts.
    """
    try:
        multi_post = MultiChannelPost.objects.get(pk=multi_post_id)
    except MultiChannelPost.DoesNotExist:
        logger.error(f"MultiChannelPost {multi_post_id} not found")
        return

    # Get all posts that need translation
    posts_to_translate = multi_post.channel_posts.filter(
        source_type="auto_translated",
        status=ChannelPostStatus.PENDING_TRANSLATION,
    ).exclude(language=multi_post.primary_channel.language)

    for post in posts_to_translate:
        translate_channel_post.delay(post.pk)

    logger.info(
        f"Scheduled translation for {posts_to_translate.count()} posts "
        f"of MultiChannelPost {multi_post_id}"
    )


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def translate_channel_post(self, channel_post_id: int):
    """
    Translate a single channel post using the LLM translation service.
    """
    from django.conf import settings
    
    try:
        post = ChannelPost.objects.select_related(
            "multi_post", "multi_post__primary_channel__language", "language", "channel"
        ).get(pk=channel_post_id)
    except ChannelPost.DoesNotExist:
        logger.error(f"ChannelPost {channel_post_id} not found")
        return

    if post.source_type == "primary":
        logger.warning(f"Cannot translate primary post {channel_post_id}")
        return

    # Get source text and languages
    source_text = post.multi_post.primary_text_markdown
    source_language = post.multi_post.primary_channel.language
    target_language = post.language

    if not source_text:
        post.error_message = "No source text to translate"
        post.status = ChannelPostStatus.DRAFT
        post.save(update_fields=["status", "error_message", "updated_at"])
        return

    if not source_language:
        post.error_message = "Source channel has no language set"
        post.status = ChannelPostStatus.DRAFT
        post.save(update_fields=["status", "error_message", "updated_at"])
        return

    if not target_language:
        post.error_message = "Target channel has no language set"
        post.status = ChannelPostStatus.DRAFT
        post.save(update_fields=["status", "error_message", "updated_at"])
        return

    # Skip if same language
    if source_language.code == target_language.code:
        post.text_markdown = source_text
        post.status = ChannelPostStatus.DRAFT
        post.save(update_fields=["text_markdown", "status", "updated_at"])
        post.convert_to_telegram_html()
        return

    try:
        from apps.integrations.translation.client import TranslationClient, TranslationError

        client = TranslationClient()
        
        logger.info(
            f"Translating ChannelPost {channel_post_id}: "
            f"{source_language.code} -> {target_language.code}"
        )

        translation = client.translate_sync(
            text=source_text,
            source_language=source_language.code,
            target_language=target_language.code,
            context=getattr(settings, 'TRANSLATION_CONTEXT', 'news channel'),
            tone=getattr(settings, 'TRANSLATION_TONE', 'professional'),
            preserve_formatting=True,
        )

        from django.utils import timezone

        post.text_markdown = translation
        post.translation_requested = True
        post.translation_received_at = timezone.now()
        post.status = ChannelPostStatus.DRAFT
        post.error_message = ""
        post.save(
            update_fields=[
                "text_markdown",
                "translation_requested",
                "translation_received_at",
                "status",
                "error_message",
                "updated_at",
            ]
        )

        # Convert to HTML
        post.convert_to_telegram_html()

        logger.info(
            f"Successfully translated ChannelPost {channel_post_id} "
            f"to {target_language.code}"
        )

    except TranslationError as e:
        error_msg = f"[{e.code}] {e.message}"
        logger.error(f"Translation error for ChannelPost {channel_post_id}: {error_msg}")
        
        # Retry on transient errors
        if e.code in ("LLM_RATE_LIMIT", "LLM_UNAVAILABLE", "LLM_TIMEOUT"):
            post.error_message = f"Retrying: {error_msg}"
            post.save(update_fields=["error_message", "updated_at"])
            raise self.retry(exc=e, countdown=60)
        
        # Mark as draft with error for other errors
        post.status = ChannelPostStatus.DRAFT
        post.error_message = error_msg
        post.save(update_fields=["status", "error_message", "updated_at"])

    except Exception as e:
        logger.exception(f"Failed to translate ChannelPost {channel_post_id}: {e}")
        post.error_message = f"Translation failed: {str(e)}"
        post.save(update_fields=["error_message", "updated_at"])
        raise self.retry(exc=e, countdown=30)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def publish_multi_post(self, multi_post_id: int):
    """
    Publish all channel posts for a MultiChannelPost.
    """
    try:
        multi_post = MultiChannelPost.objects.get(pk=multi_post_id)
    except MultiChannelPost.DoesNotExist:
        logger.error(f"MultiChannelPost {multi_post_id} not found")
        return

    # Convert all posts to HTML first
    for post in multi_post.channel_posts.all():
        if post.text_markdown and not post.text_telegram_html:
            post.convert_to_telegram_html()

    # Queue publishing for each channel post
    posts_to_publish = multi_post.channel_posts.filter(
        channel__is_active=True,
        channel__bot_can_post=True,
    ).exclude(status=ChannelPostStatus.PUBLISHED)

    for post in posts_to_publish:
        publish_channel_post.delay(post.pk)

    multi_post.status = "publishing"
    multi_post.save(update_fields=["status", "updated_at"])

    logger.info(
        f"Scheduled publishing for {posts_to_publish.count()} posts "
        f"of MultiChannelPost {multi_post_id}"
    )


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def publish_ready_channel_posts(self, multi_post_id: int):
    """
    Publish only ready channel posts for a MultiChannelPost.
    """
    try:
        multi_post = MultiChannelPost.objects.get(pk=multi_post_id)
    except MultiChannelPost.DoesNotExist:
        logger.error(f"MultiChannelPost {multi_post_id} not found")
        return

    # Queue publishing for ready channel posts only
    posts_to_publish = multi_post.channel_posts.filter(
        channel__is_active=True,
        channel__bot_can_post=True,
        status__in=[ChannelPostStatus.DRAFT, ChannelPostStatus.PENDING_PUBLISH],
    ).exclude(text_markdown="")

    for post in posts_to_publish:
        # Ensure HTML is generated
        if not post.text_telegram_html:
            post.convert_to_telegram_html()
        publish_channel_post.delay(post.pk)

    logger.info(
        f"Scheduled publishing for {posts_to_publish.count()} ready posts "
        f"of MultiChannelPost {multi_post_id}"
    )


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def publish_channel_post(self, channel_post_id: int):
    """
    Publish a single channel post to Telegram via Bot Gateway.
    """
    try:
        post = ChannelPost.objects.select_related("channel", "multi_post").get(
            pk=channel_post_id
        )
    except ChannelPost.DoesNotExist:
        logger.error(f"ChannelPost {channel_post_id} not found")
        return

    if not post.channel.bot_can_post:
        logger.warning(f"Bot cannot post to channel {post.channel}")
        post.mark_failed("Bot does not have posting permissions")
        return

    # Ensure we have HTML text
    if not post.text_telegram_html:
        if post.text_markdown:
            post.convert_to_telegram_html()
        else:
            post.mark_failed("No content to publish")
            return

    post.status = ChannelPostStatus.PUBLISHING
    post.save(update_fields=["status", "updated_at"])

    try:
        from apps.integrations.telegram_bot.client import (
            TelegramBotClient,
            TelegramBotGatewayError,
        )

        client = TelegramBotClient()

        # Get photo URL if available
        photo_url = None
        if post.photo:
            from django.conf import settings
            # Build full URL for the photo - Telegram needs absolute URL
            relative_url = post.photo.url
            if relative_url.startswith('http'):
                photo_url = relative_url
            else:
                # Prepend SITE_URL to relative path
                site_url = getattr(settings, 'SITE_URL', '').rstrip('/')
                if site_url:
                    photo_url = f"{site_url}{relative_url}"
                else:
                    # No SITE_URL configured, skip photo
                    logger.warning(
                        f"Cannot send photo for post {channel_post_id}: "
                        "SITE_URL not configured"
                    )

        # Generate idempotency key to prevent duplicate posts
        idempotency_key = f"post-{post.pk}-{post.updated_at.isoformat()}"

        result = client.send_message_sync(
            chat_id=post.channel.telegram_chat_id,
            text=post.text_telegram_html,
            parse_mode="HTML",
            photo_url=photo_url,
            disable_web_page_preview=post.multi_post.disable_web_page_preview,
            disable_notification=post.multi_post.disable_notification,
            idempotency_key=idempotency_key,
        )

        if result and result.get("message_id"):
            post.mark_published(str(result["message_id"]))
            logger.info(
                f"Successfully published ChannelPost {channel_post_id} "
                f"to {post.channel} (message_id={result['message_id']})"
            )
        else:
            post.mark_failed("No message ID received from Telegram")
            logger.error(f"Failed to publish ChannelPost {channel_post_id}: no message_id")

    except TelegramBotGatewayError as e:
        error_msg = f"[{e.code}] {e.message}"
        logger.error(f"Gateway error publishing ChannelPost {channel_post_id}: {error_msg}")
        
        # Retry on transient errors
        if e.code in ("TELEGRAM_RATE_LIMIT", "TELEGRAM_UNAVAILABLE", "TIMEOUT"):
            post.status = ChannelPostStatus.PENDING_PUBLISH
            post.error_message = f"Retrying: {error_msg}"
            post.save(update_fields=["status", "error_message", "updated_at"])
            raise self.retry(exc=e)
        else:
            post.mark_failed(error_msg)
            
    except Exception as e:
        logger.exception(f"Failed to publish ChannelPost {channel_post_id}: {e}")
        post.mark_failed(str(e))
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def edit_channel_post(self, channel_post_id: int):
    """
    Edit an already published channel post in Telegram.
    """
    try:
        post = ChannelPost.objects.select_related("channel", "multi_post").get(
            pk=channel_post_id
        )
    except ChannelPost.DoesNotExist:
        logger.error(f"ChannelPost {channel_post_id} not found")
        return

    if not post.telegram_message_id:
        logger.warning(f"ChannelPost {channel_post_id} has no telegram_message_id")
        return

    if not post.channel.bot_can_edit:
        logger.warning(f"Bot cannot edit messages in channel {post.channel}")
        return

    # Ensure we have HTML text
    if not post.text_telegram_html:
        if post.text_markdown:
            post.convert_to_telegram_html()
        else:
            logger.error(f"No content to update for ChannelPost {channel_post_id}")
            return

    try:
        from apps.integrations.telegram_bot.client import (
            TelegramBotClient,
            TelegramBotGatewayError,
        )

        client = TelegramBotClient()

        success = client.edit_message_sync(
            chat_id=post.channel.telegram_chat_id,
            message_id=int(post.telegram_message_id),
            text=post.text_telegram_html,
            parse_mode="HTML",
            disable_web_page_preview=post.multi_post.disable_web_page_preview,
        )

        if success:
            logger.info(f"Successfully edited ChannelPost {channel_post_id}")
        else:
            logger.warning(f"Failed to edit ChannelPost {channel_post_id}")

    except TelegramBotGatewayError as e:
        logger.error(f"Gateway error editing ChannelPost {channel_post_id}: {e.code} - {e.message}")
        if e.code in ("TELEGRAM_RATE_LIMIT", "TELEGRAM_UNAVAILABLE", "TIMEOUT"):
            raise self.retry(exc=e)
    except Exception as e:
        logger.exception(f"Failed to edit ChannelPost {channel_post_id}: {e}")
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def delete_channel_post(self, channel_post_id: int):
    """
    Delete a published channel post from Telegram.
    """
    try:
        post = ChannelPost.objects.select_related("channel").get(
            pk=channel_post_id
        )
    except ChannelPost.DoesNotExist:
        logger.error(f"ChannelPost {channel_post_id} not found")
        return

    if not post.telegram_message_id:
        logger.warning(f"ChannelPost {channel_post_id} has no telegram_message_id")
        return

    if not post.channel.bot_can_delete:
        logger.warning(f"Bot cannot delete messages in channel {post.channel}")
        return

    try:
        from apps.integrations.telegram_bot.client import (
            TelegramBotClient,
            TelegramBotGatewayError,
        )

        client = TelegramBotClient()

        success = client.delete_message_sync(
            chat_id=post.channel.telegram_chat_id,
            message_id=int(post.telegram_message_id),
        )

        if success:
            post.telegram_message_id = ""
            post.status = ChannelPostStatus.DRAFT
            post.published_at = None
            post.save(update_fields=[
                "telegram_message_id",
                "status",
                "published_at",
                "updated_at",
            ])
            logger.info(f"Successfully deleted ChannelPost {channel_post_id} from Telegram")
        else:
            logger.warning(f"Failed to delete ChannelPost {channel_post_id}")

    except TelegramBotGatewayError as e:
        logger.error(f"Gateway error deleting ChannelPost {channel_post_id}: {e.code} - {e.message}")
        if e.code in ("TELEGRAM_RATE_LIMIT", "TELEGRAM_UNAVAILABLE", "TIMEOUT"):
            raise self.retry(exc=e)
    except Exception as e:
        logger.exception(f"Failed to delete ChannelPost {channel_post_id}: {e}")
        raise self.retry(exc=e)
