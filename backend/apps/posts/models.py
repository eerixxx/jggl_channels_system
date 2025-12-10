"""Posts models for multi-channel posting."""

from django.db import models

from apps.core.models import TimestampedModel
from apps.telegram_channels.models import Channel, ChannelGroup, Language


class PostStatus(models.TextChoices):
    """Status choices for MultiChannelPost."""

    DRAFT = "draft", "Draft"
    READY_FOR_PUBLISH = "ready_for_publish", "Ready for Publish"
    PUBLISHING = "publishing", "Publishing"
    PUBLISHED = "published", "Published"
    PARTIAL_PUBLISHED = "partial_published", "Partially Published"
    FAILED = "failed", "Failed"


class ChannelPostStatus(models.TextChoices):
    """Status choices for ChannelPost."""

    DRAFT = "draft", "Draft"
    PENDING_TRANSLATION = "pending_translation", "Pending Translation"
    PENDING_PUBLISH = "pending_publish", "Pending Publish"
    PUBLISHING = "publishing", "Publishing"
    PUBLISHED = "published", "Published"
    FAILED = "failed", "Failed"


class SourceType(models.TextChoices):
    """Source type for ChannelPost content."""

    PRIMARY = "primary", "Primary (Original)"
    AUTO_TRANSLATED = "auto_translated", "Auto-translated"
    MANUAL = "manual", "Manual"


