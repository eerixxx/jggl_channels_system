"""Tests for core app."""

import pytest
from apps.core.utils import (
    markdown_to_telegram_html,
    telegram_html_to_markdown,
    truncate_text,
    escape_telegram_html,
    validate_telegram_html,
)


class TestMarkdownToTelegramHtml:
    """Tests for markdown_to_telegram_html function."""

    def test_empty_string(self):
        """Test with empty string."""
        assert markdown_to_telegram_html("") == ""

    def test_plain_text(self):
        """Test with plain text."""
        result = markdown_to_telegram_html("Hello world")
        assert "Hello world" in result

    def test_bold(self):
        """Test bold formatting."""
        result = markdown_to_telegram_html("**bold text**")
        assert "<b>bold text</b>" in result

    def test_italic(self):
        """Test italic formatting."""
        result = markdown_to_telegram_html("*italic text*")
        assert "<i>italic text</i>" in result

    def test_link(self):
        """Test link formatting."""
        result = markdown_to_telegram_html("[link](https://example.com)")
        assert '<a href="https://example.com">link</a>' in result

    def test_code(self):
        """Test inline code formatting."""
        result = markdown_to_telegram_html("`code`")
        assert "<code>code</code>" in result

    def test_combined_formatting(self):
        """Test combined formatting."""
        text = "**bold** and *italic* with `code`"
        result = markdown_to_telegram_html(text)
        assert "<b>bold</b>" in result
        assert "<i>italic</i>" in result
        assert "<code>code</code>" in result


class TestTelegramHtmlToMarkdown:
    """Tests for telegram_html_to_markdown function."""

    def test_empty_string(self):
        """Test with empty string."""
        assert telegram_html_to_markdown("") == ""

    def test_bold(self):
        """Test bold conversion."""
        assert "**bold**" in telegram_html_to_markdown("<b>bold</b>")

    def test_italic(self):
        """Test italic conversion."""
        assert "*italic*" in telegram_html_to_markdown("<i>italic</i>")

    def test_link(self):
        """Test link conversion."""
        result = telegram_html_to_markdown('<a href="https://example.com">link</a>')
        assert "[link](https://example.com)" in result


class TestTruncateText:
    """Tests for truncate_text function."""

    def test_short_text(self):
        """Test with text shorter than max length."""
        assert truncate_text("Hello", 100) == "Hello"

    def test_exact_length(self):
        """Test with text exactly at max length."""
        text = "a" * 100
        assert truncate_text(text, 100) == text

    def test_long_text(self):
        """Test with text longer than max length."""
        text = "Hello world this is a test"
        result = truncate_text(text, 15)
        assert len(result) <= 15
        assert result.endswith("...")

    def test_empty_string(self):
        """Test with empty string."""
        assert truncate_text("", 100) == ""


class TestEscapeTelegramHtml:
    """Tests for escape_telegram_html function."""

    def test_empty_string(self):
        """Test with empty string."""
        assert escape_telegram_html("") == ""

    def test_no_special_chars(self):
        """Test with no special characters."""
        assert escape_telegram_html("Hello world") == "Hello world"

    def test_ampersand(self):
        """Test ampersand escaping."""
        assert escape_telegram_html("a & b") == "a &amp; b"

    def test_less_than(self):
        """Test less than escaping."""
        assert escape_telegram_html("a < b") == "a &lt; b"

    def test_greater_than(self):
        """Test greater than escaping."""
        assert escape_telegram_html("a > b") == "a &gt; b"

    def test_combined(self):
        """Test combined escaping."""
        result = escape_telegram_html("<script>alert('xss')</script>")
        assert "<" not in result
        assert ">" not in result


class TestValidateTelegramHtml:
    """Tests for validate_telegram_html function."""

    def test_empty_string(self):
        """Test with empty string."""
        is_valid, error = validate_telegram_html("")
        assert is_valid
        assert error is None

    def test_valid_html(self):
        """Test with valid Telegram HTML."""
        html = "<b>bold</b> and <i>italic</i>"
        is_valid, error = validate_telegram_html(html)
        assert is_valid
        assert error is None

    def test_too_long(self):
        """Test with text exceeding 4096 characters."""
        html = "a" * 5000
        is_valid, error = validate_telegram_html(html)
        assert not is_valid
        assert "too long" in error.lower()

    def test_unsupported_tag(self):
        """Test with unsupported HTML tag."""
        html = "<div>content</div>"
        is_valid, error = validate_telegram_html(html)
        assert not is_valid
        assert "unsupported" in error.lower()

