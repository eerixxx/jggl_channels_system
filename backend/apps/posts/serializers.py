"""Posts serializers."""

from rest_framework import serializers

from apps.telegram_channels.serializers import (
    ChannelListSerializer,
    ChannelGroupListSerializer,
    LanguageSerializer,
)

from .models import ChannelPost, MultiChannelPost


class ChannelPostSerializer(serializers.ModelSerializer):
    """Serializer for ChannelPost model."""

    channel = ChannelListSerializer(read_only=True)
    language = LanguageSerializer(read_only=True)
    is_ready_for_publish = serializers.ReadOnlyField()

    class Meta:
        model = ChannelPost
        fields = [
            "id",
            "multi_post",
            "channel",
            "language",
            "source_type",
            "text_markdown",
            "text_telegram_html",
            "photo",
            "telegram_message_id",
            "status",
            "translation_requested",
            "translation_received_at",
            "manually_edited",
            "published_at",
            "error_message",
            "is_ready_for_publish",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "telegram_message_id",
            "translation_received_at",
            "published_at",
            "created_at",
            "updated_at",
        ]


class ChannelPostUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating ChannelPost content."""

    class Meta:
        model = ChannelPost
        fields = ["text_markdown", "photo", "manually_edited"]

    def update(self, instance, validated_data):
        # If text is being updated, mark as manually edited
        if "text_markdown" in validated_data:
            validated_data["manually_edited"] = True
        return super().update(instance, validated_data)


class MultiChannelPostSerializer(serializers.ModelSerializer):
    """Serializer for MultiChannelPost model."""

    group = ChannelGroupListSerializer(read_only=True)
    group_id = serializers.PrimaryKeyRelatedField(
        queryset=ChannelPost.objects.none(),
        source="group",
        write_only=True,
    )
    primary_channel = ChannelListSerializer(read_only=True)
    primary_channel_id = serializers.PrimaryKeyRelatedField(
        queryset=ChannelPost.objects.none(),
        source="primary_channel",
        write_only=True,
    )
    channel_posts = ChannelPostSerializer(many=True, read_only=True)
    channel_posts_count = serializers.ReadOnlyField()
    published_posts_count = serializers.ReadOnlyField()
    failed_posts_count = serializers.ReadOnlyField()
    pending_posts_count = serializers.ReadOnlyField()

    class Meta:
        model = MultiChannelPost
        fields = [
            "id",
            "group",
            "group_id",
            "internal_title",
            "primary_channel",
            "primary_channel_id",
            "primary_text_markdown",
            "primary_photo",
            "auto_translate_enabled",
            "status",
            "published_at",
            "scheduled_at",
            "disable_web_page_preview",
            "disable_notification",
            "channel_posts",
            "channel_posts_count",
            "published_posts_count",
            "failed_posts_count",
            "pending_posts_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "published_at",
            "created_at",
            "updated_at",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set proper querysets
        from apps.telegram_channels.models import Channel, ChannelGroup

        self.fields["group_id"].queryset = ChannelGroup.objects.all()
        self.fields["primary_channel_id"].queryset = Channel.objects.all()


class MultiChannelPostListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for MultiChannelPost lists."""

    group_name = serializers.CharField(source="group.name", read_only=True)
    channel_posts_count = serializers.ReadOnlyField()
    published_posts_count = serializers.ReadOnlyField()

    class Meta:
        model = MultiChannelPost
        fields = [
            "id",
            "internal_title",
            "group_name",
            "status",
            "channel_posts_count",
            "published_posts_count",
            "auto_translate_enabled",
            "created_at",
            "published_at",
        ]


class MultiChannelPostCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating MultiChannelPost."""

    class Meta:
        model = MultiChannelPost
        fields = [
            "group",
            "internal_title",
            "primary_channel",
            "primary_text_markdown",
            "primary_photo",
            "auto_translate_enabled",
            "scheduled_at",
            "disable_web_page_preview",
            "disable_notification",
        ]

    def validate(self, data):
        # Ensure primary_channel belongs to the group
        if data["primary_channel"].group != data["group"]:
            raise serializers.ValidationError(
                {"primary_channel": "Primary channel must belong to the selected group."}
            )
        return data

