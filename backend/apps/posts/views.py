"""Posts views."""

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import ChannelPost, ChannelPostStatus, MultiChannelPost, PostStatus
from .serializers import (
    ChannelPostSerializer,
    ChannelPostUpdateSerializer,
    MultiChannelPostCreateSerializer,
    MultiChannelPostListSerializer,
    MultiChannelPostSerializer,
)


class MultiChannelPostViewSet(viewsets.ModelViewSet):
    """ViewSet for MultiChannelPost model."""

    queryset = MultiChannelPost.objects.select_related(
        "group", "primary_channel"
    ).prefetch_related("channel_posts", "channel_posts__channel", "channel_posts__language")
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["group", "status", "auto_translate_enabled"]
    search_fields = ["internal_title", "primary_text_markdown"]
    ordering_fields = ["created_at", "published_at", "internal_title"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return MultiChannelPostListSerializer
        elif self.action == "create":
            return MultiChannelPostCreateSerializer
        return MultiChannelPostSerializer

    @action(detail=True, methods=["post"])
    def request_translations(self, request, pk=None):
        """Request auto-translations for all channel posts."""
        from apps.posts.tasks import request_translations

        post = self.get_object()
        request_translations.delay(post.pk)
        return Response({"message": "Translation request queued"})

    @action(detail=True, methods=["post"])
    def publish_all(self, request, pk=None):
        """Publish to all channels."""
        from apps.posts.tasks import publish_multi_post

        post = self.get_object()
        publish_multi_post.delay(post.pk)
        return Response({"message": "Publishing queued for all channels"})

    @action(detail=True, methods=["post"])
    def publish_ready(self, request, pk=None):
        """Publish only ready channel posts."""
        from apps.posts.tasks import publish_ready_channel_posts

        post = self.get_object()
        publish_ready_channel_posts.delay(post.pk)
        return Response({"message": "Publishing queued for ready channels"})

    @action(detail=True, methods=["post"])
    def mark_ready(self, request, pk=None):
        """Mark post as ready for publish."""
        post = self.get_object()
        if post.status == PostStatus.DRAFT:
            post.status = PostStatus.READY_FOR_PUBLISH
            post.save(update_fields=["status", "updated_at"])
            return Response({"message": "Post marked as ready for publish"})
        return Response(
            {"error": "Post is not in draft status"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    @action(detail=True, methods=["get"])
    def channel_posts(self, request, pk=None):
        """Get all channel posts for this multi-post."""
        post = self.get_object()
        channel_posts = post.channel_posts.select_related("channel", "language").all()
        serializer = ChannelPostSerializer(channel_posts, many=True)
        return Response(serializer.data)


class ChannelPostViewSet(viewsets.ModelViewSet):
    """ViewSet for ChannelPost model."""

    queryset = ChannelPost.objects.select_related(
        "multi_post", "channel", "language"
    )
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["multi_post", "channel", "language", "status", "source_type"]
    search_fields = ["multi_post__internal_title", "text_markdown"]
    ordering_fields = ["created_at", "published_at"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action in ["update", "partial_update"]:
            return ChannelPostUpdateSerializer
        return ChannelPostSerializer

    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        """Publish this channel post."""
        from apps.posts.tasks import publish_channel_post

        post = self.get_object()
        if not post.is_ready_for_publish:
            return Response(
                {"error": "Post is not ready for publishing"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        publish_channel_post.delay(post.pk)
        return Response({"message": "Publishing queued"})

    @action(detail=True, methods=["post"])
    def request_translation(self, request, pk=None):
        """Request translation for this channel post."""
        from apps.posts.tasks import translate_channel_post

        post = self.get_object()
        if post.source_type == "primary":
            return Response(
                {"error": "Cannot translate primary post"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        translate_channel_post.delay(post.pk)
        return Response({"message": "Translation request queued"})

    @action(detail=True, methods=["post"])
    def convert_to_html(self, request, pk=None):
        """Convert markdown to Telegram HTML."""
        post = self.get_object()
        post.convert_to_telegram_html()
        return Response({"html": post.text_telegram_html})

