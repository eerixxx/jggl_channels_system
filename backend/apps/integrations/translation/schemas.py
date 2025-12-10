"""Pydantic schemas for LLM Translation Middleware integration.

Based on LLM_API.md documentation.
"""

from typing import Any, Optional

from pydantic import BaseModel, Field


# ============== Request Schemas ==============


class TranslationRequest(BaseModel):
    """Request to translate text to a single language."""

    text: str = Field(..., description="Markdown text to translate (max 12000 chars)")
    source_language: str = Field(..., description="Source language code (e.g., 'en')")
    target_language: str = Field(..., description="Target language code (e.g., 'ru')")
    tone: Optional[str] = Field(
        default="professional",
        description="Translation tone: 'formal', 'casual', 'professional'",
    )
    context: Optional[str] = Field(
        None,
        description="Context for better translation (e.g., 'crypto news', 'medical')",
    )
    preserve_formatting: bool = Field(
        default=True,
        description="Whether to preserve markdown formatting",
    )


class BatchTranslationRequest(BaseModel):
    """Request to translate text to multiple languages at once."""

    text: str = Field(..., description="Markdown text to translate")
    source_language: str = Field(..., description="Source language code")
    target_languages: list[str] = Field(
        ..., description="List of target language codes (max 20)"
    )
    tone: Optional[str] = Field(default="professional")
    context: Optional[str] = None
    preserve_formatting: bool = True


# ============== Response Schemas ==============


class TranslationResponse(BaseModel):
    """Response with translated text."""

    translation: str = Field(..., description="Translated text with markdown preserved")
    warnings: list[str] = Field(
        default_factory=list,
        description="Warnings about formatting issues",
    )
    tokens_used: int = Field(0, description="Number of tokens used")


class BatchTranslationResultItem(BaseModel):
    """Single translation result in batch response."""

    target_language: str
    translation: str
    warnings: list[str] = Field(default_factory=list)
    tokens_used: int = 0


class BatchTranslationResponse(BaseModel):
    """Response with multiple translations."""

    results: list[BatchTranslationResultItem] = Field(default_factory=list)
    total_tokens_used: int = 0


class LanguageInfo(BaseModel):
    """Language information."""

    code: str
    name: str


class LanguagesResponse(BaseModel):
    """Response with supported languages."""

    languages: list[LanguageInfo] = Field(default_factory=list)


# ============== Error Response ==============


class TranslationErrorResponse(BaseModel):
    """Error response from the translation service."""

    code: str = Field(..., description="Error code (e.g., 'TEXT_TOO_LONG')")
    error: str = Field(..., description="Human-readable error message")
    details: dict[str, Any] = Field(default_factory=dict)
