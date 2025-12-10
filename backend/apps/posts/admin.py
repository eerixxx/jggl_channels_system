"""Posts admin configuration."""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe

from .models import ChannelPost, ChannelPostStatus, MultiChannelPost, PostStatus


class ChannelPostInline(admin.TabularInline):
    """Inline for channel posts within a multi-channel post."""

    model = ChannelPost
    extra = 0
    fields = [
        "channel",
        "language",
        "source_type",
        "status_display",
        "text_preview",
        "has_photo",
        "published_at",
    ]
    readonly_fields = [
        "channel",
        "language",
        "status_display",
        "text_preview",
        "has_photo",
        "published_at",
    ]
    show_change_link = True
    ordering = ["channel__language__name"]
    can_delete = False

    def status_display(self, obj):
        colors = {
            ChannelPostStatus.DRAFT: "gray",
            ChannelPostStatus.PENDING_TRANSLATION: "blue",
            ChannelPostStatus.PENDING_PUBLISH: "orange",
            ChannelPostStatus.PUBLISHING: "purple",
            ChannelPostStatus.PUBLISHED: "green",
            ChannelPostStatus.FAILED: "red",
        }
        color = colors.get(obj.status, "gray")
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display(),
        )

    status_display.short_description = "Status"

    def text_preview(self, obj):
        if obj.text_markdown:
            preview = obj.text_markdown[:100]
            if len(obj.text_markdown) > 100:
                preview += "..."
            return preview
        return "-"

    text_preview.short_description = "Text Preview"

    def has_photo(self, obj):
        if obj.photo:
            return format_html('<span style="color: green;">✓</span>')
        return format_html('<span style="color: gray;">-</span>')

    has_photo.short_description = "Photo"


