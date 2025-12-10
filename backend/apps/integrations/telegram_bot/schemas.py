"""Pydantic schemas for Telegram Bot Gateway integration.

Based on actual Telegram Bot Gateway API documentation.
API Version: v1
"""

from datetime import datetime
from typing import Any, Optional, Union

from pydantic import BaseModel, Field


# ============== Request Schemas ==============


class SendMessageRequest(BaseModel):
    """Request to send a message to a channel."""

    chat_id: Union[int, str] = Field(..., description="ID канала или @username")
    text: str = Field(..., description="Текст сообщения (1-4096 символов)")
    photo_url: Optional[str] = Field(None, description="URL фото для отправки")
    parse_mode: str = Field(
        default="HTML",
        description="Режим парсинга: HTML, Markdown, MarkdownV2",
    )
    disable_web_page_preview: bool = Field(default=False, description="Отключить превью ссылок")
    disable_notification: bool = Field(default=False, description="Отправить без звука")


class EditMessageRequest(BaseModel):
    """Request to edit an existing message."""

    chat_id: Union[int, str] = Field(..., description="ID канала")
    message_id: int = Field(..., description="ID сообщения для редактирования")
    text: str = Field(..., description="Новый текст (1-4096 символов)")
    parse_mode: str = Field(default="HTML", description="Режим парсинга")
    disable_web_page_preview: bool = Field(default=False)


class DeleteMessageRequest(BaseModel):
    """Request to delete a message."""

    chat_id: Union[int, str] = Field(..., description="ID канала")
    message_id: int = Field(..., description="ID сообщения для удаления")


class BatchMessageStatsRequest(BaseModel):
    """Request to get stats for multiple messages."""

    messages: list[dict] = Field(
        ...,
        description="Массив сообщений (1-100 элементов)",
        min_length=1,
        max_length=100,
    )


# ============== Response Schemas ==============


class PhotoInfo(BaseModel):
    """Photo information from channel."""

    small_file_id: Optional[str] = None
    big_file_id: Optional[str] = None
    small_file_url: Optional[str] = None
    big_file_url: Optional[str] = None


class SendMessageResponse(BaseModel):
    """Response from sending a message."""

    success: bool
    chat_id: Optional[Union[int, str]] = None
    message_id: Optional[int] = None
    date: Optional[datetime] = None
    text: Optional[str] = None
    raw: Optional[dict] = None
    # Error fields
    code: Optional[str] = None
    error: Optional[str] = None
    details: Optional[dict] = None


class EditMessageResponse(BaseModel):
    """Response from editing a message."""

    success: bool
    chat_id: Optional[Union[int, str]] = None
    message_id: Optional[int] = None
    text: Optional[str] = None
    raw: Optional[dict] = None
    # Error fields
    code: Optional[str] = None
    error: Optional[str] = None
    details: Optional[dict] = None


class DeleteMessageResponse(BaseModel):
    """Response from deleting a message."""

    success: bool
    chat_id: Optional[Union[int, str]] = None
    message_id: Optional[int] = None
    # Error fields
    code: Optional[str] = None
    error: Optional[str] = None
    details: Optional[dict] = None


class ChannelInfoResponse(BaseModel):
    """Response with channel information."""

    success: bool
    chat_id: Optional[Union[int, str]] = None
    title: Optional[str] = None
    username: Optional[str] = None
    description: Optional[str] = None
    invite_link: Optional[str] = None
    photo: Optional[PhotoInfo] = None
    member_count: Optional[int] = None
    linked_chat_id: Optional[int] = None
    type: Optional[str] = None
    raw: Optional[dict] = None
    # Error fields
    code: Optional[str] = None
    error: Optional[str] = None
    details: Optional[dict] = None


class BotPermissionsResponse(BaseModel):
    """Response with bot permissions in a channel."""

    success: bool
    chat_id: Optional[Union[int, str]] = None
    is_member: bool = False
    is_admin: bool = False
    can_post_messages: bool = False
    can_edit_messages: bool = False
    can_delete_messages: bool = False
    can_restrict_members: bool = False
    can_invite_users: bool = False
    can_pin_messages: bool = False
    can_manage_chat: bool = False
    status: Optional[str] = None
    raw: Optional[dict] = None
    # Error fields
    code: Optional[str] = None
    error: Optional[str] = None
    details: Optional[dict] = None


class MessageStatsResponse(BaseModel):
    """Response with message statistics.
    
    Note: Telegram Bot API не предоставляет детальную статистику сообщений.
    Для получения полной статистики используйте MTProto API.
    """

    success: bool
    chat_id: Optional[Union[int, str]] = None
    message_id: Optional[int] = None
    views: Optional[int] = None
    forwards: Optional[int] = None
    reactions: Optional[dict] = None
    reply_count: Optional[int] = None
    date: Optional[datetime] = None
    raw: Optional[dict] = None
    # Error fields
    code: Optional[str] = None
    error: Optional[str] = None
    details: Optional[dict] = None


