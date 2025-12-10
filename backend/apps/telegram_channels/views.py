"""Telegram Channels views."""

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Channel, ChannelGroup, Language
from .serializers import (
    ChannelGroupListSerializer,
    ChannelGroupSerializer,
    ChannelListSerializer,
    ChannelSerializer,
    LanguageSerializer,
)


class LanguageViewSet(viewsets.ModelViewSet):
    """ViewSet for Language model."""

    queryset = Language.objects.all()
    serializer_class = LanguageSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["code", "name", "native_name"]
    ordering_fields = ["name", "code"]
    ordering = ["name"]


class ChannelGroupViewSet(viewsets.ModelViewSet):
    """ViewSet for ChannelGroup model."""

    queryset = ChannelGroup.objects.prefetch_related(
        "channels", "channels__language"
    ).select_related("primary_channel")
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["is_active"]
    search_fields = ["name", "description"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]

    def get_serializer_class(self):
        if self.action == "list":
            return ChannelGroupListSerializer
        return ChannelGroupSerializer

    @action(detail=True, methods=["get"])
    def channels(self, request, pk=None):
        """Get all channels for a group."""
        group = self.get_object()
        channels = group.channels.select_related("language").all()
        serializer = ChannelListSerializer(channels, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def sync_stats(self, request, pk=None):
        """Trigger stats sync for all channels in the group."""
        from apps.integrations.telegram_bot.tasks import sync_channel_info

        group = self.get_object()
        count = 0
        for channel in group.channels.filter(is_active=True):
            sync_channel_info.delay(channel.pk)
            count += 1
        return Response({"message": f"Scheduled sync for {count} channels"})


class ChannelViewSet(viewsets.ModelViewSet):
    """ViewSet for Channel model."""

    queryset = Channel.objects.select_related("group", "language")
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["group", "language", "is_active", "is_primary", "bot_can_post"]
    search_fields = ["title", "username", "telegram_chat_id"]
    ordering_fields = ["title", "member_count", "created_at"]
    ordering = ["title"]

    def get_serializer_class(self):
        if self.action == "list":
            return ChannelListSerializer
        return ChannelSerializer

    @action(detail=True, methods=["post"])
    def sync(self, request, pk=None):
        """Trigger sync for this channel."""
        from apps.integrations.telegram_bot.tasks import sync_channel_info

        channel = self.get_object()
        sync_channel_info.delay(channel.pk)
        return Response({"message": "Sync scheduled"})

    @action(detail=True, methods=["post"])
    def verify_bot(self, request, pk=None):
        """Verify bot permissions for this channel."""
        from apps.integrations.telegram_bot.tasks import verify_bot_permissions

        channel = self.get_object()
        verify_bot_permissions.delay(channel.pk)
        return Response({"message": "Verification scheduled"})