class MultiChannelPost(TimestampedModel):
    """
    Main post entity that groups posts across multiple channels.
    """

    group = models.ForeignKey(
        ChannelGroup,
        on_delete=models.CASCADE,
        related_name="posts",
        help_text="Channel group this post belongs to",
    )
    internal_title = models.CharField(
        max_length=255,
        help_text="Internal title for identification (not published)",
    )
    primary_channel = models.ForeignKey(
        Channel,
        on_delete=models.PROTECT,
        related_name="primary_posts",
        help_text="Primary channel (source of original content)",
    )
    primary_text_markdown = models.TextField(
        help_text="Original post text in Markdown format",
    )
    primary_photo = models.ImageField(
        upload_to="posts/photos/%Y/%m/",
        null=True,
        blank=True,
        help_text="Primary photo for the post",
    )
    auto_translate_enabled = models.BooleanField(
        default=True,
        help_text="Whether to automatically translate to other channels",
    )
    status = models.CharField(
        max_length=20,
        choices=PostStatus.choices,
        default=PostStatus.DRAFT,
        db_index=True,
    )
    published_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the post was fully published",
    )
    scheduled_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Scheduled publication time (if set)",
    )

    # Additional options
    disable_web_page_preview = models.BooleanField(
        default=False,
        help_text="Disable link previews in the message",
    )
    disable_notification = models.BooleanField(
        default=False,
        help_text="Send message silently",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Multi-Channel Post"
        verbose_name_plural = "Multi-Channel Posts"

    def __str__(self):
        return f"{self.internal_title} ({self.group.name})"

    @property
    def channel_posts_count(self):
        """Return total number of channel posts."""
        return self.channel_posts.count()

    @property
    def published_posts_count(self):
        """Return number of successfully published channel posts."""
        return self.channel_posts.filter(status=ChannelPostStatus.PUBLISHED).count()

    @property
    def failed_posts_count(self):
        """Return number of failed channel posts."""
        return self.channel_posts.filter(status=ChannelPostStatus.FAILED).count()

    @property
    def pending_posts_count(self):
        """Return number of pending channel posts."""
        return self.channel_posts.exclude(
            status__in=[ChannelPostStatus.PUBLISHED, ChannelPostStatus.FAILED]
        ).count()

    def get_channel_post(self, channel: Channel):
        """Get the ChannelPost for a specific channel."""
        return self.channel_posts.filter(channel=channel).first()

    def create_channel_posts(self):
        """
        Create ChannelPost records for all channels in the group.
        Called after the MultiChannelPost is created.
        """
        channels = self.group.channels.filter(is_active=True).select_related("language")

        for channel in channels:
            is_primary = channel.pk == self.primary_channel_id

            ChannelPost.objects.get_or_create(
                multi_post=self,
                channel=channel,
                defaults={
                    "language": channel.language,
                    "source_type": SourceType.PRIMARY
                    if is_primary
                    else (
                        SourceType.AUTO_TRANSLATED
                        if self.auto_translate_enabled
                        else SourceType.MANUAL
                    ),
                    "text_markdown": self.primary_text_markdown if is_primary else "",
                    "photo": self.primary_photo if is_primary else None,
                    "status": ChannelPostStatus.DRAFT
                    if is_primary
                    else (
                        ChannelPostStatus.PENDING_TRANSLATION
                        if self.auto_translate_enabled
                        else ChannelPostStatus.DRAFT
                    ),
                },
            )

    def update_status(self):
        """Update the overall status based on channel posts."""
        channel_posts = self.channel_posts.all()
        total = channel_posts.count()

        if total == 0:
            return

        published = channel_posts.filter(status=ChannelPostStatus.PUBLISHED).count()
        failed = channel_posts.filter(status=ChannelPostStatus.FAILED).count()
        publishing = channel_posts.filter(status=ChannelPostStatus.PUBLISHING).count()

        if published == total:
            self.status = PostStatus.PUBLISHED
        elif failed == total:
            self.status = PostStatus.FAILED
        elif published > 0 and (published + failed) == total:
            self.status = PostStatus.PARTIAL_PUBLISHED
        elif publishing > 0:
            self.status = PostStatus.PUBLISHING
        else:
            # Keep current status
            pass

        self.save(update_fields=["status", "updated_at"])


class ChannelPost(TimestampedModel):
    """
    Post variant for a specific channel.
    """

    multi_post = models.ForeignKey(
        MultiChannelPost,
        on_delete=models.CASCADE,
        related_name="channel_posts",
    )
    channel = models.ForeignKey(
        Channel,
        on_delete=models.CASCADE,
        related_name="posts",
    )
    language = models.ForeignKey(
        Language,
        on_delete=models.PROTECT,
        related_name="channel_posts",
        help_text="Language of this post variant",
    )
    source_type = models.CharField(
        max_length=20,
        choices=SourceType.choices,
        default=SourceType.MANUAL,
    )

    # Content
    text_markdown = models.TextField(
        blank=True,
        help_text="Post text in Markdown format",
    )
    text_telegram_html = models.TextField(
        blank=True,
        help_text="Post text converted to Telegram HTML",
    )
    photo = models.ImageField(
        upload_to="posts/photos/%Y/%m/",
        null=True,
        blank=True,
        help_text="Photo for this channel variant",
    )

    # Telegram message info
    telegram_message_id = models.CharField(
        max_length=100,
        blank=True,
        help_text="Message ID in Telegram",
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=ChannelPostStatus.choices,
        default=ChannelPostStatus.DRAFT,
        db_index=True,
    )

    # Translation tracking
    translation_requested = models.BooleanField(
        default=False,
        help_text="Whether translation has been requested",
    )
    translation_received_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    manually_edited = models.BooleanField(
        default=False,
        help_text="Whether the translation was manually edited",
    )

    # Publishing
    published_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    error_message = models.TextField(
        blank=True,
        help_text="Error message if publishing failed",
    )

    # Metadata
    meta = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional metadata",
    )

    class Meta:
        ordering = ["channel__language__name"]
        verbose_name = "Channel Post"
        verbose_name_plural = "Channel Posts"
        constraints = [
            models.UniqueConstraint(
                fields=["multi_post", "channel"],
                name="unique_post_per_channel",
            ),
        ]

    def __str__(self):
        return f"{self.multi_post.internal_title} - {self.channel}"

    @property
    def is_ready_for_publish(self):
        """Check if post is ready to be published."""
        return bool(self.text_markdown or self.text_telegram_html) and self.channel.bot_can_post

    def convert_to_telegram_html(self):
        """Convert markdown text to Telegram HTML."""
        from apps.core.utils import markdown_to_telegram_html

        if self.text_markdown:
            self.text_telegram_html = markdown_to_telegram_html(self.text_markdown)
            self.save(update_fields=["text_telegram_html", "updated_at"])

    def publish(self):
        """Trigger publishing of this post."""
        from apps.posts.tasks import publish_channel_post

        if not self.is_ready_for_publish:
            raise ValueError("Post is not ready for publishing")

        self.status = ChannelPostStatus.PUBLISHING
        self.save(update_fields=["status", "updated_at"])

        publish_channel_post.delay(self.pk)

    def mark_published(self, telegram_message_id: str):
        """Mark the post as successfully published."""
        from django.utils import timezone

        self.status = ChannelPostStatus.PUBLISHED
        self.telegram_message_id = telegram_message_id
        self.published_at = timezone.now()
        self.error_message = ""
        self.save(
            update_fields=[
                "status",
                "telegram_message_id",
                "published_at",
                "error_message",
                "updated_at",
            ]
        )

        # Update parent status
        self.multi_post.update_status()

    def mark_failed(self, error_message: str):
        """Mark the post as failed."""
        self.status = ChannelPostStatus.FAILED
        self.error_message = error_message
        self.save(update_fields=["status", "error_message", "updated_at"])

        # Update parent status
        self.multi_post.update_status()