class BatchMessageStatsResponse(BaseModel):
    """Response with batch message statistics."""

    success: bool
    results: list[dict] = Field(default_factory=list)
    errors: list[dict] = Field(default_factory=list)


class ChannelStatsResponse(BaseModel):
    """Response with channel statistics.
    
    Note: Telegram Bot API предоставляет только количество подписчиков.
    Для ERR, ER и детальной аналитики используйте Telegram Analytics API.
    """

    success: bool
    chat_id: Optional[Union[int, str]] = None
    member_count: int = 0
    title: Optional[str] = None
    raw: Optional[dict] = None
    # Error fields
    code: Optional[str] = None
    error: Optional[str] = None
    details: Optional[dict] = None


# ============== Bot Management Schemas ==============


class BotInfoResponse(BaseModel):
    """Response with bot information."""

    success: bool
    bot_id: Optional[int] = None
    username: Optional[str] = None
    first_name: Optional[str] = None
    can_join_groups: bool = False
    can_read_all_group_messages: bool = False
    supports_inline_queries: bool = False
    # Error fields
    code: Optional[str] = None
    error: Optional[str] = None


class WebhookInfoResponse(BaseModel):
    """Response with webhook configuration."""

    success: bool
    url: Optional[str] = None
    has_custom_certificate: bool = False
    pending_update_count: int = 0
    max_connections: int = 40
    allowed_updates: list[str] = Field(default_factory=list)
    # Error fields
    code: Optional[str] = None
    error: Optional[str] = None


class WebhookSetResponse(BaseModel):
    """Response from setting webhook."""

    success: bool
    message: Optional[str] = None
    url: Optional[str] = None
    # Error fields
    code: Optional[str] = None
    error: Optional[str] = None


class WebhookDeleteResponse(BaseModel):
    """Response from deleting webhook."""

    success: bool
    message: Optional[str] = None
    # Error fields
    code: Optional[str] = None
    error: Optional[str] = None


class BotUpdatesResponse(BaseModel):
    """Response with bot updates (long polling)."""

    success: bool
    count: int = 0
    updates: list[dict] = Field(default_factory=list)
    # Error fields
    code: Optional[str] = None
    error: Optional[str] = None


class ProcessUpdatesResponse(BaseModel):
    """Response from processing updates."""

    success: bool
    processed: int = 0
    results: list[dict] = Field(default_factory=list)
    # Error fields
    code: Optional[str] = None
    error: Optional[str] = None


# ============== Webhook Payload Schemas (from Gateway to Backend) ==============


class BotEventPermissions(BaseModel):
    """Bot permissions in the event payload."""

    can_post_messages: bool = False
    can_edit_messages: bool = False
    can_delete_messages: bool = False
    can_restrict_members: bool = False
    can_invite_users: bool = False
    can_pin_messages: bool = False
    can_manage_chat: bool = False


class BotEventPayload(BaseModel):
    """Webhook payload for bot events (added/removed from channel).
    
    Events:
    - bot_added: Бот добавлен как администратор
    - bot_removed: Бот удалён из канала/группы
    - bot_permissions_changed: Права бота изменены
    """

    event: str = Field(..., description="Тип события: bot_added, bot_removed, bot_permissions_changed")
    chat_id: int = Field(..., description="ID канала/группы")
    chat_title: Optional[str] = None
    chat_username: Optional[str] = None
    chat_type: Optional[str] = None
    old_status: Optional[str] = None
    new_status: Optional[str] = None
    permissions: Optional[BotEventPermissions] = None


class ChannelStatsWebhook(BaseModel):
    """Webhook payload for channel stats update from bot service."""

    chat_id: Union[int, str]
    member_count: int
    title: Optional[str] = None


class MessageStatsWebhook(BaseModel):
    """Webhook payload for message stats update from bot service."""

    chat_id: Union[int, str]
    message_id: int
    views: Optional[int] = None
    forwards: Optional[int] = None


class ChannelUpdateWebhook(BaseModel):
    """Webhook payload for channel info update from bot service."""

    chat_id: Union[int, str]
    title: Optional[str] = None
    username: Optional[str] = None
    description: Optional[str] = None


# ============== Error Response ==============


class ErrorResponse(BaseModel):
    """Standard error response format."""

    code: str = Field(..., description="Код ошибки")
    error: str = Field(..., description="Человекочитаемое описание ошибки")
    details: dict = Field(default_factory=dict, description="Дополнительные детали")


# Error codes
# ============== MTProto Statistics API (Detailed Stats) ==============


