import requests
from django.core.management.base import BaseCommand
from apps.hik_adapter.services import HikPartnerService
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Automatically detect ngrok URL and register the Hik-Partner webhook"

    def add_arguments(self, parser):
        parser.add_argument(
            "--url", 
            type=str, 
            help="Manually specify the base ngrok URL (e.g., https://xyz.ngrok-free.app)"
        )

    def handle(self, *args, **options):
        service = HikPartnerService()
        
        # 1. Detect ngrok URL
        base_url = options.get("url")
        if not base_url:
            self.stdout.write("Detecting ngrok tunnel...")
            try:
                # Query local ngrok API
                ngrok_resp = requests.get("http://localhost:4040/api/tunnels", timeout=2)
                ngrok_resp.raise_for_status()
                tunnels = ngrok_resp.json().get("tunnels", [])
                
                # find the first https tunnel
                https_tunnels = [t for t in tunnels if t.get("proto") == "https" or t.get("public_url", "").startswith("https://")]
                if not https_tunnels:
                    self.stdout.write(self.style.ERROR("No active ngrok tunnels found. Is ngrok running?"))
                    return
                
                base_url = https_tunnels[0]["public_url"]
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Failed to detect ngrok: {e}"))
                self.stdout.write("Make sure ngrok is running on this machine.")
                return

        # 2. Construct the full callback path
        # Note: adjust this if your listener path changes
        callback_path = "/api/v1/alarms/webhook/"
        full_callback_url = f"{base_url.rstrip('/')}{callback_path}"

        self.stdout.write(self.style.SUCCESS(f"Registering Webhook: {full_callback_url}"))

        # 3. Register with Hik-Partner Pro
        try:
            result = service.save_webhook_config(callback_url=full_callback_url)
            if result.get("errorCode") == "0":
                self.stdout.write(self.style.SUCCESS("✓ Webhook registration successful!"))
            else:
                self.stdout.write(self.style.ERROR(f"✕ Platform error: {result.get('msg')} ({result.get('errorCode')})"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✕ Connection error: {e}"))
