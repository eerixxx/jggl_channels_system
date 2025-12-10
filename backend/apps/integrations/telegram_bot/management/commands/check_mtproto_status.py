"""Management command to check MTProto API status on Telegram Bot Gateway.

MTProto API provides detailed statistics:
- Exact views count per message
- Reactions breakdown by emoji
- Comments/replies count
- Forwards count
- Channel growth statistics

Usage:
    python manage.py check_mtproto_status
    python manage.py check_mtproto_status --connect
"""

import logging

from django.core.management.base import BaseCommand

from apps.integrations.telegram_bot.client import TelegramBotClient, TelegramBotGatewayError

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Check MTProto API status on Telegram Bot Gateway"

    def add_arguments(self, parser):
        parser.add_argument(
            "--connect",
            action="store_true",
            help="Attempt to connect MTProto client on gateway side",
        )

    def handle(self, *args, **options):
        connect = options["connect"]

        self.stdout.write(
            self.style.SUCCESS(
                "Checking MTProto API status on Telegram Bot Gateway..."
            )
        )

        client = TelegramBotClient()

        try:
            # Check MTProto status
            status = client.get_mtproto_status_sync()
            
            if not status:
                self.stdout.write(
                    self.style.ERROR("Failed to get MTProto status")
                )
                return

            enabled = status.get("enabled", False)
            available = status.get("available", False)
            connected = status.get("connected", False)
            has_api_id = status.get("has_api_id", False)
            has_api_hash = status.get("has_api_hash", False)
            has_session = status.get("has_session", False)

            self.stdout.write("\nMTProto API Status:")
            self.stdout.write(f"  Enabled:    {self._status_icon(enabled)} {enabled}")
            self.stdout.write(f"  Available:  {self._status_icon(available)} {available}")
            self.stdout.write(f"  Connected:  {self._status_icon(connected)} {connected}")
            self.stdout.write(f"  Has API ID: {self._status_icon(has_api_id)} {has_api_id}")
            self.stdout.write(f"  Has Hash:   {self._status_icon(has_api_hash)} {has_api_hash}")
            self.stdout.write(f"  Has Session:{self._status_icon(has_session)} {has_session}")

            if enabled and connected:
                self.stdout.write(
                    self.style.SUCCESS(
                        "\n✅ MTProto API is ENABLED and CONNECTED"
                    )
                )
                self.stdout.write(
                    "Backend will automatically use MTProto for detailed statistics."
                )
            elif enabled and not connected:
                self.stdout.write(
                    self.style.WARNING(
                        "\n⚠️ MTProto API is ENABLED but NOT CONNECTED"
                    )
                )
                if connect:
                    self.stdout.write("Attempting to connect...")
                    success = client.connect_mtproto_sync()
                    if success:
                        self.stdout.write(
                            self.style.SUCCESS("✅ MTProto connected successfully!")
                        )
                    else:
                        self.stdout.write(
                            self.style.ERROR("❌ Failed to connect MTProto")
                        )
                else:
                    self.stdout.write(
                        "Run with --connect to attempt connection."
                    )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        "\n⚠️ MTProto API is NOT ENABLED"
                    )
                )
                self.stdout.write(
                    "\nTo enable MTProto on Gateway, set these environment variables:"
                )
                self.stdout.write("  MTPROTO_ENABLED=true")
                self.stdout.write("  TELEGRAM_API_ID=<your api id from my.telegram.org>")
                self.stdout.write("  TELEGRAM_API_HASH=<your api hash>")
                self.stdout.write("  TELEGRAM_SESSION_STRING=<session string>")
                self.stdout.write(
                    "\nWithout MTProto, only basic statistics (member count) will be available."
                )

        except TelegramBotGatewayError as e:
            self.stdout.write(
                self.style.ERROR(
                    f"Gateway error: [{e.code}] {e.message}"
                )
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error: {e}")
            )

    def _status_icon(self, value: bool) -> str:
        """Return colored icon based on boolean value."""
        return "✓" if value else "✗"

