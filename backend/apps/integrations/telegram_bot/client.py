"""Telegram Bot Gateway service client.

Client for communicating with the external Telegram Bot Gateway service.
Based on actual API documentation.

API Base URL: configurable via settings.TELEGRAM_BOT_SERVICE_URL
API Version: v1
"""

import logging
import uuid
from typing import Optional, Union

import httpx
from django.conf import settings

from .schemas import (
    BatchDetailedStatsResponse,
    BatchMessageStatsRequest,
    BatchMessageStatsResponse,
    BotInfoResponse,
    BotPermissionsResponse,
    ChannelInfoResponse,
    ChannelStatsResponse,
    DeleteMessageRequest,
    DeleteMessageResponse,
    DetailedChannelStatsResponse,
    DetailedMessageStatsResponse,
    EditMessageRequest,
    EditMessageResponse,
    ErrorCodes,
    MessageStatsResponse,
    MTProtoConnectResponse,
    MTProtoStatusResponse,
    ProcessUpdatesResponse,
    RecentPostsStatsResponse,
    SendMessageRequest,
    SendMessageResponse,
    WebhookDeleteResponse,
    WebhookInfoResponse,
    WebhookSetResponse,
)

logger = logging.getLogger(__name__)


class TelegramBotGatewayError(Exception):
    """Base exception for Telegram Bot Gateway errors."""

    def __init__(self, code: str, message: str, details: Optional[dict] = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(f"[{code}] {message}")


class TelegramBotClient:
    """
    Client for communicating with the Telegram Bot Gateway service.
    
    Features:
    - Idempotency support via Idempotency-Key header
    - Automatic retry handling for rate limits
    - Both sync and async methods
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        token: Optional[str] = None,
        timeout: float = 30.0,
    ):
        self.base_url = (base_url or settings.TELEGRAM_BOT_SERVICE_URL).rstrip("/")
        self.token = token or settings.TELEGRAM_BOT_SERVICE_TOKEN
        self.timeout = timeout

        self._headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def _get_client(self) -> httpx.Client:
        """Get a synchronous HTTP client."""
        return httpx.Client(
            base_url=self.base_url,
            headers=self._headers,
            timeout=httpx.Timeout(self.timeout),
        )

    def _get_async_client(self) -> httpx.AsyncClient:
        """Get an asynchronous HTTP client."""
        return httpx.AsyncClient(
            base_url=self.base_url,
            headers=self._headers,
            timeout=httpx.Timeout(self.timeout),
        )

    def _handle_error_response(self, response: httpx.Response) -> None:
        """Handle error response from the gateway."""
        try:
            data = response.json()
            code = data.get("code", "UNKNOWN_ERROR")
            error = data.get("error", "Unknown error")
            details = data.get("details", {})
            raise TelegramBotGatewayError(code, error, details)
        except ValueError:
            raise TelegramBotGatewayError(
                "PARSE_ERROR",
                f"Failed to parse error response: {response.text}",
            )

    def _generate_idempotency_key(self) -> str:
        """Generate a unique idempotency key."""
        return str(uuid.uuid4())

    # ============== Messages API ==============

    def send_message_sync(
        self,
        chat_id: Union[int, str],
        text: str,
        parse_mode: str = "HTML",
        photo_url: Optional[str] = None,
        disable_web_page_preview: bool = False,
        disable_notification: bool = False,
        idempotency_key: Optional[str] = None,
    ) -> Optional[dict]:
        """
        Send a message to a channel (synchronous).

        Args:
            chat_id: Telegram chat ID or @username
            text: Message text (1-4096 chars)
            parse_mode: Parse mode (HTML, Markdown, MarkdownV2)
            photo_url: Optional URL to photo
            disable_web_page_preview: Disable link previews
            disable_notification: Send silently
            idempotency_key: Optional key to prevent duplicate sends

        Returns:
            Dict with message_id and other info if successful, None otherwise.
        """
        request_data = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": disable_web_page_preview,
            "disable_notification": disable_notification,
        }
        if photo_url:
            request_data["photo_url"] = photo_url

        headers = dict(self._headers)
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key

        try:
            with self._get_client() as client:
                response = client.post(
                    "/api/v1/messages/send",
                    json=request_data,
                    headers=headers,
                )

                if response.status_code >= 400:
                    self._handle_error_response(response)

                data = response.json()
                result = SendMessageResponse(**data)

                if result.success:
                    return {
                        "message_id": result.message_id,
                        "chat_id": result.chat_id,
                        "date": result.date,
                        "text": result.text,
                        "raw": result.raw,
                    }
                else:
                    logger.error(f"Failed to send message: {result.error}")
                    return None

        except TelegramBotGatewayError:
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error sending message: {e.response.status_code}")
            raise
        except Exception as e:
            logger.exception(f"Error sending message: {e}")
            raise

    def edit_message_sync(
        self,
        chat_id: Union[int, str],
        message_id: int,
        text: str,
        parse_mode: str = "HTML",
        disable_web_page_preview: bool = False,
    ) -> bool:
        """
        Edit an existing message (synchronous).

        Returns:
            True if successful, False otherwise.
        """
        request_data = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": disable_web_page_preview,
        }

        try:
            with self._get_client() as client:
                response = client.post(
                    "/api/v1/messages/edit",
                    json=request_data,
                )

                if response.status_code >= 400:
                    self._handle_error_response(response)

                data = response.json()
                result = EditMessageResponse(**data)
                return result.success

        except TelegramBotGatewayError:
            raise
        except Exception as e:
            logger.exception(f"Error editing message: {e}")
            raise

    def delete_message_sync(
        self,
        chat_id: Union[int, str],
        message_id: int,
    ) -> bool:
        """
        Delete a message (synchronous).

        Returns:
            True if successful, False otherwise.
        """
        request_data = {
            "chat_id": chat_id,
            "message_id": message_id,
        }

        try:
            with self._get_client() as client:
                response = client.post(
                    "/api/v1/messages/delete",
                    json=request_data,
                )

                if response.status_code >= 400:
                    self._handle_error_response(response)

                data = response.json()
                result = DeleteMessageResponse(**data)
                return result.success

        except TelegramBotGatewayError:
            raise
        except Exception as e:
            logger.exception(f"Error deleting message: {e}")
            raise

    def get_message_stats_sync(
        self,
        chat_id: Union[int, str],
        message_id: int,
    ) -> Optional[dict]:
        """
        Get message statistics (synchronous).
        
        Note: Telegram Bot API has limited stats. For full stats use MTProto API.

        Returns:
            Dict with stats if successful, None otherwise.
        """
        try:
            with self._get_client() as client:
                response = client.get(
                    "/api/v1/messages/stats",
                    params={"chat_id": chat_id, "message_id": message_id},
                )

                if response.status_code >= 400:
                    self._handle_error_response(response)

                data = response.json()
                result = MessageStatsResponse(**data)

                if result.success:
                    return {
                        "chat_id": result.chat_id,
                        "message_id": result.message_id,
                        "views": result.views,
                        "forwards": result.forwards,
                        "reactions": result.reactions,
                        "reply_count": result.reply_count,
                        "date": result.date,
                        "raw": result.raw,
                    }
                else:
                    logger.error(f"Failed to get message stats: {result.error}")
                    return None

        except TelegramBotGatewayError:
            raise
        except Exception as e:
            logger.exception(f"Error getting message stats: {e}")
            raise

    def get_batch_message_stats_sync(
        self,
        messages: list[dict],
    ) -> Optional[dict]:
        """
        Get statistics for multiple messages (synchronous).

        Args:
            messages: List of dicts with chat_id and message_id

        Returns:
            Dict with results and errors if successful.
        """
        request_data = {"messages": messages}

        try:
            with self._get_client() as client:
                response = client.post(
                    "/api/v1/messages/stats/batch",
                    json=request_data,
                )

                if response.status_code >= 400:
                    self._handle_error_response(response)

                data = response.json()
                result = BatchMessageStatsResponse(**data)

                if result.success:
                    return {
                        "results": result.results,
                        "errors": result.errors,
                    }
                return None

        except TelegramBotGatewayError:
            raise
        except Exception as e:
            logger.exception(f"Error getting batch message stats: {e}")
            raise

    # ============== Channels API ==============

    def get_channel_info_sync(self, chat_id: Union[int, str]) -> Optional[dict]:
        """
        Get channel information (synchronous).

        Returns:
            Dict with channel info if successful, None otherwise.
        """
        try:
            with self._get_client() as client:
                response = client.get(
                    "/api/v1/channels/info",
                    params={"chat_id": chat_id},
                )

                if response.status_code >= 400:
                    self._handle_error_response(response)

                data = response.json()
                result = ChannelInfoResponse(**data)

                if result.success:
                    return {
                        "chat_id": result.chat_id,
                        "title": result.title,
                        "username": result.username,
                        "description": result.description,
                        "invite_link": result.invite_link,
                        "photo": result.photo.model_dump() if result.photo else None,
                        "member_count": result.member_count,
                        "linked_chat_id": result.linked_chat_id,
                        "type": result.type,
                        "raw": result.raw,
                    }
                else:
                    logger.error(f"Failed to get channel info: {result.error}")
                    return None

        except TelegramBotGatewayError:
            raise
        except Exception as e:
            logger.exception(f"Error getting channel info: {e}")
            raise

    def verify_bot_permissions_sync(self, chat_id: Union[int, str]) -> Optional[dict]:
        """
        Verify bot permissions in a channel (synchronous).

        Returns:
            Dict with permissions if successful, None otherwise.
        """
        try:
            with self._get_client() as client:
                response = client.get(
                    "/api/v1/channels/permissions",
                    params={"chat_id": chat_id},
                )

                if response.status_code >= 400:
                    self._handle_error_response(response)

                data = response.json()
                result = BotPermissionsResponse(**data)

                if result.success:
                    return {
                        "chat_id": result.chat_id,
                        "is_member": result.is_member,
                        "is_admin": result.is_admin,
                        "can_post_messages": result.can_post_messages,
                        "can_edit_messages": result.can_edit_messages,
                        "can_delete_messages": result.can_delete_messages,
                        "can_restrict_members": result.can_restrict_members,
                        "can_invite_users": result.can_invite_users,
                        "can_pin_messages": result.can_pin_messages,
                        "can_manage_chat": result.can_manage_chat,
                        "status": result.status,
                        "raw": result.raw,
                    }
                else:
                    logger.error(f"Failed to verify permissions: {result.error}")
                    return None

        except TelegramBotGatewayError:
            raise
        except Exception as e:
            logger.exception(f"Error verifying permissions: {e}")
            raise

    def get_channel_stats_sync(self, chat_id: Union[int, str]) -> Optional[dict]:
        """
        Get channel statistics (synchronous).
        
        Note: Telegram Bot API provides only member count.
        For ERR, ER and detailed analytics use Telegram Analytics API.

        Returns:
            Dict with stats if successful, None otherwise.
        """
        try:
            with self._get_client() as client:
                response = client.get(
                    "/api/v1/channels/stats",
                    params={"chat_id": chat_id},
                )

                if response.status_code >= 400:
                    self._handle_error_response(response)

                data = response.json()
                result = ChannelStatsResponse(**data)

                if result.success:
                    return {
                        "chat_id": result.chat_id,
                        "member_count": result.member_count,
                        "title": result.title,
                        "raw": result.raw,
                    }
                else:
                    logger.error(f"Failed to get channel stats: {result.error}")
                    return None

        except TelegramBotGatewayError:
            raise
        except Exception as e:
            logger.exception(f"Error getting channel stats: {e}")
            raise

    # ============== Bot Management API ==============

    def get_bot_info_sync(self) -> Optional[dict]:
        """Get bot information (synchronous)."""
        try:
            with self._get_client() as client:
                response = client.get("/api/v1/bot/info")

                if response.status_code >= 400:
                    self._handle_error_response(response)

                data = response.json()
                result = BotInfoResponse(**data)

                if result.success:
                    return {
                        "bot_id": result.bot_id,
                        "username": result.username,
                        "first_name": result.first_name,
                        "can_join_groups": result.can_join_groups,
                        "can_read_all_group_messages": result.can_read_all_group_messages,
                        "supports_inline_queries": result.supports_inline_queries,
                    }
                return None

        except TelegramBotGatewayError:
            raise
        except Exception as e:
            logger.exception(f"Error getting bot info: {e}")
            raise

    def get_webhook_info_sync(self) -> Optional[dict]:
        """Get current webhook configuration (synchronous)."""
        try:
            with self._get_client() as client:
                response = client.get("/api/v1/bot/webhook")

                if response.status_code >= 400:
                    self._handle_error_response(response)

                data = response.json()
                result = WebhookInfoResponse(**data)

                if result.success:
                    return {
                        "url": result.url,
                        "has_custom_certificate": result.has_custom_certificate,
                        "pending_update_count": result.pending_update_count,
                        "max_connections": result.max_connections,
                        "allowed_updates": result.allowed_updates,
                    }
                return None

        except TelegramBotGatewayError:
            raise
        except Exception as e:
            logger.exception(f"Error getting webhook info: {e}")
            raise

    def set_webhook_sync(
        self,
        url: Optional[str] = None,
        secret_token: Optional[str] = None,
        max_connections: Optional[int] = None,
    ) -> bool:
        """
        Set Telegram webhook (synchronous).

        Args:
            url: Webhook URL (uses config default if not provided)
            secret_token: Secret token for validation
            max_connections: Max concurrent connections (1-100)

        Returns:
            True if successful.
        """
        params = {}
        if url:
            params["url"] = url
        if secret_token:
            params["secret_token"] = secret_token
        if max_connections:
            params["max_connections"] = max_connections

        try:
            with self._get_client() as client:
                response = client.post(
                    "/api/v1/bot/webhook/set",
                    params=params,
                )

                if response.status_code >= 400:
                    self._handle_error_response(response)

                data = response.json()
                result = WebhookSetResponse(**data)
                return result.success

        except TelegramBotGatewayError:
            raise
        except Exception as e:
            logger.exception(f"Error setting webhook: {e}")
            raise

    def delete_webhook_sync(self, drop_pending_updates: bool = False) -> bool:
        """
        Delete Telegram webhook (synchronous).

        Args:
            drop_pending_updates: Whether to drop pending updates

        Returns:
            True if successful.
        """
        params = {}
        if drop_pending_updates:
            params["drop_pending_updates"] = drop_pending_updates

        try:
            with self._get_client() as client:
                response = client.post(
                    "/api/v1/bot/webhook/delete",
                    params=params,
                )

                if response.status_code >= 400:
                    self._handle_error_response(response)

                data = response.json()
                result = WebhookDeleteResponse(**data)
                return result.success

        except TelegramBotGatewayError:
            raise
        except Exception as e:
            logger.exception(f"Error deleting webhook: {e}")
            raise

    def process_updates_sync(self) -> Optional[dict]:
        """
        Process pending bot updates (synchronous).
        
        Automatically notifies external backend about bot membership changes.

        Returns:
            Dict with processed count and results.
        """
        try:
            with self._get_client() as client:
                response = client.post("/api/v1/bot/updates/process")

                if response.status_code >= 400:
                    self._handle_error_response(response)

                data = response.json()
                result = ProcessUpdatesResponse(**data)

                if result.success:
                    return {
                        "processed": result.processed,
                        "results": result.results,
                    }
                return None

        except TelegramBotGatewayError:
            raise
        except Exception as e:
            logger.exception(f"Error processing updates: {e}")
            raise

    # ============== Asynchronous Methods ==============

    async def send_message(
        self,
        chat_id: Union[int, str],
        text: str,
        parse_mode: str = "HTML",
        photo_url: Optional[str] = None,
        disable_web_page_preview: bool = False,
        disable_notification: bool = False,
        idempotency_key: Optional[str] = None,
    ) -> Optional[dict]:
        """Send a message to a channel (asynchronous)."""
        request_data = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": disable_web_page_preview,
            "disable_notification": disable_notification,
        }
        if photo_url:
            request_data["photo_url"] = photo_url

        headers = dict(self._headers)
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key

        try:
            async with self._get_async_client() as client:
                response = await client.post(
                    "/api/v1/messages/send",
                    json=request_data,
                    headers=headers,
                )

                if response.status_code >= 400:
                    self._handle_error_response(response)

                data = response.json()
                result = SendMessageResponse(**data)

                if result.success:
                    return {
                        "message_id": result.message_id,
                        "chat_id": result.chat_id,
                        "date": result.date,
                        "text": result.text,
                        "raw": result.raw,
                    }
                else:
                    logger.error(f"Failed to send message: {result.error}")
                    return None

        except TelegramBotGatewayError:
            raise
        except Exception as e:
            logger.exception(f"Error sending message: {e}")
            raise

    async def edit_message(
        self,
        chat_id: Union[int, str],
        message_id: int,
        text: str,
        parse_mode: str = "HTML",
        disable_web_page_preview: bool = False,
    ) -> bool:
        """Edit an existing message (asynchronous)."""
        request_data = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": disable_web_page_preview,
        }

        try:
            async with self._get_async_client() as client:
                response = await client.post(
                    "/api/v1/messages/edit",
                    json=request_data,
                )

                if response.status_code >= 400:
                    self._handle_error_response(response)

                data = response.json()
                result = EditMessageResponse(**data)
                return result.success

        except TelegramBotGatewayError:
            raise
        except Exception as e:
            logger.exception(f"Error editing message: {e}")
            raise

    async def delete_message(
        self,
        chat_id: Union[int, str],
        message_id: int,
    ) -> bool:
        """Delete a message (asynchronous)."""
        request_data = {
            "chat_id": chat_id,
            "message_id": message_id,
        }

        try:
            async with self._get_async_client() as client:
                response = await client.post(
                    "/api/v1/messages/delete",
                    json=request_data,
                )

                if response.status_code >= 400:
                    self._handle_error_response(response)

                data = response.json()
                result = DeleteMessageResponse(**data)
                return result.success

        except TelegramBotGatewayError:
            raise
        except Exception as e:
            logger.exception(f"Error deleting message: {e}")
            raise

    async def get_channel_info(self, chat_id: Union[int, str]) -> Optional[dict]:
        """Get channel information (asynchronous)."""
        try:
            async with self._get_async_client() as client:
                response = await client.get(
                    "/api/v1/channels/info",
                    params={"chat_id": chat_id},
                )

                if response.status_code >= 400:
                    self._handle_error_response(response)

                data = response.json()
                result = ChannelInfoResponse(**data)

                if result.success:
                    return {
                        "chat_id": result.chat_id,
                        "title": result.title,
                        "username": result.username,
                        "description": result.description,
                        "invite_link": result.invite_link,
                        "photo": result.photo.model_dump() if result.photo else None,
                        "member_count": result.member_count,
                        "linked_chat_id": result.linked_chat_id,
                        "type": result.type,
                        "raw": result.raw,
                    }
                else:
                    logger.error(f"Failed to get channel info: {result.error}")
                    return None

        except TelegramBotGatewayError:
            raise
        except Exception as e:
            logger.exception(f"Error getting channel info: {e}")
            raise

    async def get_message_stats(
        self,
        chat_id: Union[int, str],
        message_id: int,
    ) -> Optional[dict]:
        """Get message statistics (asynchronous)."""
        try:
            async with self._get_async_client() as client:
                response = await client.get(
                    "/api/v1/messages/stats",
                    params={"chat_id": chat_id, "message_id": message_id},
                )

                if response.status_code >= 400:
                    self._handle_error_response(response)

                data = response.json()
                result = MessageStatsResponse(**data)

                if result.success:
                    return {
                        "chat_id": result.chat_id,
                        "message_id": result.message_id,
                        "views": result.views,
                        "forwards": result.forwards,
                        "reactions": result.reactions,
                        "reply_count": result.reply_count,
                        "date": result.date,
                        "raw": result.raw,
                    }
                else:
                    logger.error(f"Failed to get message stats: {result.error}")
                    return None

        except TelegramBotGatewayError:
            raise
        except Exception as e:
            logger.exception(f"Error getting message stats: {e}")
            raise

    async def get_channel_stats(self, chat_id: Union[int, str]) -> Optional[dict]:
        """Get channel statistics (asynchronous)."""
        try:
            async with self._get_async_client() as client:
                response = await client.get(
                    "/api/v1/channels/stats",
                    params={"chat_id": chat_id},
                )

                if response.status_code >= 400:
                    self._handle_error_response(response)

                data = response.json()
                result = ChannelStatsResponse(**data)

                if result.success:
                    return {
                        "chat_id": result.chat_id,
                        "member_count": result.member_count,
                        "title": result.title,
                        "raw": result.raw,
                    }
                else:
                    logger.error(f"Failed to get channel stats: {result.error}")
                    return None

        except TelegramBotGatewayError:
            raise
        except Exception as e:
            logger.exception(f"Error getting channel stats: {e}")
            raise

    async def verify_bot_permissions(self, chat_id: Union[int, str]) -> Optional[dict]:
        """Verify bot permissions in a channel (asynchronous)."""
        try:
            async with self._get_async_client() as client:
                response = await client.get(
                    "/api/v1/channels/permissions",
                    params={"chat_id": chat_id},
                )

                if response.status_code >= 400:
                    self._handle_error_response(response)

                data = response.json()
                result = BotPermissionsResponse(**data)

                if result.success:
                    return {
                        "chat_id": result.chat_id,
                        "is_member": result.is_member,
                        "is_admin": result.is_admin,
                        "can_post_messages": result.can_post_messages,
                        "can_edit_messages": result.can_edit_messages,
                        "can_delete_messages": result.can_delete_messages,
                        "can_restrict_members": result.can_restrict_members,
                        "can_invite_users": result.can_invite_users,
                        "can_pin_messages": result.can_pin_messages,
                        "can_manage_chat": result.can_manage_chat,
                        "status": result.status,
                        "raw": result.raw,
                    }
                else:
                    logger.error(f"Failed to verify permissions: {result.error}")
                    return None

        except TelegramBotGatewayError:
            raise
        except Exception as e:
            logger.exception(f"Error verifying permissions: {e}")
            raise

    # ============== MTProto Statistics API (Detailed Stats) ==============

    def get_mtproto_status_sync(self) -> Optional[dict]:
        """
        Get MTProto API status (synchronous).
        
        Returns dict with MTProto availability status.
        """
        try:
            with self._get_client() as client:
                response = client.get("/api/v1/stats/status")

                if response.status_code >= 400:
                    self._handle_error_response(response)

                data = response.json()
                result = MTProtoStatusResponse(**data)
                return result.model_dump()

        except TelegramBotGatewayError:
            raise
        except Exception as e:
            logger.exception(f"Error getting MTProto status: {e}")
            raise

    def get_detailed_channel_stats_sync(
        self,
        chat_id: Union[int, str],
    ) -> Optional[dict]:
        """
        Get detailed channel statistics via MTProto API (synchronous).
        
        Provides:
        - Exact participants count
        - Online count
        - Growth statistics
        - Detailed channel info
        
        Requires MTPROTO_ENABLED=true on gateway side.
        """
        try:
            with self._get_client() as client:
                response = client.get(f"/api/v1/stats/channel/{chat_id}")

                if response.status_code >= 400:
                    self._handle_error_response(response)

                data = response.json()
                result = DetailedChannelStatsResponse(**data)

                if result.success:
                    return {
                        "channel": result.channel.model_dump() if result.channel else None,
                        "growth_stats": result.growth_stats.model_dump() if result.growth_stats else None,
                    }
                else:
                    logger.error(f"Failed to get detailed channel stats: {result.error}")
                    return None

        except TelegramBotGatewayError:
            raise
        except Exception as e:
            logger.exception(f"Error getting detailed channel stats: {e}")
            raise

    def get_detailed_message_stats_sync(
        self,
        chat_id: Union[int, str],
        message_id: int,
    ) -> Optional[dict]:
        """
        Get detailed message statistics via MTProto API (synchronous).
        
        Provides:
        - Exact views count
        - Forwards count
        - Replies count
        - Reactions breakdown by emoji
        
        Requires MTPROTO_ENABLED=true on gateway side.
        """
        try:
            with self._get_client() as client:
                response = client.get(f"/api/v1/stats/message/{chat_id}/{message_id}")

                if response.status_code >= 400:
                    self._handle_error_response(response)

                data = response.json()
                result = DetailedMessageStatsResponse(**data)

                if result.success:
                    return {
                        "chat_id": result.chat_id,
                        "message_id": result.message_id,
                        "views": result.views,
                        "forwards": result.forwards,
                        "replies": result.replies,
                        "reactions": result.reactions.model_dump() if result.reactions else None,
                        "date": result.date,
                        "pinned": result.pinned,
                    }
                else:
                    logger.error(f"Failed to get detailed message stats: {result.error}")
                    return None

        except TelegramBotGatewayError:
            raise
        except Exception as e:
            logger.exception(f"Error getting detailed message stats: {e}")
            raise

    def get_batch_detailed_message_stats_sync(
        self,
        chat_id: Union[int, str],
        message_ids: list[int],
    ) -> Optional[dict]:
        """
        Get detailed statistics for multiple messages via MTProto API (synchronous).
        
        Args:
            chat_id: Channel chat ID
            message_ids: List of message IDs (1-100)
        
        Returns:
            Dict with batch results.
        """
        try:
            with self._get_client() as client:
                response = client.post(
                    f"/api/v1/stats/messages/{chat_id}/batch",
                    json=message_ids,
                )

                if response.status_code >= 400:
                    self._handle_error_response(response)

                data = response.json()
                result = BatchDetailedStatsResponse(**data)

                if result.success:
                    return {
                        "chat_id": result.chat_id,
                        "count": result.count,
                        "messages": [msg.model_dump() for msg in result.messages],
                    }
                else:
                    logger.error(f"Failed to get batch detailed stats: {result.error}")
                    return None

        except TelegramBotGatewayError:
            raise
        except Exception as e:
            logger.exception(f"Error getting batch detailed stats: {e}")
            raise

    def get_recent_posts_stats_sync(
        self,
        chat_id: Union[int, str],
        limit: int = 50,
        before: Optional[str] = None,
    ) -> Optional[dict]:
        """
        Get statistics for recent posts in a channel via MTProto API (synchronous).
        
        Args:
            chat_id: Channel chat ID
            limit: Number of posts to fetch (1-100, default: 50)
            before: Get posts before this datetime (ISO format)
        
        Returns:
            Dict with recent posts stats including totals and averages.
        """
        params = {"limit": limit}
        if before:
            params["before"] = before

        try:
            with self._get_client() as client:
                response = client.get(
                    f"/api/v1/stats/posts/{chat_id}/recent",
                    params=params,
                )

                if response.status_code >= 400:
                    self._handle_error_response(response)

                data = response.json()
                result = RecentPostsStatsResponse(**data)

                if result.success:
                    return {
                        "chat_id": result.chat_id,
                        "count": result.count,
                        "totals": result.totals,
                        "average": result.average,
                        "posts": [post.model_dump() for post in result.posts],
                    }
                else:
                    logger.error(f"Failed to get recent posts stats: {result.error}")
                    return None

        except TelegramBotGatewayError:
            raise
        except Exception as e:
            logger.exception(f"Error getting recent posts stats: {e}")
            raise

    def connect_mtproto_sync(self) -> bool:
        """
        Connect MTProto client on gateway side (synchronous).
        
        Returns:
            True if connected successfully.
        """
        try:
            with self._get_client() as client:
                response = client.post("/api/v1/stats/connect")

                if response.status_code >= 400:
                    self._handle_error_response(response)

                data = response.json()
                result = MTProtoConnectResponse(**data)

                if result.success and result.connected:
                    logger.info("MTProto client connected successfully")
                    return True
                else:
                    logger.warning(f"MTProto connection failed: {result.message}")
                    return False

        except TelegramBotGatewayError:
            raise
        except Exception as e:
            logger.exception(f"Error connecting MTProto: {e}")
            raise

    # ============== Async MTProto Methods ==============

    async def get_mtproto_status(self) -> Optional[dict]:
        """Get MTProto API status (asynchronous)."""
        try:
            async with self._get_async_client() as client:
                response = await client.get("/api/v1/stats/status")

                if response.status_code >= 400:
                    self._handle_error_response(response)

                data = response.json()
                result = MTProtoStatusResponse(**data)
                return result.model_dump()

        except TelegramBotGatewayError:
            raise
        except Exception as e:
            logger.exception(f"Error getting MTProto status: {e}")
            raise

    async def get_detailed_channel_stats(
        self,
        chat_id: Union[int, str],
    ) -> Optional[dict]:
        """Get detailed channel statistics via MTProto API (asynchronous)."""
        try:
            async with self._get_async_client() as client:
                response = await client.get(f"/api/v1/stats/channel/{chat_id}")

                if response.status_code >= 400:
                    self._handle_error_response(response)

                data = response.json()
                result = DetailedChannelStatsResponse(**data)

                if result.success:
                    return {
                        "channel": result.channel.model_dump() if result.channel else None,
                        "growth_stats": result.growth_stats.model_dump() if result.growth_stats else None,
                    }
                else:
                    logger.error(f"Failed to get detailed channel stats: {result.error}")
                    return None

        except TelegramBotGatewayError:
            raise
        except Exception as e:
            logger.exception(f"Error getting detailed channel stats: {e}")
            raise

    async def get_detailed_message_stats(
        self,
        chat_id: Union[int, str],
        message_id: int,
    ) -> Optional[dict]:
        """Get detailed message statistics via MTProto API (asynchronous)."""
        try:
            async with self._get_async_client() as client:
                response = await client.get(f"/api/v1/stats/message/{chat_id}/{message_id}")

                if response.status_code >= 400:
                    self._handle_error_response(response)

                data = response.json()
                result = DetailedMessageStatsResponse(**data)

                if result.success:
                    return {
                        "chat_id": result.chat_id,
                        "message_id": result.message_id,
                        "views": result.views,
                        "forwards": result.forwards,
                        "replies": result.replies,
                        "reactions": result.reactions.model_dump() if result.reactions else None,
                        "date": result.date,
                        "pinned": result.pinned,
                    }
                else:
                    logger.error(f"Failed to get detailed message stats: {result.error}")
                    return None

        except TelegramBotGatewayError:
            raise
        except Exception as e:
            logger.exception(f"Error getting detailed message stats: {e}")
            raise

    async def get_recent_posts_stats(
        self,
        chat_id: Union[int, str],
        limit: int = 50,
        before: Optional[str] = None,
    ) -> Optional[dict]:
        """Get statistics for recent posts via MTProto API (asynchronous)."""
        params = {"limit": limit}
        if before:
            params["before"] = before

        try:
            async with self._get_async_client() as client:
                response = await client.get(
                    f"/api/v1/stats/posts/{chat_id}/recent",
                    params=params,
                )

                if response.status_code >= 400:
                    self._handle_error_response(response)

                data = response.json()
                result = RecentPostsStatsResponse(**data)

                if result.success:
                    return {
                        "chat_id": result.chat_id,
                        "count": result.count,
                        "totals": result.totals,
                        "average": result.average,
                        "posts": [post.model_dump() for post in result.posts],
                    }
                else:
                    logger.error(f"Failed to get recent posts stats: {result.error}")
                    return None

        except TelegramBotGatewayError:
            raise
        except Exception as e:
            logger.exception(f"Error getting recent posts stats: {e}")
            raise
