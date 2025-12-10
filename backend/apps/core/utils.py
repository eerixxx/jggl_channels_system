"""Core utility functions."""

import re
from typing import Optional

import bleach
import markdown
from markdown.extensions import Extension
from markdown.treeprocessors import Treeprocessor


class TelegramHTMLTreeprocessor(Treeprocessor):
    """
    Treeprocessor that converts markdown elements to Telegram-compatible HTML.
    """

    # Telegram supported tags
    TELEGRAM_TAGS = {
        "b",
        "strong",
        "i",
        "em",
        "u",
        "ins",
        "s",
        "strike",
        "del",
        "a",
        "code",
        "pre",
        "tg-spoiler",
        "tg-emoji",
        "blockquote",
    }

    def run(self, root):
        # Process is handled in the conversion, this is a placeholder
        return root


class TelegramHTMLExtension(Extension):
    """Markdown extension for Telegram HTML output."""

    def extendMarkdown(self, md):
        md.treeprocessors.register(
            TelegramHTMLTreeprocessor(md), "telegram_html", 15
        )


def markdown_to_telegram_html(text: str) -> str:
    """
    Convert Markdown text to Telegram-compatible HTML.

    Telegram supports a limited subset of HTML:
    - <b>, <strong> - bold
    - <i>, <em> - italic
    - <u>, <ins> - underline
    - <s>, <strike>, <del> - strikethrough
    - <a href="..."> - links
    - <code> - inline code
    - <pre> - code blocks
    - <tg-spoiler> - spoiler
    - <blockquote> - quotes

    Args:
        text: Markdown-formatted text

    Returns:
        Telegram-compatible HTML string
    """
    if not text:
        return ""

    # Convert markdown to HTML
    md = markdown.Markdown(
        extensions=["extra", "nl2br", TelegramHTMLExtension()],
        output_format="html",
    )
    html = md.convert(text)

    # Clean and sanitize HTML, keeping only Telegram-supported tags
    allowed_tags = [
        "b",
        "strong",
        "i",
        "em",
        "u",
        "ins",
        "s",
        "strike",
        "del",
        "a",
        "code",
        "pre",
        "tg-spoiler",
        "blockquote",
    ]
    allowed_attributes = {
        "a": ["href"],
    }

    html = bleach.clean(
        html,
        tags=allowed_tags,
        attributes=allowed_attributes,
        strip=True,
    )

    # Convert some tags to Telegram equivalents
    html = html.replace("<strong>", "<b>").replace("</strong>", "</b>")
    html = html.replace("<em>", "<i>").replace("</em>", "</i>")
    html = html.replace("<ins>", "<u>").replace("</ins>", "</u>")
    html = html.replace("<strike>", "<s>").replace("</strike>", "</s>")
    html = html.replace("<del>", "<s>").replace("</del>", "</s>")

    # Remove paragraph tags (Telegram doesn't support them)
    html = html.replace("<p>", "").replace("</p>", "\n\n")

    # Clean up extra newlines
    html = re.sub(r"\n{3,}", "\n\n", html)
    html = html.strip()

    return html


def telegram_html_to_markdown(html: str) -> str:
    """
    Convert Telegram HTML back to Markdown.

    Args:
        html: Telegram HTML text

    Returns:
        Markdown-formatted string
    """
    if not html:
        return ""

    text = html

    # Convert HTML tags to Markdown
    text = re.sub(r"<b>(.*?)</b>", r"**\1**", text, flags=re.DOTALL)
    text = re.sub(r"<strong>(.*?)</strong>", r"**\1**", text, flags=re.DOTALL)
    text = re.sub(r"<i>(.*?)</i>", r"*\1*", text, flags=re.DOTALL)
    text = re.sub(r"<em>(.*?)</em>", r"*\1*", text, flags=re.DOTALL)
    text = re.sub(r"<u>(.*?)</u>", r"__\1__", text, flags=re.DOTALL)
    text = re.sub(r"<s>(.*?)</s>", r"~~\1~~", text, flags=re.DOTALL)
    text = re.sub(
        r'<a href="(.*?)">(.*?)</a>', r"[\2](\1)", text, flags=re.DOTALL
    )
    text = re.sub(r"<code>(.*?)</code>", r"`\1`", text, flags=re.DOTALL)
    text = re.sub(r"<pre>(.*?)</pre>", r"```\n\1\n```", text, flags=re.DOTALL)
    text = re.sub(
        r"<blockquote>(.*?)</blockquote>", r"> \1", text, flags=re.DOTALL
    )

    # Clean up spoiler tags
    text = re.sub(
        r"<tg-spoiler>(.*?)</tg-spoiler>", r"||\1||", text, flags=re.DOTALL
    )

    return text.strip()


def truncate_text(text: str, max_length: int = 4096, suffix: str = "...") -> str:
    """
    Truncate text to a maximum length, preserving word boundaries.

    Args:
        text: Text to truncate
        max_length: Maximum length (Telegram message limit is 4096)
        suffix: Suffix to add when truncating

    Returns:
        Truncated text
    """
    if not text or len(text) <= max_length:
        return text

    truncated = text[: max_length - len(suffix)]
    # Find last space to avoid cutting words
    last_space = truncated.rfind(" ")
    if last_space > max_length // 2:
        truncated = truncated[:last_space]

    return truncated + suffix


def escape_telegram_html(text: str) -> str:
    """
    Escape special characters for Telegram HTML mode.

    Args:
        text: Raw text

    Returns:
        Escaped text safe for Telegram HTML
    """
    if not text:
        return ""

    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def validate_telegram_html(html: str) -> tuple[bool, Optional[str]]:
    """
    Validate that HTML is compatible with Telegram.

    Args:
        html: HTML text to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not html:
        return True, None

    # Check length
    if len(html) > 4096:
        return False, f"Message too long: {len(html)} characters (max 4096)"

    # Check for unsupported tags
    allowed_tags_pattern = (
        r"<(?!/?(?:b|strong|i|em|u|ins|s|strike|del|a|code|pre|"
        r"tg-spoiler|tg-emoji|blockquote)\b)[^>]+>"
    )
    unsupported = re.findall(allowed_tags_pattern, html, re.IGNORECASE)
    if unsupported:
        return False, f"Unsupported HTML tags: {', '.join(set(unsupported))}"

    # Check for unclosed tags
    open_tags = re.findall(r"<([a-z-]+)(?:\s[^>]*)?>", html, re.IGNORECASE)
    close_tags = re.findall(r"</([a-z-]+)>", html, re.IGNORECASE)

    # Simple check - count should match for most cases
    open_count = {}
    for tag in open_tags:
        tag = tag.lower()
        open_count[tag] = open_count.get(tag, 0) + 1

    close_count = {}
    for tag in close_tags:
        tag = tag.lower()
        close_count[tag] = close_count.get(tag, 0) + 1

    for tag, count in open_count.items():
        if close_count.get(tag, 0) != count:
            return False, f"Unclosed or mismatched tag: <{tag}>"

    return True, None

