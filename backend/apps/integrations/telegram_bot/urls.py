"""Telegram Bot integration URL configuration."""

from django.urls import path

from .views import (
    channel_stats_webhook,
    channel_update_webhook,
    message_stats_webhook,
)

app_name = "telegram_bot"

urlpatterns = [
    path("channel-stats/", channel_stats_webhook, name="channel-stats"),
    path("message-stats/", message_stats_webhook, name="message-stats"),
    path("channel-update/", channel_update_webhook, name="channel-update"),
]

