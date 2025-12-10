"""LLM Translation service client."""

import asyncio
import logging
import time
from typing import Optional

import httpx
from django.conf import settings

from .schemas import (
    BatchTranslationRequest,
    BatchTranslationResponse,
    TranslationRequest,
    TranslationResponse,
)

logger = logging.getLogger(__name__)


class TranslationError(Exception):
    """Custom exception for translation errors."""

    pass


class TranslationClient:
    """
    Client for communicating with the LLM translation middleware service.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        token: Optional[str] = None,
        timeout: float = 60.0,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        self.base_url = base_url or settings.TRANSLATION_SERVICE_URL
        self.token = token or settings.TRANSLATION_SERVICE_TOKEN
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay

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

    def _should_retry(self, exception: Exception) -> bool:
        """Determine if we should retry based on the exception."""
        if isinstance(exception, httpx.HTTPStatusError):
            # Retry on server errors and rate limits
            return exception.response.status_code in (429, 500, 502, 503, 504)
        if isinstance(exception, (httpx.ConnectError, httpx.ReadTimeout)):
            return True
        return False

    # ============== Synchronous Methods ==============

    def translate_sync(
        self,
        text: str,
        source_language: str,
        target_language: str,
        context: Optional[str] = None,
        tone: Optional[str] = None,
        preserve_formatting: bool = True,
    ) -> Optional[str]:
        """
        Translate text to a target language (synchronous).

        Returns the translated text if successful, None otherwise.
        Implements retry logic with exponential backoff.
        """
        request = TranslationRequest(
            text=text,
            source_language=source_language,
            target_language=target_language,
            context=context,
            tone=tone,
            preserve_formatting=preserve_formatting,
        )

        last_exception = None

        for attempt in range(self.max_retries):
            try:
                with self._get_client() as client:
                    response = client.post(
                        "/api/v1/translate",
                        json=request.model_dump(exclude_none=True),
                    )
                    response.raise_for_status()

                    data = response.json()
                    result = TranslationResponse(**data)

                    if result.success:
                        if result.warning:
                            logger.warning(
                                f"Translation warning ({target_language}): {result.warning}"
                            )
                        return result.translated_text
                    else:
                        logger.error(f"Translation failed: {result.error}")
                        raise TranslationError(result.error)

            except Exception as e:
                last_exception = e
                if self._should_retry(e) and attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2**attempt)  # Exponential backoff
                    logger.warning(
                        f"Translation attempt {attempt + 1} failed, "
                        f"retrying in {delay}s: {e}"
                    )
                    time.sleep(delay)
                else:
                    break

        logger.exception(f"Translation failed after {self.max_retries} attempts")
        raise last_exception or TranslationError("Translation failed")

    def batch_translate_sync(
        self,
        text: str,
        source_language: str,
        target_languages: list[str],
        context: Optional[str] = None,
        tone: Optional[str] = None,
        preserve_formatting: bool = True,
    ) -> dict[str, str]:
        """
        Translate text to multiple languages (synchronous).

        Returns a dict mapping language code to translated text.
        Raises TranslationError if all translations fail.
        """
        request = BatchTranslationRequest(
            text=text,
            source_language=source_language,
            target_languages=target_languages,
            context=context,
            tone=tone,
            preserve_formatting=preserve_formatting,
        )

        try:
            with self._get_client() as client:
                response = client.post(
                    "/api/v1/translate/batch",
                    json=request.model_dump(exclude_none=True),
                )
                response.raise_for_status()

                data = response.json()
                result = BatchTranslationResponse(**data)

                if result.success or result.translations:
                    # Log any warnings
                    for lang, warning in result.warnings.items():
                        logger.warning(f"Translation warning ({lang}): {warning}")

                    # Log any errors
                    for lang, error in result.errors.items():
                        logger.error(f"Translation error ({lang}): {error}")

                    return result.translations
                else:
                    raise TranslationError(
                        f"Batch translation failed: {result.errors}"
                    )

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error in batch translation: {e.response.status_code}")
            raise TranslationError(f"HTTP error: {e.response.status_code}")
        except Exception as e:
            logger.exception(f"Batch translation error: {e}")
            raise TranslationError(str(e))

    # ============== Asynchronous Methods ==============

    async def translate(
        self,
        text: str,
        source_language: str,
        target_language: str,
        context: Optional[str] = None,
        tone: Optional[str] = None,
        preserve_formatting: bool = True,
    ) -> Optional[str]:
        """
        Translate text to a target language (asynchronous).

        Returns the translated text if successful, None otherwise.
        """
        request = TranslationRequest(
            text=text,
            source_language=source_language,
            target_language=target_language,
            context=context,
            tone=tone,
            preserve_formatting=preserve_formatting,
        )

        last_exception = None

        for attempt in range(self.max_retries):
            try:
                async with self._get_async_client() as client:
                    response = await client.post(
                        "/api/v1/translate",
                        json=request.model_dump(exclude_none=True),
                    )
                    response.raise_for_status()

                    data = response.json()
                    result = TranslationResponse(**data)

                    if result.success:
                        if result.warning:
                            logger.warning(
                                f"Translation warning ({target_language}): {result.warning}"
                            )
                        return result.translated_text
                    else:
                        logger.error(f"Translation failed: {result.error}")
                        raise TranslationError(result.error)

            except Exception as e:
                last_exception = e
                if self._should_retry(e) and attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2**attempt)
                    logger.warning(
                        f"Translation attempt {attempt + 1} failed, "
                        f"retrying in {delay}s: {e}"
                    )
                    await asyncio.sleep(delay)
                else:
                    break

        logger.exception(f"Translation failed after {self.max_retries} attempts")
        raise last_exception or TranslationError("Translation failed")

    async def batch_translate(
        self,
        text: str,
        source_language: str,
        target_languages: list[str],
        context: Optional[str] = None,
        tone: Optional[str] = None,
        preserve_formatting: bool = True,
    ) -> dict[str, str]:
        """
        Translate text to multiple languages (asynchronous).

        Returns a dict mapping language code to translated text.
        """
        request = BatchTranslationRequest(
            text=text,
            source_language=source_language,
            target_languages=target_languages,
            context=context,
            tone=tone,
            preserve_formatting=preserve_formatting,
        )

        try:
            async with self._get_async_client() as client:
                response = await client.post(
                    "/api/v1/translate/batch",
                    json=request.model_dump(exclude_none=True),
                )
                response.raise_for_status()

                data = response.json()
                result = BatchTranslationResponse(**data)

                if result.success or result.translations:
                    for lang, warning in result.warnings.items():
                        logger.warning(f"Translation warning ({lang}): {warning}")

                    for lang, error in result.errors.items():
                        logger.error(f"Translation error ({lang}): {error}")

                    return result.translations
                else:
                    raise TranslationError(
                        f"Batch translation failed: {result.errors}"
                    )

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error in batch translation: {e.response.status_code}")
            raise TranslationError(f"HTTP error: {e.response.status_code}")
        except Exception as e:
            logger.exception(f"Batch translation error: {e}")
            raise TranslationError(str(e))

    async def translate_parallel(
        self,
        text: str,
        source_language: str,
        target_languages: list[str],
        context: Optional[str] = None,
        tone: Optional[str] = None,
        preserve_formatting: bool = True,
    ) -> dict[str, str]:
        """
        Translate text to multiple languages in parallel (asynchronous).

        This is an alternative to batch_translate that makes parallel requests
        instead of a single batch request.

        Returns a dict mapping language code to translated text.
        """
        tasks = [
            self.translate(
                text=text,
                source_language=source_language,
                target_language=lang,
                context=context,
                tone=tone,
                preserve_formatting=preserve_formatting,
            )
            for lang in target_languages
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        translations = {}
        for lang, result in zip(target_languages, results):
            if isinstance(result, Exception):
                logger.error(f"Failed to translate to {lang}: {result}")
            elif result:
                translations[lang] = result

        return translations

