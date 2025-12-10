"""Telegram Bot service client."""

import asyncio
import logging
from typing import Optional

import httpx
from django.conf import settings

from .schemas import (
    BotPermissionsResponse,
    ChannelInfoResponse,
    ChannelStatsResponse,
    EditMessageRequest,
    EditMessageResponse,
    MessageStatsResponse,
    SendMessageRequest,
    SendMessageResponse,
)

logger = logging.getLogger(__name__)


class TelegramBotClient:
    """
    Client for communicating with the external Telegram bot service.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        token: Optional[str] = None,
        timeout: float = 30.0,
    ):
        self.base_url = base_url or settings.TELEGRAM_BOT_SERVICE_URL
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

    # ============== Synchronous Methods ==============

    def send_message_sync(
        self,
        chat_id: str,
        text: str,
        parse_mode: str = "HTML",
        photo_url: Optional[str] = None,
        disable_web_page_preview: bool = False,
        disable_notification: bool = False,
        reply_markup: Optional[dict] = None,
    ) -> Optional[dict]:
        """
        Send a message to a channel (synchronous).

        Returns the response dict with message_id if successful, None otherwise.
        """
        request = SendMessageRequest(
            chat_id=chat_id,
            text=text,
            parse_mode=parse_mode,
            photo_url=photo_url,
            disable_web_page_preview=disable_web_page_preview,
            disable_notification=disable_notification,
            reply_markup=reply_markup,
        )

        try:
            with self._get_client() as client:
                response = client.post(
                    "/api/v1/messages/send",
                    json=request.model_dump(exclude_none=True),
                )
                response.raise_for_status()

                data = response.json()
                result = SendMessageResponse(**data)

                if result.success:
                    return {"message_id": result.message_id, "raw": result.raw_response}
                else:
                    logger.error(f"Failed to send message: {result.error}")
                    return None

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error sending message: {e.response.status_code}")
            raise
        except Exception as e:
            logger.exception(f"Error sending message: {e}")
            raise

    def edit_message_sync(
        self,
        chat_id: str,
        message_id: str,
        text: str,
        parse_mode: str = "HTML",
        disable_web_page_preview: bool = False,
        reply_markup: Optional[dict] = None,
    ) -> bool:
        """Edit an existing message (synchronous)."""
        request = EditMessageRequest(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            parse_mode=parse_mode,
            disable_web_page_preview=disable_web_page_preview,
            reply_markup=reply_markup,
        )

        try:
            with self._get_client() as client:
                response = client.post(
                    "/api/v1/messages/edit",
                    json=request.model_dump(exclude_none=True),
                )
                response.raise_for_status()

                data = response.json()
                result = EditMessageResponse(**data)
                return result.success

        except Exception as e:
            logger.exception(f"Error editing message: {e}")
            raise

    def get_channel_info_sync(self, chat_id: str) -> Optional[dict]:
        """Get channel information (synchronous)."""
        try:
            with self._get_client() as client:
                response = client.get(
                    "/api/v1/channels/info",
                    params={"chat_id": chat_id},
                )
                response.raise_for_status()

                data = response.json()
                result = ChannelInfoResponse(**data)

                if result.success:
                    return result.model_dump(exclude={"success", "error"})
                else:
                    logger.error(f"Failed to get channel info: {result.error}")
                    return None

        except Exception as e:
            logger.exception(f"Error getting channel info: {e}")
            raise

    def verify_bot_permissions_sync(self, chat_id: str) -> Optional[dict]:
        """Verify bot permissions in a channel (synchronous)."""
        try:
            with self._get_client() as client:
                response = client.get(
                    "/api/v1/channels/permissions",
                    params={"chat_id": chat_id},
                )
                response.raise_for_status()

                data = response.json()
                result = BotPermissionsResponse(**data)

                if result.success:
                    return result.model_dump(exclude={"success", "error"})
                else:
                    logger.error(f"Failed to verify permissions: {result.error}")
                    return None

        except Exception as e:
            logger.exception(f"Error verifying permissions: {e}")
            raise

    def get_message_stats_sync(self, chat_id: str, message_id: str) -> Optional[dict]:
        """Get message statistics (synchronous)."""
        try:
            with self._get_client() as client:
                response = client.get(
                    "/api/v1/messages/stats",
                    params={"chat_id": chat_id, "message_id": message_id},
                )
                response.raise_for_status()

                data = response.json()
                result = MessageStatsResponse(**data)

                if result.success:
                    return result.model_dump(exclude={"success", "error"})
                else:
                    logger.error(f"Failed to get message stats: {result.error}")
                    return None

        except Exception as e:
            logger.exception(f"Error getting message stats: {e}")
            raise

    def get_channel_stats_sync(self, chat_id: str) -> Optional[dict]:
        """Get channel statistics (synchronous)."""
        try:
            with self._get_client() as client:
                response = client.get(
                    "/api/v1/channels/stats",
                    params={"chat_id": chat_id},
                )
                response.raise_for_status()

                data = response.json()
                result = ChannelStatsResponse(**data)

                if result.success:
                    return result.model_dump(exclude={"success", "error"})
                else:
                    logger.error(f"Failed to get channel stats: {result.error}")
                    return None

        except Exception as e:
            logger.exception(f"Error getting channel stats: {e}")
            raise

    # ============== Asynchronous Methods ==============

    async def send_message(
        self,
        chat_id: str,
        text: str,
        parse_mode: str = "HTML",
        photo_url: Optional[str] = None,
        disable_web_page_preview: bool = False,
        disable_notification: bool = False,
        reply_markup: Optional[dict] = None,
    ) -> Optional[dict]:
        """Send a message to a channel (asynchronous)."""
        request = SendMessageRequest(
            chat_id=chat_id,
            text=text,
            parse_mode=parse_mode,
            photo_url=photo_url,
            disable_web_page_preview=disable_web_page_preview,
            disable_notification=disable_notification,
            reply_markup=reply_markup,
        )

        try:
            async with self._get_async_client() as client:
                response = await client.post(
                    "/api/v1/messages/send",
                    json=request.model_dump(exclude_none=True),
                )
                response.raise_for_status()

                data = response.json()
                result = SendMessageResponse(**data)

                if result.success:
                    return {"message_id": result.message_id, "raw": result.raw_response}
                else:
                    logger.error(f"Failed to send message: {result.error}")
                    return None

        except Exception as e:
            logger.exception(f"Error sending message: {e}")
            raise

    async def get_channel_info(self, chat_id: str) -> Optional[dict]:
        """Get channel information (asynchronous)."""
        try:
            async with self._get_async_client() as client:
                response = await client.get(
                    "/api/v1/channels/info",
                    params={"chat_id": chat_id},
                )
                response.raise_for_status()

                data = response.json()
                result = ChannelInfoResponse(**data)

                if result.success:
                    return result.model_dump(exclude={"success", "error"})
                else:
                    logger.error(f"Failed to get channel info: {result.error}")
                    return None

        except Exception as e:
            logger.exception(f"Error getting channel info: {e}")
            raise

    async def get_message_stats(self, chat_id: str, message_id: str) -> Optional[dict]:
        """Get message statistics (asynchronous)."""
        try:
            async with self._get_async_client() as client:
                response = await client.get(
                    "/api/v1/messages/stats",
                    params={"chat_id": chat_id, "message_id": message_id},
                )
                response.raise_for_status()

                data = response.json()
                result = MessageStatsResponse(**data)

                if result.success:
                    return result.model_dump(exclude={"success", "error"})
                else:
                    logger.error(f"Failed to get message stats: {result.error}")
                    return None

        except Exception as e:
            logger.exception(f"Error getting message stats: {e}")
            raise

    async def get_channel_stats(self, chat_id: str) -> Optional[dict]:
        """Get channel statistics (asynchronous)."""
        try:
            async with self._get_async_client() as client:
                response = await client.get(
                    "/api/v1/channels/stats",
                    params={"chat_id": chat_id},
                )
                response.raise_for_status()

                data = response.json()
                result = ChannelStatsResponse(**data)

                if result.success:
                    return result.model_dump(exclude={"success", "error"})
                else:
                    logger.error(f"Failed to get channel stats: {result.error}")
                    return None

        except Exception as e:
            logger.exception(f"Error getting channel stats: {e}")
            raise

