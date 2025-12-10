"""Post signals for automatic actions."""

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import MultiChannelPost


@receiver(post_save, sender=MultiChannelPost)
def create_channel_posts_on_multi_post_create(sender, instance, created, **kwargs):
    """
    Automatically create ChannelPost records when a MultiChannelPost is created.
    """
    if created:
        instance.create_channel_posts()

        # Trigger auto-translation if enabled
        if instance.auto_translate_enabled:
            from apps.posts.tasks import request_translations

            request_translations.delay(instance.pk)

