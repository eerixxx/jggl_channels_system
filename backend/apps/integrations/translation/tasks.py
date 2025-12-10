"""Celery tasks for translation integration."""

import logging

from celery import shared_task
from django.conf import settings

from apps.posts.models import ChannelPost, ChannelPostStatus, SourceType

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def translate_channel_post(self, channel_post_id: int):
    """
    Translate a single channel post.
    
    This task:
    1. Gets the primary post text from the multi-post
    2. Translates to the channel's language
    3. Updates the channel post with translated text
    """
    try:
        post = ChannelPost.objects.select_related(
            "multi_post", "multi_post__primary_channel", "channel", "language"
        ).get(pk=channel_post_id)
    except ChannelPost.DoesNotExist:
        logger.error(f"ChannelPost {channel_post_id} not found")
        return

    # Skip if not pending translation
    if post.status != ChannelPostStatus.PENDING_TRANSLATION:
        logger.info(f"ChannelPost {channel_post_id} not pending translation, skipping")
        return

    # Skip if already translated
    if post.translation_received_at:
        logger.info(f"ChannelPost {channel_post_id} already translated, skipping")
        return

    # Get source text and language
    source_text = post.multi_post.primary_text_markdown
    source_language = post.multi_post.primary_channel.language

    if not source_text:
        logger.warning(f"No source text for ChannelPost {channel_post_id}")
        post.status = ChannelPostStatus.DRAFT
        post.error_message = "No source text to translate"
        post.save(update_fields=["status", "error_message", "updated_at"])
        return

    if not source_language:
        logger.warning(f"No source language for ChannelPost {channel_post_id}")
        post.status = ChannelPostStatus.DRAFT
        post.error_message = "Source channel has no language set"
        post.save(update_fields=["status", "error_message", "updated_at"])
        return

    target_language = post.language
    if not target_language:
        logger.warning(f"No target language for ChannelPost {channel_post_id}")
        post.status = ChannelPostStatus.DRAFT
        post.error_message = "Channel has no language set"
        post.save(update_fields=["status", "error_message", "updated_at"])
        return

    # Skip if same language
    if source_language.code == target_language.code:
        logger.info(
            f"ChannelPost {channel_post_id}: same language, copying text"
        )
        post.text_markdown = source_text
        post.source_type = SourceType.PRIMARY
        post.status = ChannelPostStatus.DRAFT
        post.save(update_fields=[
            "text_markdown", "source_type", "status", "updated_at"
        ])
        return

    try:
        from .client import TranslationClient, TranslationError

        client = TranslationClient()

        # Check service health
        if not client.health_check():
            logger.warning("Translation service not healthy, will retry")
            raise self.retry(countdown=30)

        logger.info(
            f"Translating ChannelPost {channel_post_id}: "
            f"{source_language.code} -> {target_language.code}"
        )

        translated_text = client.translate_sync(
            text=source_text,
            source_language=source_language.code,
            target_language=target_language.code,
            context=getattr(settings, 'TRANSLATION_CONTEXT', 'news channel'),
            tone=getattr(settings, 'TRANSLATION_TONE', 'professional'),
            preserve_formatting=True,
        )

        # Update the post
        from django.utils import timezone
        
        post.text_markdown = translated_text
        post.source_type = SourceType.AUTO_TRANSLATED
        post.status = ChannelPostStatus.DRAFT  # Ready for review/publish
        post.translation_received_at = timezone.now()
        post.error_message = ""
        post.save(update_fields=[
            "text_markdown", "source_type", "status",
            "translation_received_at", "error_message", "updated_at"
        ])

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

        # Mark as failed for other errors
        post.status = ChannelPostStatus.DRAFT
        post.error_message = error_msg
        post.save(update_fields=["status", "error_message", "updated_at"])

    except Exception as e:
        logger.exception(f"Unexpected error translating ChannelPost {channel_post_id}")
        post.status = ChannelPostStatus.DRAFT
        post.error_message = f"Translation error: {str(e)}"
        post.save(update_fields=["status", "error_message", "updated_at"])