@admin.register(MultiChannelPost)
class MultiChannelPostAdmin(admin.ModelAdmin):
    """Admin for MultiChannelPost model."""

    list_display = [
        "internal_title",
        "group",
        "status_display",
        "channels_progress",
        "auto_translate_enabled",
        "created_at",
        "published_at",
    ]
    list_filter = ["status", "auto_translate_enabled", "group", "created_at"]
    search_fields = ["internal_title", "primary_text_markdown"]
    ordering = ["-created_at"]
    raw_id_fields = ["group", "primary_channel"]
    inlines = [ChannelPostInline]
    date_hierarchy = "created_at"

    fieldsets = (
        (None, {"fields": ("group", "internal_title")}),
        (
            "Content",
            {
                "fields": (
                    "primary_channel",
                    "primary_text_markdown",
                    "primary_photo",
                )
            },
        ),
        (
            "Settings",
            {
                "fields": (
                    "auto_translate_enabled",
                    "disable_web_page_preview",
                    "disable_notification",
                    "scheduled_at",
                )
            },
        ),
        (
            "Status",
            {
                "fields": ("status", "published_at"),
                "classes": ("collapse",),
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )
    readonly_fields = ["status", "published_at", "created_at", "updated_at"]

    def status_display(self, obj):
        colors = {
            PostStatus.DRAFT: "gray",
            PostStatus.READY_FOR_PUBLISH: "blue",
            PostStatus.PUBLISHING: "purple",
            PostStatus.PUBLISHED: "green",
            PostStatus.PARTIAL_PUBLISHED: "orange",
            PostStatus.FAILED: "red",
        }
        color = colors.get(obj.status, "gray")
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display(),
        )

    status_display.short_description = "Status"

    def channels_progress(self, obj):
        total = obj.channel_posts_count
        published = obj.published_posts_count
        failed = obj.failed_posts_count

        if total == 0:
            return "-"

        if failed > 0:
            return format_html(
                '<span style="color: green;">{}</span> / '
                '<span style="color: red;">{}</span> / {}',
                published,
                failed,
                total,
            )
        return format_html("{} / {}", published, total)

    channels_progress.short_description = "Progress"

    actions = [
        "request_translations",
        "publish_all",
        "publish_ready",
        "mark_ready_for_publish",
    ]

    @admin.action(description="Request auto-translations")
    def request_translations(self, request, queryset):
        from apps.posts.tasks import request_translations

        count = 0
        for post in queryset:
            request_translations.delay(post.pk)
            count += 1
        self.message_user(request, f"Requested translations for {count} post(s).")

    @admin.action(description="Publish all channel posts")
    def publish_all(self, request, queryset):
        from apps.posts.tasks import publish_multi_post

        count = 0
        for post in queryset:
            publish_multi_post.delay(post.pk)
            count += 1
        self.message_user(request, f"Scheduled publishing for {count} post(s).")

    @admin.action(description="Publish ready channel posts only")
    def publish_ready(self, request, queryset):
        from apps.posts.tasks import publish_ready_channel_posts

        count = 0
        for post in queryset:
            publish_ready_channel_posts.delay(post.pk)
            count += 1
        self.message_user(request, f"Scheduled publishing for {count} post(s).")

    @admin.action(description="Mark as ready for publish")
    def mark_ready_for_publish(self, request, queryset):
        updated = queryset.filter(status=PostStatus.DRAFT).update(
            status=PostStatus.READY_FOR_PUBLISH
        )
        self.message_user(request, f"Marked {updated} post(s) as ready for publish.")


@admin.register(ChannelPost)
class ChannelPostAdmin(admin.ModelAdmin):
    """Admin for ChannelPost model."""

    list_display = [
        "multi_post_link",
        "channel",
        "language",
        "source_type",
        "status_display",
        "published_at",
    ]
    list_filter = ["status", "source_type", "language", "channel__group"]
    search_fields = [
        "multi_post__internal_title",
        "text_markdown",
        "channel__title",
    ]
    ordering = ["-multi_post__created_at", "channel__language__name"]
    raw_id_fields = ["multi_post", "channel"]

    fieldsets = (
        (None, {"fields": ("multi_post", "channel", "language")}),
        (
            "Content",
            {
                "fields": (
                    "source_type",
                    "text_markdown",
                    "text_telegram_html",
                    "photo",
                )
            },
        ),
        (
            "Translation",
            {
                "fields": (
                    "translation_requested",
                    "translation_received_at",
                    "manually_edited",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Status",
            {
                "fields": (
                    "status",
                    "telegram_message_id",
                    "published_at",
                    "error_message",
                )
            },
        ),
        (
            "Metadata",
            {
                "fields": ("meta",),
                "classes": ("collapse",),
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )
    readonly_fields = [
        "telegram_message_id",
        "published_at",
        "created_at",
        "updated_at",
    ]

    def multi_post_link(self, obj):
        url = reverse("admin:posts_multichannelpost_change", args=[obj.multi_post.pk])
        return format_html(
            '<a href="{}">{}</a>', url, obj.multi_post.internal_title
        )

    multi_post_link.short_description = "Multi-Channel Post"

    def status_display(self, obj):
        colors = {
            ChannelPostStatus.DRAFT: "gray",
            ChannelPostStatus.PENDING_TRANSLATION: "blue",
            ChannelPostStatus.PENDING_PUBLISH: "orange",
            ChannelPostStatus.PUBLISHING: "purple",
            ChannelPostStatus.PUBLISHED: "green",
            ChannelPostStatus.FAILED: "red",
        }
        color = colors.get(obj.status, "gray")
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display(),
        )

    status_display.short_description = "Status"

    actions = ["publish_selected", "convert_to_html", "request_translation"]

    @admin.action(description="Publish selected posts")
    def publish_selected(self, request, queryset):
        from apps.posts.tasks import publish_channel_post

        count = 0
        for post in queryset.filter(status__in=[
            ChannelPostStatus.DRAFT,
            ChannelPostStatus.PENDING_PUBLISH,
            ChannelPostStatus.FAILED,
        ]):
            publish_channel_post.delay(post.pk)
            count += 1
        self.message_user(request, f"Scheduled publishing for {count} post(s).")

    @admin.action(description="Convert markdown to Telegram HTML")
    def convert_to_html(self, request, queryset):
        count = 0
        for post in queryset:
            post.convert_to_telegram_html()
            count += 1
        self.message_user(request, f"Converted {count} post(s) to Telegram HTML.")

    @admin.action(description="Request translation")
    def request_translation(self, request, queryset):
        from apps.posts.tasks import translate_channel_post

        count = 0
        for post in queryset.exclude(source_type="primary"):
            translate_channel_post.delay(post.pk)
            count += 1
        self.message_user(request, f"Requested translation for {count} post(s).")

