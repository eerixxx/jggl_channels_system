"""Management command to add a Telegram channel by chat_id.

Since the Telegram Bot API doesn't provide a way to list all channels where
the bot is admin, this command allows manually adding channels by their chat_id.

The command will:
1. Fetch channel info from Gateway
2. Verify bot permissions
3. Create/update the Channel in database

Usage:
    python manage.py add_channel -1001234567890
    python manage.py add_channel @channel_username
    python manage.py add_channel -1001234567890 -1001234567891 @another_channel
"""

import logging

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.integrations.telegram_bot.client import TelegramBotClient, TelegramBotGatewayError
from apps.telegram_channels.models import Channel, Language

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Add Telegram channel(s) by chat_id or @username"

    def add_arguments(self, parser):
        parser.add_argument(
            "chat_ids",
            nargs="+",
            help="Chat ID(s) or @username(s) of channels to add",
        )
        parser.add_argument(
            "--language",
            "-l",
            type=str,
            default=None,
            help="Language code for the channel (e.g., 'en', 'ru')",
        )
        parser.add_argument(
            "--primary",
            "-p",
            action="store_true",
            help="Mark channel as primary",
        )

    def handle(self, *args, **options):
        chat_ids = options["chat_ids"]
        language_code = options.get("language")
        is_primary = options.get("primary", False)

        self.stdout.write(
            self.style.SUCCESS(
                f"Adding {len(chat_ids)} channel(s)..."
            )
        )

        client = TelegramBotClient()

        # Check bot info first
        try:
            bot_info = client.get_bot_info_sync()
            if bot_info:
                self.stdout.write(
                    f"Using bot: @{bot_info.get('username')} "
                    f"(ID: {bot_info.get('bot_id')})"
                )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Failed to get bot info: {e}")
            )
            return

        # Get language if specified
        language = None
        if language_code:
            try:
                language = Language.objects.get(code=language_code)
            except Language.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(
                        f"Language '{language_code}' not found. "
                        "Channel will be created without language."
                    )
                )

        success_count = 0
        for chat_id in chat_ids:
            if self._add_channel(client, chat_id, language, is_primary):
                success_count += 1

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully added/updated {success_count}/{len(chat_ids)} channel(s)"
            )
        )

        # Show all channels
        self._show_all_channels()

    def _add_channel(
        self,
        client: TelegramBotClient,
        chat_id: str,
        language: Language = None,
        is_primary: bool = False,
    ) -> bool:
        """Add or update a single channel."""
        self.stdout.write(f"\nProcessing: {chat_id}")

        try:
            # 1. Get channel info
            self.stdout.write("  Fetching channel info...")
            channel_info = client.get_channel_info_sync(chat_id)
            
            if not channel_info:
                self.stdout.write(
                    self.style.ERROR(f"  ✗ Failed to get channel info")
                )
                return False

            telegram_chat_id = channel_info.get("chat_id")
            title = channel_info.get("title", "Unknown")
            username = channel_info.get("username")
            member_count = channel_info.get("member_count", 0)
            description = channel_info.get("description") or ""  # Ensure not None

            self.stdout.write(
                f"  Channel: {title} (@{username or 'private'})"
            )
            self.stdout.write(f"  Members: {member_count}")

            # 2. Get bot permissions
            self.stdout.write("  Checking bot permissions...")
            permissions = client.verify_bot_permissions_sync(chat_id)

            if not permissions:
                self.stdout.write(
                    self.style.WARNING(
                        f"  ⚠ Could not verify permissions (bot may not be admin)"
                    )
                )
                # Still create channel but with limited info
                is_admin = False
                can_post = False
                can_edit = False
                can_delete = False
            else:
                is_admin = permissions.get("is_admin", False)
                can_post = permissions.get("can_post_messages", False)
                can_edit = permissions.get("can_edit_messages", False)
                can_delete = permissions.get("can_delete_messages", False)

                self.stdout.write(
                    f"  Bot status: {'Admin' if is_admin else 'Not admin'}"
                )
                self.stdout.write(
                    f"  Permissions: post={can_post}, edit={can_edit}, delete={can_delete}"
                )

            # 3. Create or update Channel
            # First check if channel exists to preserve existing values
            existing_channel = Channel.objects.filter(
                telegram_chat_id=str(telegram_chat_id)
            ).first()
            
            # Determine values for is_primary and language
            final_is_primary = is_primary
            final_language = language
            
            if existing_channel:
                # Keep existing values if not explicitly set
                final_is_primary = is_primary or existing_channel.is_primary
                final_language = language if language else existing_channel.language
            
            channel, created = Channel.objects.update_or_create(
                telegram_chat_id=str(telegram_chat_id),
                defaults={
                    "title": title,
                    "username": username,
                    "description": description,
                    "member_count": member_count,
                    "is_active": True,
                    "bot_admin": is_admin,
                    "bot_can_post": can_post,
                    "bot_can_edit": can_edit,
                    "bot_can_delete": can_delete,
                    "is_primary": final_is_primary,
                    "language": final_language,
                    "last_synced_at": timezone.now(),
                },
            )

            action = "Created" if created else "Updated"
            self.stdout.write(
                self.style.SUCCESS(f"  ✓ {action}: {channel.title}")
            )
            return True

        except TelegramBotGatewayError as e:
            self.stdout.write(
                self.style.ERROR(
                    f"  ✗ Gateway error: [{e.code}] {e.message}"
                )
            )
            return False
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"  ✗ Error: {e}")
            )
            return False

    def _show_all_channels(self):
        """Show all channels in database."""
        channels = Channel.objects.all().order_by("-is_primary", "title")

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("All channels in database:")
        self.stdout.write("=" * 60)

        if not channels.exists():
            self.stdout.write("  No channels found.")
            return

        for channel in channels:
            status_parts = []
            if channel.is_primary:
                status_parts.append("PRIMARY")
            if channel.is_active:
                status_parts.append("active")
            else:
                status_parts.append("inactive")
            if channel.bot_admin:
                status_parts.append("bot=admin")
            
            perms = []
            if channel.bot_can_post:
                perms.append("post")
            if channel.bot_can_edit:
                perms.append("edit")
            if channel.bot_can_delete:
                perms.append("delete")
            
            perms_str = f"[{','.join(perms)}]" if perms else "[no perms]"
            status_str = ", ".join(status_parts)
            lang_str = f"({channel.language.code})" if channel.language else ""

            self.stdout.write(
                f"  • {channel.title} @{channel.username or 'private'} "
                f"{lang_str} - {status_str} {perms_str}"
            )
            self.stdout.write(
                f"    ID: {channel.telegram_chat_id} | Members: {channel.member_count}"
            )

