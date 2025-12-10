"""Posts Celery tasks."""

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
    try:
        post = ChannelPost.objects.select_related(
            "multi_post", "language", "channel"
        ).get(pk=channel_post_id)
    except ChannelPost.DoesNotExist:
        logger.error(f"ChannelPost {channel_post_id} not found")
        return

    if post.source_type == "primary":
        logger.warning(f"Cannot translate primary post {channel_post_id}")
        return

    # Get source text
    source_text = post.multi_post.primary_text_markdown
    target_language = post.language.code

    try:
        from apps.integrations.translation.client import TranslationClient

        client = TranslationClient()
        translation = client.translate_sync(
            text=source_text,
            source_language=post.multi_post.primary_channel.language.code,
            target_language=target_language,
        )

        if translation:
            from django.utils import timezone

            post.text_markdown = translation
            post.translation_requested = True
            post.translation_received_at = timezone.now()
            post.status = ChannelPostStatus.DRAFT
            post.save(
                update_fields=[
                    "text_markdown",
                    "translation_requested",
                    "translation_received_at",
                    "status",
                    "updated_at",
                ]
            )

            # Convert to HTML
            post.convert_to_telegram_html()

            logger.info(f"Successfully translated ChannelPost {channel_post_id}")
        else:
            logger.warning(f"Empty translation for ChannelPost {channel_post_id}")
            post.status = ChannelPostStatus.DRAFT
            post.save(update_fields=["status", "updated_at"])

    except Exception as e:
        logger.exception(f"Failed to translate ChannelPost {channel_post_id}: {e}")
        raise self.retry(exc=e)


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
    Publish a single channel post to Telegram.
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
        from apps.integrations.telegram_bot.client import TelegramBotClient

        client = TelegramBotClient()

        # Get photo URL if available
        photo_url = None
        if post.photo:
            photo_url = post.photo.url

        result = client.send_message_sync(
            chat_id=post.channel.telegram_chat_id,
            text=post.text_telegram_html,
            parse_mode="HTML",
            photo_url=photo_url,
            disable_web_page_preview=post.multi_post.disable_web_page_preview,
            disable_notification=post.multi_post.disable_notification,
        )

        if result and result.get("message_id"):
            post.mark_published(str(result["message_id"]))
            logger.info(f"Successfully published ChannelPost {channel_post_id}")
        else:
            post.mark_failed("No message ID received from Telegram")
            logger.error(f"Failed to publish ChannelPost {channel_post_id}: no message_id")

    except Exception as e:
        logger.exception(f"Failed to publish ChannelPost {channel_post_id}: {e}")
        post.mark_failed(str(e))
        raise self.retry(exc=e)

