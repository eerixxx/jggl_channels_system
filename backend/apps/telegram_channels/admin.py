"""Telegram Channels admin configuration."""

from django.contrib import admin
from django.utils.html import format_html

from .models import Channel, ChannelGroup, Language


@admin.register(Language)
class LanguageAdmin(admin.ModelAdmin):
    """Admin for Language model."""

    list_display = ["code", "name", "native_name", "is_default", "is_active"]
    list_filter = ["is_active", "is_default"]
    search_fields = ["code", "name", "native_name"]
    ordering = ["name"]

    fieldsets = (
        (None, {"fields": ("code", "name", "native_name")}),
        ("Status", {"fields": ("is_default", "is_active")}),
    )


class ChannelInline(admin.TabularInline):
    """Inline for channels within a group."""

    model = Channel
    extra = 0
    fields = [
        "title",
        "username",
        "language",
        "is_primary",
        "is_active",
        "bot_can_post",
        "member_count",
    ]
    readonly_fields = ["member_count"]
    show_change_link = True
    ordering = ["language__name"]


@admin.register(ChannelGroup)
class ChannelGroupAdmin(admin.ModelAdmin):
    """Admin for ChannelGroup model."""

    list_display = [
        "name",
        "primary_channel_display",
        "channels_count",
        "active_channels_count",
        "is_active",
        "created_at",
    ]
    list_filter = ["is_active", "created_at"]
    search_fields = ["name", "description"]
    ordering = ["name"]
    inlines = [ChannelInline]

    fieldsets = (
        (None, {"fields": ("name", "description")}),
        ("Configuration", {"fields": ("primary_channel", "is_active")}),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )
    readonly_fields = ["created_at", "updated_at"]

    def primary_channel_display(self, obj):
        if obj.primary_channel:
            return format_html(
                '<a href="/admin/telegram_channels/channel/{}/change/">{}</a>',
                obj.primary_channel.pk,
                obj.primary_channel,
            )
        return "-"

    primary_channel_display.short_description = "Primary Channel"

    def channels_count(self, obj):
        return obj.channels_count

    channels_count.short_description = "Total Channels"

    def active_channels_count(self, obj):
        return obj.active_channels_count

    active_channels_count.short_description = "Active Channels"

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "primary_channel":
            # Filter to show only channels from this group
            if request.resolver_match.kwargs.get("object_id"):
                group_id = request.resolver_match.kwargs["object_id"]
                kwargs["queryset"] = Channel.objects.filter(group_id=group_id)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(Channel)
class ChannelAdmin(admin.ModelAdmin):
    """Admin for Channel model."""

    list_display = [
        "title",
        "username_display",
        "group",
        "language",
        "is_primary",
        "is_active",
        "bot_status_display",
        "member_count",
        "last_synced_at",
    ]
    list_filter = [
        "is_active",
        "is_primary",
        "bot_admin",
        "bot_can_post",
        "group",
        "language",
    ]
    search_fields = ["title", "username", "telegram_chat_id", "description"]
    ordering = ["group__name", "language__name"]
    raw_id_fields = ["group"]
    autocomplete_fields = ["language"]

    fieldsets = (
        (
            None,
            {"fields": ("group", "telegram_chat_id", "title", "username", "language")},
        ),
        ("Status", {"fields": ("is_primary", "is_active", "description")}),
        (
            "Bot Permissions",
            {
                "fields": (
                    "bot_admin",
                    "bot_can_post",
                    "bot_can_edit",
                    "bot_can_delete",
                    "bot_can_read",
                )
            },
        ),
        (
            "Channel Info",
            {
                "fields": ("member_count", "photo_url", "invite_link"),
                "classes": ("collapse",),
            },
        ),
        (
            "Metadata",
            {"fields": ("meta", "last_synced_at"), "classes": ("collapse",)},
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )
    readonly_fields = [
        "member_count",
        "photo_url",
        "last_synced_at",
        "created_at",
        "updated_at",
    ]

    def username_display(self, obj):
        if obj.username:
            return format_html(
                '<a href="https://t.me/{}" target="_blank">@{}</a>',
                obj.username,
                obj.username,
            )
        return "-"

    username_display.short_description = "Username"

    def bot_status_display(self, obj):
        if obj.bot_admin and obj.bot_can_post:
            return format_html('<span style="color: green;">✓ Ready</span>')
        elif obj.bot_admin:
            return format_html('<span style="color: orange;">⚠ Limited</span>')
        return format_html('<span style="color: red;">✗ Not configured</span>')

    bot_status_display.short_description = "Bot Status"

    actions = ["sync_channel_stats", "verify_bot_permissions"]

    @admin.action(description="Sync channel statistics")
    def sync_channel_stats(self, request, queryset):
        from apps.integrations.telegram_bot.tasks import sync_channel_info

        count = 0
        for channel in queryset:
            sync_channel_info.delay(channel.pk)
            count += 1
        self.message_user(request, f"Scheduled sync for {count} channel(s).")

    @admin.action(description="Verify bot permissions")
    def verify_bot_permissions(self, request, queryset):
        from apps.integrations.telegram_bot.tasks import verify_bot_permissions

        count = 0
        for channel in queryset:
            verify_bot_permissions.delay(channel.pk)
            count += 1
        self.message_user(
            request, f"Scheduled permission check for {count} channel(s)."
        )

