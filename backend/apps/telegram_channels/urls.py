"""Telegram Channels URL configuration."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ChannelGroupViewSet, ChannelViewSet, LanguageViewSet

app_name = "telegram_channels"

router = DefaultRouter()
router.register(r"languages", LanguageViewSet, basename="language")
router.register(r"groups", ChannelGroupViewSet, basename="channelgroup")
router.register(r"", ChannelViewSet, basename="channel")

urlpatterns = [
    path("", include(router.urls)),
]

