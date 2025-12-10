"""Pydantic schemas for LLM Translation integration."""

from typing import Optional

from pydantic import BaseModel, Field


class TranslationRequest(BaseModel):
    """Request to translate text."""

    text: str = Field(..., description="Text to translate (markdown format)")
    source_language: str = Field(..., description="Source language code (e.g., 'en')")
    target_language: str = Field(..., description="Target language code (e.g., 'ru')")
    context: Optional[str] = Field(
        None,
        description="Additional context for better translation (e.g., 'crypto news')",
    )
    tone: Optional[str] = Field(
        None,
        description="Desired tone (e.g., 'formal', 'casual', 'professional')",
    )
    preserve_formatting: bool = Field(
        default=True,
        description="Whether to preserve markdown/HTML formatting",
    )


class BatchTranslationRequest(BaseModel):
    """Request to translate text to multiple languages at once."""

    text: str = Field(..., description="Text to translate (markdown format)")
    source_language: str = Field(..., description="Source language code")
    target_languages: list[str] = Field(
        ..., description="List of target language codes"
    )
    context: Optional[str] = None
    tone: Optional[str] = None
    preserve_formatting: bool = True


class TranslationResponse(BaseModel):
    """Response with translated text."""

    success: bool
    source_language: str
    target_language: str
    original_text: str
    translated_text: Optional[str] = None
    error: Optional[str] = None
    warning: Optional[str] = None  # e.g., if some formatting was lost
    tokens_used: Optional[int] = None


class BatchTranslationResponse(BaseModel):
    """Response with multiple translations."""

    success: bool
    source_language: str
    original_text: str
    translations: dict[str, str] = Field(
        default_factory=dict,
        description="Map of language code to translated text",
    )
    errors: dict[str, str] = Field(
        default_factory=dict,
        description="Map of language code to error message",
    )
    warnings: dict[str, str] = Field(
        default_factory=dict,
        description="Map of language code to warning message",
    )
    total_tokens_used: Optional[int] = None


class LanguageSupportResponse(BaseModel):
    """Response with supported languages."""

    languages: list[dict] = Field(
        ..., description="List of supported languages with code and name"
    )