class MTProtoStatusResponse(BaseModel):
    """Response with MTProto API status."""

    enabled: bool = False
    available: bool = False
    connected: bool = False
    has_api_id: bool = False
    has_api_hash: bool = False
    has_session: bool = False


class ChannelDetailedInfo(BaseModel):
    """Detailed channel information from MTProto."""

    chat_id: int
    title: str
    username: Optional[str] = None
    participants_count: int = 0
    admins_count: int = 0
    online_count: int = 0
    about: Optional[str] = None
    is_verified: bool = False
    is_megagroup: bool = False
    is_broadcast: bool = True
    can_view_stats: bool = False


class GrowthStats(BaseModel):
    """Growth statistics for a channel."""

    period: dict = Field(
        default_factory=dict,
        description="Period with min_date and max_date",
    )
    followers: dict = Field(
        default_factory=dict,
        description="Current and previous follower counts",
    )
    views_per_post: dict = Field(
        default_factory=dict,
        description="Current and previous views per post",
    )


class DetailedChannelStatsResponse(BaseModel):
    """Detailed channel statistics from MTProto API."""

    success: bool
    channel: Optional[ChannelDetailedInfo] = None
    growth_stats: Optional[GrowthStats] = None
    # Error fields
    code: Optional[str] = None
    error: Optional[str] = None
    details: Optional[dict] = None


class MessageReaction(BaseModel):
    """Single reaction on a message."""

    emoji: str
    count: int


class MessageReactions(BaseModel):
    """Reactions breakdown for a message."""

    total_count: int = 0
    reactions: list[MessageReaction] = Field(default_factory=list)


class DetailedMessageStatsResponse(BaseModel):
    """Detailed message statistics from MTProto API."""

    success: bool
    chat_id: Optional[int] = None
    message_id: Optional[int] = None
    views: Optional[int] = None
    forwards: Optional[int] = None
    replies: Optional[int] = None
    reactions: Optional[MessageReactions] = None
    date: Optional[datetime] = None
    pinned: bool = False
    # Error fields
    code: Optional[str] = None
    error: Optional[str] = None
    details: Optional[dict] = None


class BatchMessageDetailedStats(BaseModel):
    """Single message stats in batch response."""

    message_id: int
    views: int = 0
    forwards: int = 0
    replies: int = 0
    reactions: MessageReactions = Field(default_factory=MessageReactions)


class BatchDetailedStatsResponse(BaseModel):
    """Batch detailed statistics response."""

    success: bool
    chat_id: int
    count: int = 0
    messages: list[BatchMessageDetailedStats] = Field(default_factory=list)
    # Error fields
    code: Optional[str] = None
    error: Optional[str] = None
    details: Optional[dict] = None


class RecentPostStats(BaseModel):
    """Statistics for a single post in recent posts list."""

    message_id: int
    text: Optional[str] = None
    has_media: bool = False
    views: int = 0
    forwards: int = 0
    replies: int = 0
    reactions_count: int = 0
    date: datetime
    pinned: bool = False


class RecentPostsStatsResponse(BaseModel):
    """Recent posts statistics response."""

    success: bool
    chat_id: int
    count: int = 0
    totals: dict = Field(
        default_factory=dict,
        description="Total views, forwards, reactions, replies",
    )
    average: dict = Field(
        default_factory=dict,
        description="Average views, forwards, reactions, replies per post",
    )
    posts: list[RecentPostStats] = Field(default_factory=list)
    # Error fields
    code: Optional[str] = None
    error: Optional[str] = None
    details: Optional[dict] = None


class MTProtoConnectResponse(BaseModel):
    """Response from MTProto connection attempt."""

    success: bool
    connected: bool = False
    message: Optional[str] = None
    # Error fields
    code: Optional[str] = None
    error: Optional[str] = None


# ============== Error Codes ==============


class ErrorCodes:
    """Error codes from Telegram Bot Gateway."""

    UNAUTHORIZED = "UNAUTHORIZED"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_CHAT_ID = "INVALID_CHAT_ID"
    INVALID_MESSAGE_ID = "INVALID_MESSAGE_ID"
    BOT_NOT_ADMIN = "BOT_NOT_ADMIN"
    BOT_CANNOT_POST = "BOT_CANNOT_POST"
    TELEGRAM_RATE_LIMIT = "TELEGRAM_RATE_LIMIT"
    TELEGRAM_UNAVAILABLE = "TELEGRAM_UNAVAILABLE"
    TELEGRAM_BAD_REQUEST = "TELEGRAM_BAD_REQUEST"
    TIMEOUT = "TIMEOUT"
    IDEMPOTENCY_CONFLICT = "IDEMPOTENCY_CONFLICT"
    INTERNAL_ERROR = "INTERNAL_ERROR"
