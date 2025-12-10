"""Telegram Bot integration URL configuration.

Webhook endpoints for receiving updates from Telegram Bot Gateway:
- /bot-events/ - Bot membership events (added/removed from channels)
- /channel-stats/ - Channel statistics updates
- /message-stats/ - Message statistics updates
- /channel-update/ - Channel information updates
"""

from django.urls import path

from .views import (
    bot_events_webhook,
    channel_stats_webhook,
    channel_update_webhook,
    message_stats_webhook,
)

app_name = "telegram_bot"

urlpatterns = [
    # Bot events (new endpoint from actual API)
    path("bot-events/", bot_events_webhook, name="bot-events"),
    
    # Legacy webhook endpoints
    path("channel-stats/", channel_stats_webhook, name="channel-stats"),
    path("message-stats/", message_stats_webhook, name="message-stats"),
    path("channel-update/", channel_update_webhook, name="channel-update"),
]
