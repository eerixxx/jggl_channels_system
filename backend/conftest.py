"""Pytest configuration and fixtures."""

import pytest
from django.conf import settings


@pytest.fixture(scope="session")
def django_db_setup():
    """Configure test database settings."""
    settings.DATABASES["default"] = {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "test_channels_admin",
        "USER": settings.DATABASES["default"].get("USER", "postgres"),
        "PASSWORD": settings.DATABASES["default"].get("PASSWORD", "postgres"),
        "HOST": settings.DATABASES["default"].get("HOST", "localhost"),
        "PORT": settings.DATABASES["default"].get("PORT", "5432"),
    }


@pytest.fixture
def api_client():
    """Return an API client for testing."""
    from rest_framework.test import APIClient

    return APIClient()


@pytest.fixture
def authenticated_client(api_client, django_user_model):
    """Return an authenticated API client."""
    user = django_user_model.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="testpass123",
    )
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def admin_client(api_client, django_user_model):
    """Return an admin-authenticated API client."""
    user = django_user_model.objects.create_superuser(
        username="admin",
        email="admin@example.com",
        password="adminpass123",
    )
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def language(db):
    """Create a test language."""
    from apps.telegram_channels.models import Language

    return Language.objects.create(
        code="en",
        name="English",
        native_name="English",
        is_default=True,
        is_active=True,
    )


@pytest.fixture
def language_ru(db):
    """Create a Russian language."""
    from apps.telegram_channels.models import Language

    return Language.objects.create(
        code="ru",
        name="Russian",
        native_name="Русский",
        is_default=False,
        is_active=True,
    )


@pytest.fixture
def channel_group(db):
    """Create a test channel group."""
    from apps.telegram_channels.models import ChannelGroup

    return ChannelGroup.objects.create(
        name="Test Group",
        description="Test channel group",
        is_active=True,
    )


@pytest.fixture
def channel(db, channel_group, language):
    """Create a test channel."""
    from apps.telegram_channels.models import Channel

    return Channel.objects.create(
        group=channel_group,
        telegram_chat_id="-1001234567890",
        title="Test Channel EN",
        username="testchannel_en",
        language=language,
        is_primary=True,
        is_active=True,
        bot_admin=True,
        bot_can_post=True,
        bot_can_read=True,
        member_count=1000,
    )


@pytest.fixture
def channel_ru(db, channel_group, language_ru):
    """Create a Russian test channel."""
    from apps.telegram_channels.models import Channel

    return Channel.objects.create(
        group=channel_group,
        telegram_chat_id="-1001234567891",
        title="Test Channel RU",
        username="testchannel_ru",
        language=language_ru,
        is_primary=False,
        is_active=True,
        bot_admin=True,
        bot_can_post=True,
        bot_can_read=True,
        member_count=500,
    )


@pytest.fixture
def multi_post(db, channel_group, channel):
    """Create a test multi-channel post."""
    from apps.posts.models import MultiChannelPost

    return MultiChannelPost.objects.create(
        group=channel_group,
        internal_title="Test Post",
        primary_channel=channel,
        primary_text_markdown="**Test** post content",
        auto_translate_enabled=True,
    )

