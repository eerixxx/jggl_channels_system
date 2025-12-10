"""LLM Translation Middleware client.

Based on LLM_API.md documentation.
API Base: http://178.217.98.201:8002
"""

import asyncio
import logging
import time
from typing import Optional

import httpx
from django.conf import settings

from .schemas import (
    BatchTranslationRequest,
    BatchTranslationResponse,
    LanguagesResponse,
    TranslationErrorResponse,
    TranslationRequest,
    TranslationResponse,
)

logger = logging.getLogger(__name__)


class TranslationError(Exception):
    """Custom exception for translation errors."""

    def __init__(self, message: str, code: str = "UNKNOWN", details: dict = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


class TranslationClient:
    """
    Client for communicating with the LLM Translation Middleware service.
    
    Handles:
    - Single text translation
    - Batch translation to multiple languages
    - Retry logic with exponential backoff
    - Error handling and logging
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        token: Optional[str] = None,
        timeout: float = 120.0,  # LLM can be slow
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        self.base_url = (base_url or getattr(settings, 'TRANSLATION_SERVICE_URL', '')).rstrip('/')
        self.token = token or getattr(settings, 'TRANSLATION_SERVICE_TOKEN', '')
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

    def _handle_error_response(self, response: httpx.Response) -> None:
        """Parse error response and raise TranslationError."""
        try:
            data = response.json()
            error = TranslationErrorResponse(**data)
            raise TranslationError(
                message=error.error,
                code=error.code,
                details=error.details,
            )
        except TranslationError:
            raise
        except Exception:
            raise TranslationError(
                message=f"HTTP {response.status_code}: {response.text[:200]}",
                code=f"HTTP_{response.status_code}",
            )

    def _should_retry(self, exception: Exception) -> bool:
        """Determine if we should retry based on the exception."""
        if isinstance(exception, TranslationError):
            # Retry on rate limits and service unavailable
            return exception.code in (
                "LLM_RATE_LIMIT",
                "LLM_UNAVAILABLE",
                "LLM_TIMEOUT",
            )
        if isinstance(exception, httpx.HTTPStatusError):
            return exception.response.status_code in (429, 500, 502, 503, 504)
        if isinstance(exception, (httpx.ConnectError, httpx.ReadTimeout)):
            return True
        return False

    # ============== Health Check ==============

    def health_check(self) -> bool:
        """Check if the translation service is healthy."""
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(f"{self.base_url}/health")
                if response.status_code == 200:
                    data = response.json()
                    return data.get("status") == "healthy"
        except Exception as e:
            logger.warning(f"Translation service health check failed: {e}")
        return False

    # ============== Get Languages ==============

    def get_languages_sync(self) -> list[dict]:
        """Get list of supported languages (synchronous)."""
        try:
            with self._get_client() as client:
                response = client.get("/api/v1/languages")
                if response.status_code >= 400:
                    self._handle_error_response(response)
                
                data = response.json()
                result = LanguagesResponse(**data)
                return [{"code": lang.code, "name": lang.name} for lang in result.languages]
        except TranslationError:
            raise
        except Exception as e:
            logger.exception(f"Error getting languages: {e}")
            raise TranslationError(str(e), code="INTERNAL_ERROR")

    # ============== Synchronous Methods ==============

    def translate_sync(
        self,
        text: str,
        source_language: str,
        target_language: str,
        context: Optional[str] = None,
        tone: str = "professional",
        preserve_formatting: bool = True,
    ) -> str:
        """
        Translate text to a target language (synchronous).

        Args:
            text: Markdown text to translate (max 12000 chars)
            source_language: Source language code (e.g., 'en', 'ru')
            target_language: Target language code
            context: Optional context for better translation
            tone: Translation tone ('formal', 'casual', 'professional')
            preserve_formatting: Whether to preserve markdown

        Returns:
            Translated text with preserved formatting.

        Raises:
            TranslationError: If translation fails after retries.
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

                    if response.status_code >= 400:
                        self._handle_error_response(response)

                    data = response.json()
                    result = TranslationResponse(**data)

                    # Log warnings if any
                    for warning in result.warnings:
                        logger.warning(
                            f"Translation warning ({source_language}->{target_language}): {warning}"
                        )

                    logger.info(
                        f"Translated {len(text)} chars from {source_language} to {target_language} "
                        f"(tokens: {result.tokens_used})"
                    )

                    return result.translation

            except TranslationError as e:
                last_exception = e
                if self._should_retry(e) and attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2 ** attempt)
                    logger.warning(
                        f"Translation attempt {attempt + 1} failed ({e.code}), "
                        f"retrying in {delay}s"
                    )
                    time.sleep(delay)
                else:
                    break

            except Exception as e:
                last_exception = TranslationError(str(e), code="INTERNAL_ERROR")
                if self._should_retry(e) and attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2 ** attempt)
                    logger.warning(
                        f"Translation attempt {attempt + 1} failed, retrying in {delay}s: {e}"
                    )
                    time.sleep(delay)
                else:
                    break

        logger.error(
            f"Translation failed after {self.max_retries} attempts: "
            f"{source_language}->{target_language}"
        )
        raise last_exception or TranslationError("Translation failed")

    def batch_translate_sync(
        self,
        text: str,
        source_language: str,
        target_languages: list[str],
        context: Optional[str] = None,
        tone: str = "professional",
        preserve_formatting: bool = True,
    ) -> dict[str, str]:
        """
        Translate text to multiple languages (synchronous).

        Args:
            text: Markdown text to translate
            source_language: Source language code
            target_languages: List of target language codes (max 20)
            context: Optional context for better translation
            tone: Translation tone
            preserve_formatting: Whether to preserve markdown

        Returns:
            Dict mapping language code to translated text.

        Raises:
            TranslationError: If all translations fail.
        """
        if not target_languages:
            return {}

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

                if response.status_code >= 400:
                    self._handle_error_response(response)

                data = response.json()
                result = BatchTranslationResponse(**data)

                translations = {}
                for item in result.results:
                    translations[item.target_language] = item.translation
                    
                    # Log warnings
                    for warning in item.warnings:
                        logger.warning(
                            f"Translation warning ({item.target_language}): {warning}"
                        )

                logger.info(
                    f"Batch translated {len(text)} chars from {source_language} to "
                    f"{len(translations)} languages (tokens: {result.total_tokens_used})"
                )

                return translations

        except TranslationError:
            raise
        except Exception as e:
            logger.exception(f"Batch translation error: {e}")
            raise TranslationError(str(e), code="INTERNAL_ERROR")

    # ============== Asynchronous Methods ==============

    async def translate(
        self,
        text: str,
        source_language: str,
        target_language: str,
        context: Optional[str] = None,
        tone: str = "professional",
        preserve_formatting: bool = True,
    ) -> str:
        """
        Translate text to a target language (asynchronous).

        Returns the translated text.
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

                    if response.status_code >= 400:
                        self._handle_error_response(response)

                    data = response.json()
                    result = TranslationResponse(**data)

                    for warning in result.warnings:
                        logger.warning(
                            f"Translation warning ({source_language}->{target_language}): {warning}"
                        )

                    return result.translation

            except TranslationError as e:
                last_exception = e
                if self._should_retry(e) and attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2 ** attempt)
                    logger.warning(
                        f"Translation attempt {attempt + 1} failed ({e.code}), "
                        f"retrying in {delay}s"
                    )
                    await asyncio.sleep(delay)
                else:
                    break

            except Exception as e:
                last_exception = TranslationError(str(e), code="INTERNAL_ERROR")
                if self._should_retry(e) and attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2 ** attempt)
                    await asyncio.sleep(delay)
                else:
                    break

        raise last_exception or TranslationError("Translation failed")

    async def batch_translate(
        self,
        text: str,
        source_language: str,
        target_languages: list[str],
        context: Optional[str] = None,
        tone: str = "professional",
        preserve_formatting: bool = True,
    ) -> dict[str, str]:
        """
        Translate text to multiple languages (asynchronous).

        Returns a dict mapping language code to translated text.
        """
        if not target_languages:
            return {}

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

                if response.status_code >= 400:
                    self._handle_error_response(response)

                data = response.json()
                result = BatchTranslationResponse(**data)

                translations = {}
                for item in result.results:
                    translations[item.target_language] = item.translation

                return translations

        except TranslationError:
            raise
        except Exception as e:
            logger.exception(f"Batch translation error: {e}")
            raise TranslationError(str(e), code="INTERNAL_ERROR")
