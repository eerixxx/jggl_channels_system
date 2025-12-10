"""Telegram Channels serializers."""

from rest_framework import serializers

from .models import Channel, ChannelGroup, Language


class LanguageSerializer(serializers.ModelSerializer):
    """Serializer for Language model."""

    class Meta:
        model = Language
        fields = ["id", "code", "name", "native_name", "is_default", "is_active"]
        read_only_fields = ["id"]


class ChannelSerializer(serializers.ModelSerializer):
    """Serializer for Channel model."""

    language = LanguageSerializer(read_only=True)
    language_id = serializers.PrimaryKeyRelatedField(
        queryset=Language.objects.all(),
        source="language",
        write_only=True,
    )
    telegram_link = serializers.ReadOnlyField()
    is_bot_configured = serializers.ReadOnlyField()

    class Meta:
        model = Channel
        fields = [
            "id",
            "group",
            "telegram_chat_id",
            "title",
            "username",
            "language",
            "language_id",
            "description",
            "is_primary",
            "is_active",
            "bot_admin",
            "bot_can_post",
            "bot_can_edit",
            "bot_can_delete",
            "bot_can_read",
            "member_count",
            "photo_url",
            "invite_link",
            "telegram_link",
            "is_bot_configured",
            "last_synced_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "member_count",
            "photo_url",
            "last_synced_at",
            "created_at",
            "updated_at",
        ]


class ChannelListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for Channel lists."""

    language_code = serializers.CharField(source="language.code", read_only=True)

    class Meta:
        model = Channel
        fields = [
            "id",
            "title",
            "username",
            "language_code",
            "is_primary",
            "is_active",
            "member_count",
        ]


class ChannelGroupSerializer(serializers.ModelSerializer):
    """Serializer for ChannelGroup model."""

    channels = ChannelListSerializer(many=True, read_only=True)
    primary_channel = ChannelListSerializer(read_only=True)
    primary_channel_id = serializers.PrimaryKeyRelatedField(
        queryset=Channel.objects.all(),
        source="primary_channel",
        write_only=True,
        required=False,
        allow_null=True,
    )
    channels_count = serializers.ReadOnlyField()
    active_channels_count = serializers.ReadOnlyField()

    class Meta:
        model = ChannelGroup
        fields = [
            "id",
            "name",
            "description",
            "primary_channel",
            "primary_channel_id",
            "channels",
            "channels_count",
            "active_channels_count",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class ChannelGroupListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for ChannelGroup lists."""

    channels_count = serializers.ReadOnlyField()

    class Meta:
        model = ChannelGroup
        fields = ["id", "name", "is_active", "channels_count"]

