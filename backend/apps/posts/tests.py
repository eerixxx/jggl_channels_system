"""Tests for posts app."""

import pytest
from apps.posts.models import (
    MultiChannelPost,
    ChannelPost,
    PostStatus,
    ChannelPostStatus,
    SourceType,
)


@pytest.mark.django_db
class TestMultiChannelPostModel:
    """Tests for MultiChannelPost model."""

    def test_create_post(self, channel_group, channel):
        """Test creating a multi-channel post."""
        post = MultiChannelPost.objects.create(
            group=channel_group,
            internal_title="Test Post",
            primary_channel=channel,
            primary_text_markdown="**Hello** world",
            auto_translate_enabled=True,
        )
        assert post.internal_title == "Test Post"
        assert post.status == PostStatus.DRAFT

    def test_creates_channel_posts(self, channel_group, channel, channel_ru):
        """Test that channel posts are created automatically."""
        post = MultiChannelPost.objects.create(
            group=channel_group,
            internal_title="Test Post",
            primary_channel=channel,
            primary_text_markdown="**Hello** world",
            auto_translate_enabled=True,
        )

        channel_posts = post.channel_posts.all()
        assert channel_posts.count() == 2

        # Check primary post
        primary_post = channel_posts.get(channel=channel)
        assert primary_post.source_type == SourceType.PRIMARY
        assert primary_post.text_markdown == "**Hello** world"

        # Check translated post
        translated_post = channel_posts.get(channel=channel_ru)
        assert translated_post.source_type == SourceType.AUTO_TRANSLATED
        assert translated_post.status == ChannelPostStatus.PENDING_TRANSLATION

    def test_manual_translation_mode(self, channel_group, channel, channel_ru):
        """Test creating post with manual translation mode."""
        post = MultiChannelPost.objects.create(
            group=channel_group,
            internal_title="Manual Post",
            primary_channel=channel,
            primary_text_markdown="Hello",
            auto_translate_enabled=False,
        )

        translated_post = post.channel_posts.get(channel=channel_ru)
        assert translated_post.source_type == SourceType.MANUAL
        assert translated_post.status == ChannelPostStatus.DRAFT


@pytest.mark.django_db
class TestChannelPostModel:
    """Tests for ChannelPost model."""

    def test_is_ready_for_publish(self, multi_post):
        """Test is_ready_for_publish property."""
        primary_post = multi_post.channel_posts.filter(
            source_type=SourceType.PRIMARY
        ).first()

        assert primary_post.is_ready_for_publish

        primary_post.text_markdown = ""
        primary_post.save()
        assert not primary_post.is_ready_for_publish

    def test_convert_to_telegram_html(self, multi_post):
        """Test markdown to HTML conversion."""
        primary_post = multi_post.channel_posts.filter(
            source_type=SourceType.PRIMARY
        ).first()

        primary_post.text_markdown = "**Bold** and *italic*"
        primary_post.save()
        primary_post.convert_to_telegram_html()

        assert "<b>Bold</b>" in primary_post.text_telegram_html
        assert "<i>italic</i>" in primary_post.text_telegram_html

    def test_mark_published(self, multi_post):
        """Test marking a post as published."""
        primary_post = multi_post.channel_posts.filter(
            source_type=SourceType.PRIMARY
        ).first()

        primary_post.mark_published("12345")

        assert primary_post.status == ChannelPostStatus.PUBLISHED
        assert primary_post.telegram_message_id == "12345"
        assert primary_post.published_at is not None

    def test_mark_failed(self, multi_post):
        """Test marking a post as failed."""
        primary_post = multi_post.channel_posts.filter(
            source_type=SourceType.PRIMARY
        ).first()

        primary_post.mark_failed("Bot error")

        assert primary_post.status == ChannelPostStatus.FAILED
        assert primary_post.error_message == "Bot error"


@pytest.mark.django_db
class TestMultiChannelPostAPI:
    """Tests for MultiChannelPost API endpoints."""

    def test_list_posts(self, authenticated_client, multi_post):
        """Test listing multi-channel posts."""
        response = authenticated_client.get("/api/v1/posts/multi/")
        assert response.status_code == 200
        assert len(response.data["results"]) == 1

    def test_create_post(self, authenticated_client, channel_group, channel):
        """Test creating a multi-channel post via API."""
        data = {
            "group": channel_group.pk,
            "internal_title": "API Post",
            "primary_channel": channel.pk,
            "primary_text_markdown": "Test content",
            "auto_translate_enabled": True,
        }
        response = authenticated_client.post("/api/v1/posts/multi/", data)
        assert response.status_code == 201
        assert response.data["internal_title"] == "API Post"

    def test_get_post_detail(self, authenticated_client, multi_post):
        """Test getting post details."""
        response = authenticated_client.get(f"/api/v1/posts/multi/{multi_post.pk}/")
        assert response.status_code == 200
        assert response.data["internal_title"] == "Test Post"
        assert len(response.data["channel_posts"]) > 0


@pytest.mark.django_db
class TestChannelPostAPI:
    """Tests for ChannelPost API endpoints."""

    def test_list_channel_posts(self, authenticated_client, multi_post):
        """Test listing channel posts."""
        response = authenticated_client.get("/api/v1/posts/channel/")
        assert response.status_code == 200
        assert len(response.data["results"]) > 0

    def test_update_channel_post(self, authenticated_client, multi_post):
        """Test updating a channel post."""
        channel_post = multi_post.channel_posts.first()
        data = {
            "text_markdown": "Updated content",
        }
        response = authenticated_client.patch(
            f"/api/v1/posts/channel/{channel_post.pk}/",
            data,
        )
        assert response.status_code == 200

        channel_post.refresh_from_db()
        assert channel_post.text_markdown == "Updated content"
        assert channel_post.manually_edited

