"""Tests for telegram_channels app."""

import pytest
from django.db import IntegrityError

from apps.telegram_channels.models import Channel, ChannelGroup, Language


@pytest.mark.django_db
class TestLanguageModel:
    """Tests for Language model."""

    def test_create_language(self):
        """Test creating a language."""
        lang = Language.objects.create(
            code="en",
            name="English",
            native_name="English",
            is_default=True,
        )
        assert lang.code == "en"
        assert str(lang) == "English (en)"

    def test_unique_code(self, language):
        """Test that language code is unique."""
        with pytest.raises(IntegrityError):
            Language.objects.create(code="en", name="English 2")

    def test_single_default(self, language):
        """Test that only one language can be default."""
        lang2 = Language.objects.create(
            code="ru",
            name="Russian",
            is_default=True,
        )
        language.refresh_from_db()
        assert not language.is_default
        assert lang2.is_default


@pytest.mark.django_db
class TestChannelGroupModel:
    """Tests for ChannelGroup model."""

    def test_create_group(self):
        """Test creating a channel group."""
        group = ChannelGroup.objects.create(
            name="Test Group",
            description="Test description",
        )
        assert group.name == "Test Group"
        assert str(group) == "Test Group"

    def test_channels_count(self, channel_group, channel, channel_ru):
        """Test channels count property."""
        assert channel_group.channels_count == 2
        assert channel_group.active_channels_count == 2


@pytest.mark.django_db
class TestChannelModel:
    """Tests for Channel model."""

    def test_create_channel(self, channel_group, language):
        """Test creating a channel."""
        channel = Channel.objects.create(
            group=channel_group,
            telegram_chat_id="-1001111111111",
            title="Test Channel",
            language=language,
        )
        assert channel.title == "Test Channel"
        assert not channel.is_bot_configured  # bot_admin and bot_can_post are False

    def test_unique_telegram_chat_id(self, channel, channel_group, language_ru):
        """Test that telegram_chat_id is unique."""
        with pytest.raises(IntegrityError):
            Channel.objects.create(
                group=channel_group,
                telegram_chat_id=channel.telegram_chat_id,
                title="Duplicate Channel",
                language=language_ru,
            )

    def test_is_bot_configured(self, channel):
        """Test is_bot_configured property."""
        assert channel.is_bot_configured  # Both bot_admin and bot_can_post are True

        channel.bot_can_post = False
        channel.save()
        assert not channel.is_bot_configured

    def test_telegram_link(self, channel):
        """Test telegram_link property."""
        assert channel.telegram_link == "https://t.me/testchannel_en"

        channel.username = ""
        channel.invite_link = "https://t.me/+abc123"
        channel.save()
        assert channel.telegram_link == "https://t.me/+abc123"

    def test_unique_language_per_group(self, channel, channel_group, language):
        """Test that only one channel per language per group."""
        with pytest.raises(IntegrityError):
            Channel.objects.create(
                group=channel_group,
                telegram_chat_id="-1002222222222",
                title="Another EN Channel",
                language=language,
            )


@pytest.mark.django_db
class TestChannelGroupAPI:
    """Tests for ChannelGroup API endpoints."""

    def test_list_groups(self, authenticated_client, channel_group):
        """Test listing channel groups."""
        response = authenticated_client.get("/api/v1/channels/groups/")
        assert response.status_code == 200
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["name"] == "Test Group"

    def test_get_group_detail(self, authenticated_client, channel_group, channel):
        """Test getting channel group details."""
        response = authenticated_client.get(f"/api/v1/channels/groups/{channel_group.pk}/")
        assert response.status_code == 200
        assert response.data["name"] == "Test Group"
        assert len(response.data["channels"]) == 1


@pytest.mark.django_db
class TestChannelAPI:
    """Tests for Channel API endpoints."""

    def test_list_channels(self, authenticated_client, channel):
        """Test listing channels."""
        response = authenticated_client.get("/api/v1/channels/")
        assert response.status_code == 200
        assert len(response.data["results"]) == 1

    def test_filter_by_group(self, authenticated_client, channel, channel_group):
        """Test filtering channels by group."""
        response = authenticated_client.get(
            f"/api/v1/channels/?group={channel_group.pk}"
        )
        assert response.status_code == 200
        assert len(response.data["results"]) == 1

