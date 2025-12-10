"""Pydantic schemas for Telegram Bot integration."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ============== Request Schemas ==============


class SendMessageRequest(BaseModel):
    """Request to send a message to a channel."""

    chat_id: str = Field(..., description="Telegram chat ID")
    text: str = Field(..., description="Message text (HTML or MarkdownV2)")
    parse_mode: str = Field(default="HTML", description="Parse mode: HTML or MarkdownV2")
    photo_url: Optional[str] = Field(None, description="URL to photo to attach")
    disable_web_page_preview: bool = Field(default=False)
    disable_notification: bool = Field(default=False)
    reply_markup: Optional[dict] = Field(None, description="Inline keyboard markup")


class EditMessageRequest(BaseModel):
    """Request to edit an existing message."""

    chat_id: str
    message_id: str
    text: str
    parse_mode: str = "HTML"
    disable_web_page_preview: bool = False
    reply_markup: Optional[dict] = None


class DeleteMessageRequest(BaseModel):
    """Request to delete a message."""

    chat_id: str
    message_id: str


class GetChannelInfoRequest(BaseModel):
    """Request to get channel information."""

    chat_id: str


class GetMessageStatsRequest(BaseModel):
    """Request to get message statistics."""

    chat_id: str
    message_id: str


class VerifyBotPermissionsRequest(BaseModel):
    """Request to verify bot permissions in a channel."""

    chat_id: str


# ============== Response Schemas ==============


class SendMessageResponse(BaseModel):
    """Response from sending a message."""

    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None
    raw_response: Optional[dict] = None


class EditMessageResponse(BaseModel):
    """Response from editing a message."""

    success: bool
    error: Optional[str] = None


class DeleteMessageResponse(BaseModel):
    """Response from deleting a message."""

    success: bool
    error: Optional[str] = None


class ChannelInfoResponse(BaseModel):
    """Response with channel information."""

    success: bool
    chat_id: Optional[str] = None
    title: Optional[str] = None
    username: Optional[str] = None
    description: Optional[str] = None
    member_count: Optional[int] = None
    photo_url: Optional[str] = None
    invite_link: Optional[str] = None
    error: Optional[str] = None
    raw_response: Optional[dict] = None


class BotPermissionsResponse(BaseModel):
    """Response with bot permissions in a channel."""

    success: bool
    is_admin: bool = False
    can_post_messages: bool = False
    can_edit_messages: bool = False
    can_delete_messages: bool = False
    can_read_messages: bool = False
    error: Optional[str] = None


class MessageStatsResponse(BaseModel):
    """Response with message statistics."""

    success: bool
    views: int = 0
    forwards: int = 0
    reactions_count: int = 0
    reactions: dict = Field(default_factory=dict)  # emoji -> count
    comments: int = 0
    error: Optional[str] = None
    raw_response: Optional[dict] = None


class ChannelStatsResponse(BaseModel):
    """Response with channel statistics."""

    success: bool
    member_count: int = 0
    views_last_10_posts: int = 0
    avg_views_per_post: float = 0
    er: float = 0
    err: float = 0
    total_posts: int = 0
    posts_last_24h: int = 0
    posts_last_7d: int = 0
    error: Optional[str] = None
    raw_response: Optional[dict] = None


# ============== Webhook Payload Schemas ==============


class ChannelStatsWebhook(BaseModel):
    """Webhook payload for channel stats update from bot service."""

    chat_id: str
    timestamp: datetime
    member_count: int
    views_last_10_posts: int = 0
    avg_views_per_post: float = 0
    er: float = 0
    err: float = 0
    total_posts: int = 0
    posts_last_24h: int = 0
    posts_last_7d: int = 0
    extra: dict = Field(default_factory=dict)


class MessageStatsWebhook(BaseModel):
    """Webhook payload for message stats update from bot service."""

    chat_id: str
    message_id: str
    timestamp: datetime
    views: int = 0
    forwards: int = 0
    reactions_count: int = 0
    reactions: dict = Field(default_factory=dict)
    comments: int = 0
    extra: dict = Field(default_factory=dict)


class ChannelUpdateWebhook(BaseModel):
    """Webhook payload for channel info update from bot service."""

    chat_id: str
    title: str
    username: Optional[str] = None
    description: Optional[str] = None
    member_count: int = 0
    photo_url: Optional[str] = None
    invite_link: Optional[str] = None
    is_admin: bool = False
    can_post_messages: bool = False
    can_edit_messages: bool = False
    can_delete_messages: bool = False
    extra: dict = Field(default_factory=dict)