@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def translate_multi_post(self, multi_post_id: int):
    """
    Translate all pending channel posts for a multi-post.
    
    Uses batch translation for efficiency when multiple languages are needed.
    """
    from apps.posts.models import MultiChannelPost

    try:
        multi_post = MultiChannelPost.objects.prefetch_related(
            "channel_posts__channel__language",
            "primary_channel__language",
        ).get(pk=multi_post_id)
    except MultiChannelPost.DoesNotExist:
        logger.error(f"MultiChannelPost {multi_post_id} not found")
        return

    source_text = multi_post.primary_text_markdown
    source_language = multi_post.primary_channel.language

    if not source_text or not source_language:
        logger.warning(f"No source text/language for MultiChannelPost {multi_post_id}")
        return

    # Get posts pending translation
    pending_posts = multi_post.channel_posts.filter(
        status=ChannelPostStatus.PENDING_TRANSLATION,
        translation_received_at__isnull=True,
    ).exclude(
        language__code=source_language.code
    ).select_related("channel", "language")

    if not pending_posts.exists():
        logger.info(f"No pending translations for MultiChannelPost {multi_post_id}")
        return

    # Collect target languages
    target_languages = []
    post_by_language = {}
    for post in pending_posts:
        if post.language and post.language.code not in post_by_language:
            target_languages.append(post.language.code)
            post_by_language[post.language.code] = post

    if not target_languages:
        logger.info(f"No target languages for MultiChannelPost {multi_post_id}")
        return

    try:
        from .client import TranslationClient, TranslationError

        client = TranslationClient()

        logger.info(
            f"Batch translating MultiChannelPost {multi_post_id}: "
            f"{source_language.code} -> {target_languages}"
        )

        # Use batch translation
        translations = client.batch_translate_sync(
            text=source_text,
            source_language=source_language.code,
            target_languages=target_languages,
            context=getattr(settings, 'TRANSLATION_CONTEXT', 'news channel'),
            tone=getattr(settings, 'TRANSLATION_TONE', 'professional'),
            preserve_formatting=True,
        )

        from django.utils import timezone
        now = timezone.now()

        # Update posts with translations
        for lang_code, translated_text in translations.items():
            post = post_by_language.get(lang_code)
            if post:
                post.text_markdown = translated_text
                post.source_type = SourceType.AUTO_TRANSLATED
                post.status = ChannelPostStatus.DRAFT
                post.translation_received_at = now
                post.error_message = ""
                post.save(update_fields=[
                    "text_markdown", "source_type", "status",
                    "translation_received_at", "error_message", "updated_at"
                ])
                logger.info(f"Updated ChannelPost {post.pk} with {lang_code} translation")

        # Mark failed for languages not returned
        for lang_code, post in post_by_language.items():
            if lang_code not in translations:
                post.error_message = f"Translation to {lang_code} failed"
                post.save(update_fields=["error_message", "updated_at"])
                logger.warning(f"No translation returned for {lang_code}")

        logger.info(
            f"Batch translation complete for MultiChannelPost {multi_post_id}: "
            f"{len(translations)}/{len(target_languages)} languages"
        )

    except TranslationError as e:
        error_msg = f"[{e.code}] {e.message}"
        logger.error(f"Batch translation error: {error_msg}")

        if e.code in ("LLM_RATE_LIMIT", "LLM_UNAVAILABLE", "LLM_TIMEOUT"):
            raise self.retry(exc=e, countdown=60)

        # Fall back to individual translations
        logger.info("Falling back to individual translations")
        for post in pending_posts:
            translate_channel_post.delay(post.pk)

    except Exception as e:
        logger.exception(f"Unexpected error in batch translation")
        # Fall back to individual translations
        for post in pending_posts:
            translate_channel_post.delay(post.pk)


@shared_task
def process_pending_translations():
    """
    Periodic task to process any pending translations.
    
    This catches any posts that might have been missed.
    """
    pending_posts = ChannelPost.objects.filter(
        status=ChannelPostStatus.PENDING_TRANSLATION,
        translation_requested=False,
    ).select_related("multi_post")

    if not pending_posts.exists():
        return

    logger.info(f"Found {pending_posts.count()} pending translations")

    # Group by multi-post for batch processing
    multi_post_ids = set()
    for post in pending_posts:
        multi_post_ids.add(post.multi_post_id)
        post.translation_requested = True
        post.save(update_fields=["translation_requested", "updated_at"])

    for multi_post_id in multi_post_ids:
        translate_multi_post.delay(multi_post_id)

    logger.info(f"Scheduled translation for {len(multi_post_ids)} multi-posts")

