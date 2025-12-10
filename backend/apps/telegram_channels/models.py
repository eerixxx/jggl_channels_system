"""Telegram Channels models."""

from django.db import models
from django.core.exceptions import ValidationError

from apps.core.models import TimestampedModel


class Language(models.Model):
    """
    Language model for channel localization.
    """

    code = models.CharField(
        max_length=10,
        unique=True,
        help_text="ISO language code (e.g., 'en', 'ru', 'de')",
    )
    name = models.CharField(
        max_length=100,
        help_text="Human-readable language name (e.g., 'English', 'Russian')",
    )
    native_name = models.CharField(
        max_length=100,
        blank=True,
        help_text="Language name in its own language (e.g., 'Русский')",
    )
    is_default = models.BooleanField(
        default=False,
        help_text="Default language for new channels",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this language is available for selection",
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "Language"
        verbose_name_plural = "Languages"

    def __str__(self):
        return f"{self.name} ({self.code})"

    def save(self, *args, **kwargs):
        # Ensure only one default language
        if self.is_default:
            Language.objects.filter(is_default=True).exclude(pk=self.pk).update(
                is_default=False
            )
        super().save(*args, **kwargs)


class ChannelGroup(TimestampedModel):
    """
    Group of related Telegram channels (e.g., main channel + localized versions).
    """

    name = models.CharField(
        max_length=255,
        help_text="Internal name for the channel group",
    )
    description = models.TextField(
        blank=True,
        help_text="Description of the channel group",
    )
    primary_channel = models.ForeignKey(
        "Channel",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="primary_for_groups",
        help_text="Main channel (usually English) for this group",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this group is active",
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "Channel Group"
        verbose_name_plural = "Channel Groups"

    def __str__(self):
        return self.name

    @property
    def channels_count(self):
        """Return number of channels in this group."""
        return self.channels.count()

    @property
    def active_channels_count(self):
        """Return number of active channels in this group."""
        return self.channels.filter(is_active=True).count()

    def get_channels_by_language(self):
        """Return channels grouped by language."""
        return self.channels.select_related("language").order_by("language__name")

    def clean(self):
        # Validate that primary_channel belongs to this group
        if self.primary_channel and self.pk:
            if self.primary_channel.group_id != self.pk:
                raise ValidationError(
                    {"primary_channel": "Primary channel must belong to this group."}
                )


class Channel(TimestampedModel):
    """
    Single Telegram channel.
    """

    group = models.ForeignKey(
        ChannelGroup,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="channels",
        help_text="Channel group this channel belongs to",
    )
    telegram_chat_id = models.CharField(
        max_length=100,
        unique=True,
        help_text="Telegram chat ID (e.g., '-1001234567890')",
    )
    title = models.CharField(
        max_length=255,
        help_text="Channel title in Telegram",
    )
    username = models.CharField(
        max_length=100,
        blank=True,
        help_text="Channel username without @ (e.g., 'mychannel')",
    )
    language = models.ForeignKey(
        Language,
        on_delete=models.PROTECT,
        related_name="channels",
        null=True,
        blank=True,
        help_text="Language of this channel (optional)",
    )
    description = models.TextField(
        blank=True,
        help_text="Channel description",
    )
    is_primary = models.BooleanField(
        default=False,
        help_text="Whether this is the primary channel in its group",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this channel is active",
    )

    # Bot permissions
    bot_admin = models.BooleanField(
        default=False,
        help_text="Whether the bot is an admin in this channel",
    )
    bot_can_post = models.BooleanField(
        default=False,
        help_text="Whether the bot can post messages",
    )
    bot_can_edit = models.BooleanField(
        default=False,
        help_text="Whether the bot can edit messages",
    )
    bot_can_delete = models.BooleanField(
        default=False,
        help_text="Whether the bot can delete messages",
    )
    bot_can_read = models.BooleanField(
        default=False,
        help_text="Whether the bot can read channel statistics",
    )

    # Channel metadata from Telegram
    member_count = models.PositiveIntegerField(
        default=0,
        help_text="Current number of subscribers",
    )
    photo_url = models.URLField(
        blank=True,
        help_text="URL to channel photo",
    )
    invite_link = models.URLField(
        blank=True,
        help_text="Invite link to the channel",
    )

    # Additional metadata
    meta = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional metadata from Telegram",
    )

    # Sync status
    last_synced_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last time channel data was synced from Telegram",
    )

    class Meta:
        ordering = ["group__name", "language__name"]
        verbose_name = "Channel"
        verbose_name_plural = "Channels"
        constraints = [
            models.UniqueConstraint(
                fields=["group", "language"],
                name="unique_language_per_group",
                condition=models.Q(group__isnull=False),
            ),
        ]

    def __str__(self):
        lang_code = self.language.code if self.language else "no lang"
        if self.username:
            return f"@{self.username} ({lang_code})"
        return f"{self.title} ({lang_code})"

    @property
    def telegram_link(self):
        """Return the public Telegram link if username is available."""
        if self.username:
            return f"https://t.me/{self.username}"
        return self.invite_link or None

    @property
    def is_bot_configured(self):
        """Check if bot has necessary permissions."""
        return self.bot_admin and self.bot_can_post

    def clean(self):
        # Ensure only one primary per group
        if self.is_primary and self.group:
            existing_primary = Channel.objects.filter(
                group=self.group, is_primary=True
            ).exclude(pk=self.pk)
            if existing_primary.exists():
                raise ValidationError(
                    {
                        "is_primary": "Another channel is already marked as primary in this group."
                    }
                )

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update group's primary_channel if this is marked as primary
        if self.is_primary and self.group:
            if self.group.primary_channel_id != self.pk:
                ChannelGroup.objects.filter(pk=self.group_id).update(
                    primary_channel=self
                )

