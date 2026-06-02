import time
import logging
from django.core.management.base import BaseCommand
from apps.hik_adapter.services import HikPartnerService

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Run Hik MQ listener for real-time event polling"

    def handle(self, *args, **options):
        service = HikPartnerService()
        client = service.client

        self.stdout.write(self.style.SUCCESS("--- Starting Hik MQ listener ---"))
        self.stdout.write(self.style.WARNING("Note: Webhooks are also active via Ngrok."))

        # Subscribe to all events
        try:
            client.subscribe_events()
            self.stdout.write(self.style.SUCCESS("MQ subscription successful"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"MQ subscription failed: {e}"))

        while True:
            try:
                # blocks for up to 20s
                response = client.poll_messages()
                data = response.get("data", {})

                # Robust message extraction as suggested
                messages = data.get("list") or data.get("data") or []
                batch_id = data.get("batchId")

                if messages:
                    self.stdout.write(self.style.SUCCESS(f"Received {len(messages)} events"))
                    failed = 0
                    
                    for msg in messages:
                        try:
                            # Process and Sync state
                            event = service.process_mq_message(msg)
                            if event:
                                self.stdout.write(self.style.SUCCESS(f"  Processed: {event.event_type} (Serial: {msg.get('deviceSerial')})"))
                        except Exception as e:
                            failed += 1
                            logger.error("Failed to process message: %s", e)

                    # Confirm batch receipt only after every message is processed.
                    if batch_id and failed == 0:
                        client.confirm_messages(batch_id)
                    elif batch_id:
                        logger.warning(
                            "Leaving MQ batch %s unacknowledged after %d failure(s)",
                            batch_id,
                            failed,
                        )
                
            except Exception as e:
                logger.error("MQ polling error: %s", e)
                self.stdout.write(self.style.ERROR(f"Polling error: {e}"))

            # Small sleep to prevent tight loop on error
            time.sleep(1)
