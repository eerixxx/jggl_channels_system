"""Management command to sync channels from Telegram Bot Gateway.

This command processes pending bot updates to discover channels where the bot
was recently added. For adding existing channels, use `add_channel` command.

IMPORTANT: This command only finds channels where the bot was RECENTLY added
(pending updates). If the bot was added before and updates were already processed,
use `add_channel` command with specific chat_id instead.

Usage:
    python manage.py sync_bot_channels
    python manage.py sync_bot_channels --continuous --interval 60
    
To add specific channels:
    python manage.py add_channel -1001234567890
    python manage.py add_channel @channel_username
"""

import logging
import time

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.integrations.telegram_bot.client import TelegramBotClient, TelegramBotGatewayError
from apps.telegram_channels.models import Channel, Language

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Sync channels from Telegram Bot Gateway by processing pending bot updates"

    def add_arguments(self, parser):
        parser.add_argument(
            "--continuous",
            action="store_true",
            help="Run continuously (useful for development/testing)",
        )
        parser.add_argument(
            "--interval",
            type=int,
            default=60,
            help="Interval in seconds for continuous mode (default: 60)",
        )
        parser.add_argument(
            "--once",
            action="store_true",
            help="Process updates once and exit (default behavior)",
        )

    def handle(self, *args, **options):
        continuous = options["continuous"]
        interval = options["interval"]

        self.stdout.write(
            self.style.SUCCESS(
                "Starting Telegram Bot channels synchronization..."
            )
        )
        self.stdout.write(
            self.style.WARNING(
                "Note: This command only finds RECENT bot additions. "
                "For existing channels, use: python manage.py add_channel <chat_id>"
            )
        )
        self.stdout.write("")

        client = TelegramBotClient()

        # Check bot info first
        try:
            bot_info = client.get_bot_info_sync()
            if bot_info:
                self.stdout.write(
                    f"Connected to bot: @{bot_info.get('username')} "
                    f"(ID: {bot_info.get('bot_id')})"
                )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Failed to get bot info: {e}")
            )
            return

        if continuous:
            self.stdout.write(
                self.style.WARNING(
                    f"Running in continuous mode (interval: {interval}s). "
                    "Press Ctrl+C to stop."
                )
            )
            
            try:
                while True:
                    self._process_updates(client)
                    time.sleep(interval)
            except KeyboardInterrupt:
                self.stdout.write("\nStopped by user.")
        else:
            # Run once
            self._process_updates(client)

        self.stdout.write(
            self.style.SUCCESS("Synchronization completed.")
        )

    def _process_updates(self, client: TelegramBotClient):
        """Process bot updates and sync channels."""
        try:
            self.stdout.write("Processing bot updates...")
            
            result = client.process_updates_sync()
            
            if result:
                processed = result.get("processed", 0)
                results = result.get("results", [])
                
                self.stdout.write(f"Processed {processed} updates")
                
                # Log details
                for item in results:
                    update_id = item.get("update_id")
                    status = item.get("status")
                    update_type = item.get("type")
                    
                    if status == "processed":
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"  ✓ Update #{update_id} ({update_type}): {status}"
                            )
                        )
                    else:
                        self.stdout.write(
                            f"  - Update #{update_id} ({update_type}): {status}"
                        )
                
                if processed > 0:
                    # Show current channels
                    self._show_channels_summary()
            else:
                self.stdout.write("No updates to process")
                
        except TelegramBotGatewayError as e:
            self.stdout.write(
                self.style.ERROR(
                    f"Gateway error: [{e.code}] {e.message}"
                )
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error processing updates: {e}")
            )

    def _show_channels_summary(self):
        """Show summary of current channels."""
        channels = Channel.objects.filter(bot_admin=True)
        
        self.stdout.write("\nChannels where bot is admin:")
        if channels.exists():
            for channel in channels:
                status = "✓ Active" if channel.is_active else "✗ Inactive"
                permissions = []
                if channel.bot_can_post:
                    permissions.append("post")
                if channel.bot_can_edit:
                    permissions.append("edit")
                if channel.bot_can_delete:
                    permissions.append("delete")
                
                perms_str = ", ".join(permissions) if permissions else "no permissions"
                
                self.stdout.write(
                    f"  • {channel.title} (@{channel.username or 'private'}) "
                    f"[{status}] - {perms_str}"
                )
        else:
            self.stdout.write("  No channels found.")
            self.stdout.write("")
            self.stdout.write(
                self.style.WARNING("=" * 60)
            )
            self.stdout.write(
                self.style.WARNING("HOW TO ADD CHANNELS:")
            )
            self.stdout.write(
                self.style.WARNING("=" * 60)
            )
            self.stdout.write(
                "The Telegram Bot API doesn't provide a list of channels where"
            )
            self.stdout.write(
                "the bot is admin. Channels are discovered via events when"
            )
            self.stdout.write(
                "the bot is added to a channel."
            )
            self.stdout.write("")
            self.stdout.write("To add channels manually, use:")
            self.stdout.write(
                self.style.SUCCESS(
                    "  python manage.py add_channel <chat_id_or_username>"
                )
            )
            self.stdout.write("")
            self.stdout.write("Examples:")
            self.stdout.write("  python manage.py add_channel -1001234567890")
            self.stdout.write("  python manage.py add_channel @my_channel")
            self.stdout.write("  python manage.py add_channel -1001111 -1002222 @third")
            self.stdout.write("")
            self.stdout.write("With options:")
            self.stdout.write("  python manage.py add_channel @channel --language ru --primary")
            self.stdout.write("")
            self.stdout.write(
                self.style.WARNING(
                    "Tip: Find chat_id by forwarding a message from your channel to @userinfobot"
                )
            )
        
        self.stdout.write("")

