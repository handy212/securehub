from datetime import date, timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.cache import cache
from django.core import mail
from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse
from django.utils import timezone
import json

from apps.alarms.models import AlarmEvent
from apps.communication.models import BroadcastMessage
from apps.dashboard.console_auth import CONSOLE_LOGIN_ATTEMPT_LIMIT
from apps.hik_adapter.exceptions import HikPartnerError
from apps.accounts.models import StaffOperatorProfile
from apps.accounts.rbac import OperatorRole
from apps.sites.models import (
    AlarmOutput,
    AlarmPanelDevice,
    AlarmPeripheral,
    CustomerSiteAccess,
    OperationsZone,
    Site,
    Subscription,
    SubscriptionPayment,
    Subsystem,
    Zone,
)


class DashboardFlowTests(TestCase):
    def setUp(self):
        cache.clear()
        self.staff = User.objects.create_user(
            username="staff-operator",
            email="staff-operator@example.com",
            password="Secret123!",
            is_staff=True,
        )
        StaffOperatorProfile.objects.get_or_create(
            user=self.staff,
            defaults={"role": OperatorRole.OPERATIONS},
        )
        self.platform_staff = User.objects.create_user(
            username="platform-operator",
            email="platform-operator@example.com",
            password="Secret123!",
            is_staff=True,
        )
        StaffOperatorProfile.objects.get_or_create(
            user=self.platform_staff,
            defaults={"role": OperatorRole.PLATFORM_ADMIN},
        )
        self.billing_staff = User.objects.create_user(
            username="billing-operator",
            email="billing-operator@example.com",
            password="Secret123!",
            is_staff=True,
        )
        StaffOperatorProfile.objects.get_or_create(
            user=self.billing_staff,
            defaults={"role": OperatorRole.BILLING},
        )
        self.superuser = User.objects.create_user(
            username="super-operator",
            password="Secret123!",
            is_staff=True,
            is_superuser=True,
        )
        self.regular = User.objects.create_user(
            username="regular-user",
            password="Secret123!",
        )
        self.site = Site.objects.create(name="HQ", hik_site_id="hik-site-100")

    def test_non_staff_cannot_access_console_settings(self):
        self.client.force_login(self.regular)

        response = self.client.get(reverse("dashboard:settings"))

        self.assertEqual(response.status_code, 403)

    def test_console_login_locks_after_repeated_failures(self):
        for _ in range(CONSOLE_LOGIN_ATTEMPT_LIMIT):
            response = self.client.post(
                reverse("dashboard:login"),
                {
                    "username": self.staff.username,
                    "password": "wrong-password",
                    "next": reverse("dashboard:home"),
                },
            )
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "Invalid credentials or insufficient permissions.")

        locked_response = self.client.post(
            reverse("dashboard:login"),
            {
                "username": self.staff.username,
                "password": "Secret123!",
                "next": reverse("dashboard:home"),
            },
        )

        self.assertEqual(locked_response.status_code, 200)
        self.assertContains(locked_response, "Too many sign-in attempts. Please wait a few minutes and try again.")

    def test_console_login_accepts_email(self):
        response = self.client.post(
            reverse("dashboard:login"),
            {
                "username": "staff-operator@example.com",
                "password": "Secret123!",
                "next": reverse("dashboard:home"),
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("dashboard:home"))

    def test_console_password_reset_sends_email(self):
        response = self.client.post(
            reverse("dashboard:password-reset"),
            {"email": "staff-operator@example.com"},
            HTTP_HOST="console.testserver",
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/console/password-reset/done/")
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("console.testserver/console/password-reset/", mail.outbox[0].body)

    def test_staff_sees_platform_status_and_global_map_labels(self):
        self.client.force_login(self.platform_staff)

        settings_response = self.client.get(reverse("dashboard:settings"))
        map_response = self.client.get(reverse("dashboard:site-map"))

        self.assertContains(settings_response, "Platform Status")
        self.assertContains(settings_response, "Live ops")
        self.assertContains(map_response, "Global Map")
        self.assertContains(map_response, "Fit view")
        self.assertContains(map_response, "Legend")

    def test_logs_filter_uses_event_category_and_display_name(self):
        AlarmEvent.objects.create(
            site=self.site,
            event_type="PanelStatus(Power&Battery)",
            event_category=AlarmEvent.CATEGORY_HEALTH,
            severity=AlarmEvent.SEVERITY_MEDIUM,
            event_code="cidEvent",
            payload={
                "event_name": "Panel Power Status",
                "normalized_event_type": "panel_power_status",
            },
            occurred_at=timezone.now(),
        )
        AlarmEvent.objects.create(
            site=self.site,
            event_type="SystemOperation",
            event_category=AlarmEvent.CATEGORY_SYSTEM,
            severity=AlarmEvent.SEVERITY_LOW,
            event_code="cidEvent",
            payload={
                "event_name": "System Operation",
                "normalized_event_type": "system_operation",
            },
            occurred_at=timezone.now(),
        )
        self.client.force_login(self.staff)

        response = self.client.get(reverse("dashboard:logs"), {"type": "health"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Panel Power Status")
        events = list(response.context["events"])
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].payload["event_name"], "Panel Power Status")
        self.assertEqual(events[0].event_category, AlarmEvent.CATEGORY_HEALTH)

    def test_site_console_shows_alarm_module_inventory(self):
        device = AlarmPanelDevice.objects.create(
            site=self.site,
            name="AX Pro",
            serial_number="SN-AX-1",
            hik_device_id="hik-dev-1",
            is_online=True,
        )
        AlarmPeripheral.objects.create(
            site=self.site,
            device=device,
            peripheral_type=AlarmPeripheral.TYPE_SIREN,
            peripheral_number=1,
            name="Front Siren",
            is_online=True,
        )
        AlarmOutput.objects.create(
            site=self.site,
            device=device,
            output_number=1,
            name="Gate Relay",
            status="on",
            is_online=True,
        )
        self.client.force_login(self.staff)

        response = self.client.get(reverse("dashboard:site-console", args=[self.site.pk]))

        self.assertContains(response, "Alarm Inventory")
        self.assertContains(response, "Installed Modules & Outputs")
        self.assertContains(response, "Front Siren")
        self.assertContains(response, "Gate Relay")
        self.assertEqual(len(response.context["alarm_module_peripherals"]), 1)
        self.assertEqual(response.context["alarm_module_peripherals"][0]["name"], "Front Siren")
        self.assertEqual(response.context["inventory_counts"]["outputs"], 1)

    def test_site_console_normalizes_panel_power_status_labels(self):
        device = AlarmPanelDevice.objects.create(
            site=self.site,
            name="AX Pro",
            serial_number="SN-AX-PWR",
            hik_device_id="hik-dev-pwr",
            is_online=True,
            battery_status="normal",
        )
        self.client.force_login(self.staff)

        response = self.client.get(reverse("dashboard:site-console", args=[self.site.pk]))

        self.assertContains(response, "Mains OK")
        self.assertEqual(response.context["devices"][0].power_status_label, "Mains OK")

    def test_site_console_lists_only_installed_module_devices(self):
        device = AlarmPanelDevice.objects.create(
            site=self.site,
            name="AX Pro",
            serial_number="SN-AX-2",
            hik_device_id="hik-dev-2",
            is_online=True,
        )
        subsystem = Subsystem.objects.create(
            site=self.site,
            device=device,
            name="Area 1",
            hik_subsystem_id="sub-1",
            subsystem_number=1,
        )
        Zone.objects.create(
            subsystem=subsystem,
            name="Remote Fob 1",
            zone_number=2,
            device_type=Zone.DEVICE_TYPE_KEYFOB,
            is_online=True,
            signal_strength="strong",
        )
        self.client.force_login(self.staff)

        response = self.client.get(reverse("dashboard:site-console", args=[self.site.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Keyfobs")
        self.assertEqual(response.context["inventory_counts"]["keyfobs"], 0)
        self.assertEqual(response.context["alarm_peripherals"], [])
        self.assertEqual(response.context["alarm_module_peripherals"], [])

    def test_site_console_excludes_not_related_outputs_from_module_section(self):
        device = AlarmPanelDevice.objects.create(
            site=self.site,
            name="AX Pro",
            serial_number="SN-AX-OUT",
            hik_device_id="hik-dev-out",
            is_online=True,
        )
        AlarmOutput.objects.create(
            site=self.site,
            device=device,
            output_number=1,
            name="Real Relay",
            status="offline",
            is_online=False,
        )
        AlarmOutput.objects.create(
            site=self.site,
            device=device,
            output_number=2,
            name="Capacity Slot",
            status="notRelated",
            is_online=False,
        )
        self.client.force_login(self.staff)

        response = self.client.get(reverse("dashboard:site-console", args=[self.site.pk]))

        self.assertEqual(response.status_code, 200)
        output_names = [output.name for output in response.context["alarm_outputs"]]
        self.assertEqual(output_names, ["Real Relay"])
        self.assertEqual(response.context["inventory_counts"]["outputs"], 1)
        self.assertContains(response, "Real Relay")
        self.assertNotContains(response, "Capacity Slot")

    def test_site_console_provides_enriched_recent_event_payload(self):
        device = AlarmPanelDevice.objects.create(
            site=self.site,
            name="AX Pro",
            serial_number="SN-AX-EVT",
            hik_device_id="hik-dev-evt",
            is_online=True,
        )
        subsystem = Subsystem.objects.create(
            site=self.site,
            device=device,
            name="Area 1",
            hik_subsystem_id="sub-evt-1",
            subsystem_number=1,
        )
        zone = Zone.objects.create(
            subsystem=subsystem,
            name="Front Door PIR",
            zone_number=1,
            device_type=Zone.DEVICE_TYPE_ZONE,
            is_online=True,
        )
        AlarmEvent.objects.create(
            site=self.site,
            subsystem=subsystem,
            zone=zone,
            event_type="cidEvent",
            event_category=AlarmEvent.CATEGORY_ALARM,
            severity=AlarmEvent.SEVERITY_CRITICAL,
            performed_by="Operator Desk",
            payload={
                "event_name": "Intrusion Alarm",
                "normalized_event_type": "alarm_triggered",
                "pictures": [{"url": "https://example.com/frame1.jpg"}],
            },
            occurred_at=timezone.now(),
        )
        self.client.force_login(self.staff)

        response = self.client.get(reverse("dashboard:site-console", args=[self.site.pk]))

        self.assertEqual(response.status_code, 200)
        recent_events_payload = response.context["recent_events_payload"]
        self.assertEqual(len(recent_events_payload), 1)
        payload = recent_events_payload[0]
        self.assertEqual(payload["displayName"], "Intrusion Alarm")
        self.assertEqual(payload["typeLabel"], "Alarm Triggered")
        self.assertEqual(payload["categoryLabel"], "Alarm")
        self.assertEqual(payload["severityLabel"], "Critical")
        self.assertEqual(payload["locationLabel"], "Front Door PIR")
        self.assertEqual(payload["operatorLabel"], "Operator Desk")
        self.assertTrue(payload["hasPictures"])
        self.assertEqual(payload["mediaCount"], 1)

    @patch("apps.alarms.media.probe_remote_media_type")
    def test_event_pictures_merges_related_snapshot_image_and_video(self, mock_probe_remote_media_type):
        def _probe(url: str):
            if "clip-asset" in url:
                return "video"
            return "image"

        mock_probe_remote_media_type.side_effect = _probe

        device = AlarmPanelDevice.objects.create(
            site=self.site,
            name="AX Pro",
            serial_number="SN-AX-MEDIA",
            hik_device_id="hik-dev-media",
            is_online=True,
        )
        subsystem = Subsystem.objects.create(
            site=self.site,
            device=device,
            name="Area 1",
            hik_subsystem_id="sub-media-1",
            subsystem_number=1,
        )
        zone = Zone.objects.create(
            subsystem=subsystem,
            name="Motion Cam Sensor",
            zone_number=1,
            device_type=Zone.DEVICE_TYPE_ZONE,
            is_online=True,
        )
        relation_id = "rel-12345"
        snapshot_event = AlarmEvent.objects.create(
            site=self.site,
            subsystem=subsystem,
            zone=zone,
            event_type="Snapshot",
            event_code="Snapshot",
            event_category=AlarmEvent.CATEGORY_INFO,
            severity=AlarmEvent.SEVERITY_LOW,
            payload={
                "event_name": "Snapshot Captured",
                "normalized_event_type": "snapshot_captured",
                "alarmData": {
                    "relationId": relation_id,
                    "triggerTime": "2026-04-22T15:05:54",
                    "pictureList": [
                        {"id": "snap-1", "url": "https://example.com/image-asset"},
                    ],
                },
                "pictures": [
                    {"id": "snap-1", "url": "https://example.com/image-asset", "type": "image"},
                ],
            },
            occurred_at=timezone.now(),
        )
        AlarmEvent.objects.create(
            site=self.site,
            subsystem=subsystem,
            zone=zone,
            event_type="MobileZoneInstantAlarm",
            event_code="cidEvent",
            event_category=AlarmEvent.CATEGORY_ALARM,
            severity=AlarmEvent.SEVERITY_CRITICAL,
            payload={
                "event_name": "Instant Zone Alarm",
                "normalized_event_type": "instant_zone_alarm",
                "alarmData": {
                    "relationId": relation_id,
                    "triggerTime": "2026-04-22T15:05:54",
                    "isVideo": 2,
                },
                "pictures": [
                    {"id": "clip-1", "url": "https://example.com/clip-asset", "type": "image"},
                ],
            },
            occurred_at=timezone.now(),
        )
        self.client.force_login(self.staff)

        response = self.client.get(
            reverse("dashboard:event-pictures", args=[self.site.pk, snapshot_event.id])
        )

        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content)
        self.assertEqual(len(payload["pictures"]), 2)
        self.assertEqual(payload["pictures"][0]["type"], "image")
        self.assertEqual(payload["pictures"][1]["type"], "video")
        self.assertEqual(
            [item["url"] for item in payload["pictures"]],
            ["https://example.com/image-asset", "https://example.com/clip-asset"],
        )

    def test_site_console_hides_snapshot_rows_and_humanizes_related_alarm_names(self):
        device = AlarmPanelDevice.objects.create(
            site=self.site,
            name="AX Pro",
            serial_number="SN-AX-FEED",
            hik_device_id="hik-dev-feed",
            is_online=True,
        )
        subsystem = Subsystem.objects.create(
            site=self.site,
            device=device,
            name="Area 1",
            hik_subsystem_id="sub-feed-1",
            subsystem_number=1,
        )
        zone = Zone.objects.create(
            subsystem=subsystem,
            name="Motion Cam Sensor",
            zone_number=1,
            device_type=Zone.DEVICE_TYPE_ZONE,
            is_online=True,
        )
        relation_id = "rel-feed-123"
        AlarmEvent.objects.create(
            site=self.site,
            subsystem=subsystem,
            zone=zone,
            event_type="Snapshot",
            event_code="Snapshot",
            event_category=AlarmEvent.CATEGORY_INFO,
            severity=AlarmEvent.SEVERITY_LOW,
            payload={
                "event_name": "Snapshot",
                "normalized_event_type": "snapshot_captured",
                "alarmData": {
                    "relationId": relation_id,
                    "triggerTime": "2026-04-22T15:05:54",
                },
                "pictures": [
                    {"id": "snap-1", "url": "https://example.com/image-asset", "type": "image"},
                ],
            },
            occurred_at=timezone.now(),
        )
        AlarmEvent.objects.create(
            site=self.site,
            subsystem=subsystem,
            zone=zone,
            event_type="MobileZoneInstantAlarm",
            event_code="cidEvent",
            event_category=AlarmEvent.CATEGORY_ALARM,
            severity=AlarmEvent.SEVERITY_CRITICAL,
            payload={
                "event_name": "MobileZoneInstantAlarm",
                "normalized_event_type": "instant_zone_alarm",
                "alarmData": {
                    "relationId": relation_id,
                    "triggerTime": "2026-04-22T15:05:54",
                    "isVideo": 2,
                },
                "pictures": [
                    {"id": "clip-1", "url": "https://example.com/clip-asset", "type": "video"},
                ],
            },
            occurred_at=timezone.now(),
        )
        self.client.force_login(self.staff)

        response = self.client.get(reverse("dashboard:site-console", args=[self.site.pk]))

        self.assertEqual(response.status_code, 200)
        recent_events_payload = response.context["recent_events_payload"]
        self.assertEqual(len(recent_events_payload), 1)
        self.assertEqual(recent_events_payload[0]["displayName"], "Instant Zone Alarm")
        self.assertEqual(recent_events_payload[0]["typeLabel"], "Instant Zone Alarm")
        self.assertEqual(recent_events_payload[0]["mediaCount"], 2)

    def test_site_console_panic_form_keeps_modal_open_until_submit_completes(self):
        self.client.force_login(self.staff)

        response = self.client.get(reverse("dashboard:site-console", args=[self.site.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '@submit="actionBusy = true"')
        self.assertNotContains(response, 'actionBusy = true; panicModal = false')

    @patch("apps.dashboard.views_sites.HikPartnerService.get_site_panic_capability")
    def test_site_console_marks_silent_panic_unavailable_when_panel_is_audible_only(self, mock_capability):
        mock_capability.return_value = {
            "audible_enabled": True,
            "silent_enabled": False,
            "mode": "one_key_alarm",
            "summary_message": "This site supports audible panic only through Hik-Partner Pro.",
            "panels": [{"panel": "SN-AX-ONLY", "mode": "one_key_alarm"}],
        }
        self.client.force_login(self.staff)

        response = self.client.get(reverse("dashboard:site-console", args=[self.site.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This site supports audible panic only through Hik-Partner Pro.")
        self.assertContains(response, "Silent panic unavailable")
        self.assertNotContains(response, 'name="panic_type" value="silent"', html=False)

    @patch("apps.dashboard.views_sites.HikPartnerService.trigger_global_panic")
    @patch("apps.dashboard.views_sites.HikPartnerService.get_site_panic_capability")
    def test_panic_action_rejects_unsupported_silent_panic_before_dispatch(
        self,
        mock_capability,
        mock_trigger_global_panic,
    ):
        mock_capability.return_value = {
            "audible_enabled": True,
            "silent_enabled": False,
            "mode": "one_key_alarm",
            "summary_message": "This site supports audible panic only through Hik-Partner Pro.",
            "panels": [{"panel": "SN-AX-ONLY", "mode": "one_key_alarm"}],
        }
        self.client.force_login(self.staff)

        response = self.client.post(
            reverse("dashboard:site-action", args=[self.site.pk, "panic"]),
            {"panic_type": "silent"},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This site supports audible panic only through Hik-Partner Pro.")
        mock_trigger_global_panic.assert_not_called()

    @patch("apps.dashboard.views_ops.HikPartnerService.geocode_site_location")
    def test_global_map_backfills_coordinates_for_site_with_address(self, mock_geocode):
        self.site.address = "15 Industrial Estate"
        self.site.city = "Accra"
        self.site.state = "Greater Accra"
        self.site.save(update_fields=["address", "city", "state", "updated_at"])

        def geocode(site, force=False):
            site.latitude = "5.6037"
            site.longitude = "-0.1870"
            site.save(update_fields=["latitude", "longitude", "updated_at"])
            return True

        mock_geocode.side_effect = geocode
        self.client.force_login(self.staff)

        response = self.client.get(reverse("dashboard:site-map"))

        payload = response.context["sites_data"]
        self.assertEqual(payload[0]["name"], "HQ")
        self.assertEqual(payload[0]["lat"], 5.6037)

    def test_onboarding_can_link_existing_user_and_create_subscription(self):
        existing_user = User.objects.create_user(
            username="client-1",
            email="client@example.com",
            password="Secret123!",
        )
        self.client.force_login(self.staff)

        response = self.client.post(
            reverse("dashboard:onboard-client", args=[self.site.pk]),
            {
                "first_name": "Client",
                "last_name": "User",
                "email": "client@example.com",
                "username": "client-1",
                "phone": "+123456789",
                "role": "manager",
                "can_control_alarm": "on",
                "monthly_rate": "199.99",
                "next_due_date": "2026-05-01",
                "grace_period_days": "14",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.filter(email="client@example.com").count(), 1)
        access = CustomerSiteAccess.objects.get(user=existing_user, site=self.site)
        self.assertEqual(access.role, CustomerSiteAccess.ROLE_MANAGER)
        self.assertTrue(access.can_control_alarm)
        subscription = Subscription.objects.get(site=self.site)
        self.assertEqual(subscription.grace_period_days, 14)
        self.assertEqual(str(subscription.monthly_rate), "199.99")
        self.assertEqual(subscription.billing_day, 1)

    def test_site_console_shows_add_user_when_owner_already_assigned(self):
        owner = User.objects.create_user(
            username="owner-client",
            email="owner@example.com",
            password="Secret123!",
        )
        CustomerSiteAccess.objects.create(
            user=owner,
            site=self.site,
            role=CustomerSiteAccess.ROLE_OWNER,
        )
        self.client.force_login(self.staff)

        response = self.client.get(reverse("dashboard:site-console", args=[self.site.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Add User")
        self.assertNotContains(response, "Complete Onboarding")
        self.assertNotContains(response, "Site Pending Activation")
        self.assertTrue(response.context["has_owner_access"])

    def test_site_console_still_requires_owner_when_only_viewer_assigned(self):
        viewer = User.objects.create_user(
            username="viewer-client",
            email="viewer@example.com",
            password="Secret123!",
        )
        CustomerSiteAccess.objects.create(
            user=viewer,
            site=self.site,
            role=CustomerSiteAccess.ROLE_VIEWER,
        )
        self.client.force_login(self.staff)

        response = self.client.get(reverse("dashboard:site-console", args=[self.site.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Assign Owner")
        self.assertContains(response, "No owner assigned")
        self.assertFalse(response.context["has_owner_access"])

    def test_site_console_hides_billing_shortcut_when_subscription_exists(self):
        Subscription.objects.create(
            site=self.site,
            monthly_rate="100.00",
            billing_day=1,
            grace_period_days=7,
            next_due_date=date(2026, 5, 1),
        )
        self.client.force_login(self.staff)

        response = self.client.get(reverse("dashboard:site-console", args=[self.site.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["readiness"]["has_subscription"])
        self.assertNotContains(response, "data-readiness-billing-action")

    def test_site_console_shows_readiness_billing_action_when_subscription_missing(self):
        self.client.force_login(self.staff)

        response = self.client.get(reverse("dashboard:site-console", args=[self.site.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["readiness"]["has_subscription"])
        self.assertContains(response, "data-readiness-billing-action")
        self.assertNotContains(response, "Live Status")

    def test_site_console_active_faults_ignore_historical_alarm_events(self):
        for index in range(2):
            AlarmEvent.objects.create(
                site=self.site,
                event_type="MobileZoneInstantAlarm",
                event_category=AlarmEvent.CATEGORY_ALARM,
                severity=AlarmEvent.SEVERITY_CRITICAL,
                payload={"event_name": "Instant Zone Alarm"},
                occurred_at=timezone.now() - timedelta(hours=index + 1),
            )
        self.client.force_login(self.staff)

        response = self.client.get(reverse("dashboard:site-console", args=[self.site.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["active_fault_count"], 0)
        self.assertEqual(response.context["system_faults"], 0)
        self.assertEqual(response.context["active_faults_payload"], [])

    def test_site_status_poll_returns_current_active_faults(self):
        device = AlarmPanelDevice.objects.create(
            site=self.site,
            name="AX Pro",
            serial_number="SN-FAULT-1",
            hik_device_id="hik-fault-1",
            is_online=True,
        )
        subsystem = Subsystem.objects.create(
            site=self.site,
            device=device,
            name="Area 1",
            hik_subsystem_id="sub-fault-1",
            subsystem_number=1,
            status=Subsystem.STATUS_DISARMED,
        )
        Zone.objects.create(
            subsystem=subsystem,
            name="Front Door",
            zone_number=1,
            state=Zone.STATE_ALARM,
        )
        self.client.force_login(self.staff)

        response = self.client.get(reverse("site-status-poll", args=[self.site.pk]))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["activeFaultCount"], 1)
        self.assertEqual(payload["activeFaults"][0]["label"], "Zone Alarm")
        self.assertEqual(payload["activeFaults"][0]["source"], "Front Door")

    def test_site_console_disables_controls_when_no_panels_are_online(self):
        device = AlarmPanelDevice.objects.create(
            site=self.site,
            name="AX Pro",
            serial_number="SN-OFFLINE-1",
            hik_device_id="hik-offline-1",
            is_online=False,
        )
        Subsystem.objects.create(
            site=self.site,
            device=device,
            name="Area 1",
            hik_subsystem_id="sub-offline-1",
            subsystem_number=1,
        )
        self.client.force_login(self.staff)

        response = self.client.get(reverse("dashboard:site-console", args=[self.site.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["has_online_control_areas"])
        self.assertContains(response, "Controls paused: no online panels are available.")

    @patch("apps.dashboard.views_sites.HikPartnerService.execute_subsystem_command")
    def test_global_arm_treats_hik_unreachable_as_offline_skip(self, mock_execute):
        device = AlarmPanelDevice.objects.create(
            site=self.site,
            name="AX Pro",
            serial_number="SN-STALE-ONLINE",
            hik_device_id="hik-stale-online",
            is_online=True,
        )
        Subsystem.objects.create(
            site=self.site,
            device=device,
            name="Area 1",
            hik_subsystem_id="sub-stale-1",
            subsystem_number=1,
        )
        mock_execute.side_effect = HikPartnerError(
            "Panel is offline or unreachable.",
            error_code="LAP020011",
        )
        self.client.force_login(self.staff)

        response = self.client.post(
            reverse("dashboard:site-action", args=[self.site.pk, "arm"]),
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Skipped 1 offline or unreachable area")
        self.assertNotContains(response, "Global arm failed")

    def test_onboarding_with_past_due_billing_classifies_status(self):
        self.client.force_login(self.staff)

        response = self.client.post(
            reverse("dashboard:onboard-client", args=[self.site.pk]),
            {
                "email": "past-due@example.com",
                "username": "past-due",
                "role": "owner",
                "monthly_rate": "199.99",
                "next_due_date": (date.today() - timedelta(days=10)).isoformat(),
                "grace_period_days": "7",
            },
        )

        self.assertEqual(response.status_code, 200)
        subscription = Subscription.objects.get(site=self.site)
        self.assertEqual(subscription.status, Subscription.STATUS_SUSPENDED)
        self.assertIsNotNone(subscription.suspended_at)

    def test_onboarding_new_viewer_forces_control_off(self):
        self.client.force_login(self.staff)

        response = self.client.post(
            reverse("dashboard:onboard-client", args=[self.site.pk]),
            {
                "first_name": "Viewer",
                "last_name": "Only",
                "email": "viewer@example.com",
                "username": "viewer-only",
                "role": "viewer",
                "can_control_alarm": "on",
            },
        )

        self.assertEqual(response.status_code, 200)
        access = CustomerSiteAccess.objects.get(site=self.site, user__username="viewer-only")
        self.assertFalse(access.can_control_alarm)

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        SECUREHUB_APP_LINKS={
            "android": "https://play.example.com/securehub",
            "ios": "https://apps.example.com/securehub",
            "web": "https://app.securehub.test/login",
            "support": "https://securehub.test/help",
        },
    )
    def test_onboarding_sends_welcome_email_with_app_links(self):
        self.client.force_login(self.staff)

        response = self.client.post(
            reverse("dashboard:onboard-client", args=[self.site.pk]),
            {
                "first_name": "Client",
                "last_name": "Owner",
                "email": "owner@example.com",
                "username": "owner-user",
                "role": "owner",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["client_password"])
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertIn("owner-user", email.body)
        self.assertIn("Android app: https://play.example.com/securehub", email.body)
        self.assertIn("iPhone app: https://apps.example.com/securehub", email.body)
        self.assertIn("Web portal: https://app.securehub.test/login", email.body)
        self.assertIn("SecureHub does not send passwords by email.", email.body)
        self.assertNotIn(response.context["client_password"], email.body)

    def test_create_subscription_rejects_invalid_billing_day(self):
        self.client.force_login(self.billing_staff)

        response = self.client.post(
            reverse("dashboard:subscription-create"),
            {
                "site_id": str(self.site.pk),
                "monthly_rate": "100.00",
                "billing_day": "31",
                "grace_period_days": "7",
                "next_due_date": "2026-05-01",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Subscription.objects.filter(site=self.site).exists())

    def test_create_subscription_with_past_due_date_starts_overdue(self):
        self.client.force_login(self.billing_staff)

        response = self.client.post(
            reverse("dashboard:subscription-create"),
            {
                "site_id": str(self.site.pk),
                "monthly_rate": "100.00",
                "billing_day": "1",
                "grace_period_days": "7",
                "next_due_date": (date.today() - timedelta(days=1)).isoformat(),
            },
        )

        self.assertEqual(response.status_code, 302)
        subscription = Subscription.objects.get(site=self.site)
        self.assertEqual(subscription.status, Subscription.STATUS_OVERDUE)

    def test_record_payment_rejects_invalid_period_order(self):
        subscription = Subscription.objects.create(
            site=self.site,
            monthly_rate="100.00",
            billing_day=1,
            grace_period_days=7,
            next_due_date=date(2026, 5, 1),
        )
        self.client.force_login(self.billing_staff)

        response = self.client.post(
            reverse("dashboard:subscription-pay", args=[subscription.pk]),
            {
                "amount": "100.00",
                "period_start": "2026-05-31",
                "period_end": "2026-05-01",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        subscription.refresh_from_db()
        self.assertEqual(subscription.payments.count(), 0)
        self.assertEqual(subscription.next_due_date, date(2026, 5, 1))

    def test_record_payment_rejects_overlapping_period(self):
        subscription = Subscription.objects.create(
            site=self.site,
            monthly_rate="100.00",
            billing_day=1,
            grace_period_days=7,
            next_due_date=date(2026, 5, 1),
        )
        SubscriptionPayment.objects.create(
            subscription=subscription,
            amount="100.00",
            period_start=date(2026, 4, 1),
            period_end=date(2026, 4, 30),
            recorded_by=self.staff,
        )
        self.client.force_login(self.billing_staff)

        response = self.client.post(
            reverse("dashboard:subscription-pay", args=[subscription.pk]),
            {
                "amount": "100.00",
                "period_start": "2026-04-15",
                "period_end": "2026-05-14",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(subscription.payments.count(), 1)
        self.assertContains(response, "Payment periods cannot overlap existing records for this site.")

    def test_suspend_subscription_handles_already_suspended(self):
        subscription = Subscription.objects.create(
            site=self.site,
            monthly_rate="100.00",
            billing_day=1,
            grace_period_days=7,
            next_due_date=date(2026, 5, 1),
            status=Subscription.STATUS_SUSPENDED,
        )
        self.client.force_login(self.billing_staff)

        response = self.client.post(
            reverse("dashboard:subscription-suspend", args=[subscription.pk]),
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("dashboard:site-console", args=[self.site.pk]))

    @patch("apps.dashboard.views.send_suspension_notice.delay")
    def test_manual_suspend_sends_notice(self, mock_notice):
        client_user = User.objects.create_user(
            username="notice-client",
            email="notice@example.com",
            password="Secret123!",
        )
        CustomerSiteAccess.objects.create(
            user=client_user,
            site=self.site,
            role=CustomerSiteAccess.ROLE_OWNER,
        )
        subscription = Subscription.objects.create(
            site=self.site,
            monthly_rate="100.00",
            billing_day=1,
            grace_period_days=7,
            next_due_date=date(2026, 5, 1),
            status=Subscription.STATUS_ACTIVE,
        )
        self.client.force_login(self.billing_staff)

        response = self.client.post(
            reverse("dashboard:subscription-suspend", args=[subscription.pk]),
        )

        self.assertEqual(response.status_code, 302)
        subscription.refresh_from_db()
        self.assertEqual(subscription.status, Subscription.STATUS_SUSPENDED)
        mock_notice.assert_called_once_with(str(subscription.id))

    def test_staff_user_management_requires_superuser(self):
        self.client.force_login(self.staff)

        response = self.client.post(
            reverse("dashboard:user-update", args=[self.staff.pk]),
            {
                "username": self.staff.username,
                "email": "staff-operator@example.com",
                "is_active": "on",
                "is_superuser": "on",
            },
        )

        self.assertEqual(response.status_code, 403)
        self.staff.refresh_from_db()
        self.assertFalse(self.staff.is_superuser)

    def test_staff_user_can_be_created_and_updated_in_console(self):
        self.client.force_login(self.superuser)

        create_response = self.client.post(
            reverse("dashboard:user-create"),
            {
                "username": "new-staff",
                "email": "staff@example.com",
                "password": "SecurePass123!",
                "is_superuser": "on",
            },
        )
        self.assertEqual(create_response.status_code, 302)
        staff_user = User.objects.get(username="new-staff")
        self.assertTrue(staff_user.is_staff)
        self.assertTrue(staff_user.is_superuser)

        update_response = self.client.post(
            reverse("dashboard:user-update", args=[staff_user.pk]),
            {
                "username": "new-staff",
                "email": "ops@example.com",
                "first_name": "Ops",
                "last_name": "Lead",
                "is_active": "on",
            },
        )
        self.assertEqual(update_response.status_code, 302)
        staff_user.refresh_from_db()
        self.assertEqual(staff_user.email, "ops@example.com")
        self.assertEqual(staff_user.first_name, "Ops")

    def test_staff_user_create_rejects_common_password(self):
        self.client.force_login(self.superuser)

        response = self.client.post(
            reverse("dashboard:user-create"),
            {
                "username": "weak-staff",
                "email": "weak-staff@example.com",
                "password": "password123",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="weak-staff").exists())
        self.assertContains(response, "This password is too common.")

    def test_site_access_can_be_updated_and_removed(self):
        client_user = User.objects.create_user(
            username="site-client",
            email="site-client@example.com",
            password="Secret123!",
        )
        access = CustomerSiteAccess.objects.create(
            user=client_user,
            site=self.site,
            role=CustomerSiteAccess.ROLE_OWNER,
            can_control_alarm=True,
        )
        self.client.force_login(self.staff)

        update_response = self.client.post(
            reverse("dashboard:site-access-update", args=[self.site.pk, access.pk]),
            {
                "role": "viewer",
            },
        )
        self.assertEqual(update_response.status_code, 302)
        access.refresh_from_db()
        self.assertEqual(access.role, CustomerSiteAccess.ROLE_VIEWER)
        self.assertFalse(access.can_control_alarm)

        delete_response = self.client.post(
            reverse("dashboard:site-access-delete", args=[self.site.pk, access.pk]),
        )
        self.assertEqual(delete_response.status_code, 302)
        self.assertFalse(CustomerSiteAccess.objects.filter(pk=access.pk).exists())

    def test_subscription_can_be_updated_and_cancelled(self):
        subscription = Subscription.objects.create(
            site=self.site,
            monthly_rate="100.00",
            billing_day=1,
            grace_period_days=7,
            next_due_date=date(2026, 5, 1),
        )
        self.client.force_login(self.billing_staff)

        update_response = self.client.post(
            reverse("dashboard:subscription-update", args=[subscription.pk]),
            {
                "monthly_rate": "149.99",
                "billing_day": "5",
                "grace_period_days": "10",
                "next_due_date": "2026-06-01",
                "notes": "Updated plan",
            },
        )
        self.assertEqual(update_response.status_code, 302)
        subscription.refresh_from_db()
        self.assertEqual(str(subscription.monthly_rate), "149.99")
        self.assertEqual(subscription.billing_day, 5)
        self.assertEqual(subscription.status, Subscription.STATUS_ACTIVE)

        cancel_response = self.client.post(
            reverse("dashboard:subscription-cancel", args=[subscription.pk]),
        )
        self.assertEqual(cancel_response.status_code, 302)
        subscription.refresh_from_db()
        self.assertEqual(subscription.status, Subscription.STATUS_CANCELLED)

    @patch("apps.dashboard.views.send_subscription_lockout_notice.delay")
    def test_cancel_subscription_sends_notice(self, mock_notice):
        subscription = Subscription.objects.create(
            site=self.site,
            monthly_rate="100.00",
            billing_day=1,
            grace_period_days=7,
            next_due_date=date(2026, 5, 1),
        )
        self.client.force_login(self.billing_staff)

        response = self.client.post(
            reverse("dashboard:subscription-cancel", args=[subscription.pk]),
        )

        self.assertEqual(response.status_code, 302)
        mock_notice.assert_called_once_with(str(subscription.id), notice_type="cancelled")

    def test_subscription_update_with_expired_due_date_marks_plan_suspended(self):
        subscription = Subscription.objects.create(
            site=self.site,
            monthly_rate="100.00",
            billing_day=1,
            grace_period_days=7,
            next_due_date=date.today() + timedelta(days=5),
            status=Subscription.STATUS_ACTIVE,
        )
        self.client.force_login(self.billing_staff)

        response = self.client.post(
            reverse("dashboard:subscription-update", args=[subscription.pk]),
            {
                "monthly_rate": "149.99",
                "billing_day": "5",
                "grace_period_days": "7",
                "next_due_date": (date.today() - timedelta(days=10)).isoformat(),
                "notes": "Backdated plan",
            },
        )

        self.assertEqual(response.status_code, 302)
        subscription.refresh_from_db()
        self.assertEqual(subscription.status, Subscription.STATUS_SUSPENDED)
        self.assertIsNotNone(subscription.suspended_at)

    def test_site_can_be_deleted_with_exact_confirmation(self):
        self.client.force_login(self.staff)

        bad_response = self.client.post(
            reverse("dashboard:delete-site", args=[self.site.pk]),
            {"confirm_name": "Wrong Name"},
        )
        self.assertEqual(bad_response.status_code, 302)
        self.assertTrue(Site.objects.filter(pk=self.site.pk).exists())

        good_response = self.client.post(
            reverse("dashboard:delete-site", args=[self.site.pk]),
            {"confirm_name": self.site.name},
        )
        self.assertEqual(good_response.status_code, 302)
        self.assertFalse(Site.objects.filter(pk=self.site.pk).exists())

    def test_broadcast_can_be_deleted_from_console(self):
        self.client.force_login(self.staff)
        message = BroadcastMessage.objects.create(
            title="Maintenance",
            body="Window tonight",
            sent_by=self.staff,
        )

        response = self.client.post(
            reverse("dashboard:broadcast-delete", args=[message.pk]),
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(BroadcastMessage.objects.filter(pk=message.pk).exists())

    def test_staff_user_can_be_deleted_but_not_self(self):
        other_staff = User.objects.create_user(
            username="other-staff",
            email="other-staff@example.com",
            password="Secret123!",
            is_staff=True,
        )
        self.client.force_login(self.superuser)

        self_response = self.client.post(
            reverse("dashboard:user-delete", args=[self.superuser.pk]),
        )
        self.assertEqual(self_response.status_code, 302)
        self.assertTrue(User.objects.filter(pk=self.superuser.pk).exists())

        delete_response = self.client.post(
            reverse("dashboard:user-delete", args=[other_staff.pk]),
        )
        self.assertEqual(delete_response.status_code, 302)
        self.assertFalse(User.objects.filter(pk=other_staff.pk).exists())

    def test_customer_can_be_created_updated_and_deleted_from_console(self):
        self.client.force_login(self.staff)

        create_response = self.client.post(
            reverse("dashboard:customer-create"),
            {
                "username": "cust-1",
                "email": "cust1@example.com",
                "password": "Secret123!",
                "phone": "+1111111",
                "site_id": str(self.site.pk),
                "role": "manager",
                "can_control_alarm": "on",
            },
        )
        self.assertEqual(create_response.status_code, 302)
        customer = User.objects.get(username="cust-1")
        self.assertFalse(customer.is_staff)
        self.assertEqual(customer.customer_profile.phone_number, "+1111111")
        access = CustomerSiteAccess.objects.get(user=customer, site=self.site)
        self.assertEqual(access.role, CustomerSiteAccess.ROLE_MANAGER)

        update_response = self.client.post(
            reverse("dashboard:customer-update", args=[customer.pk]),
            {
                "username": "cust-1",
                "email": "cust1-updated@example.com",
                "first_name": "Client",
                "last_name": "Updated",
                "phone": "+2222222",
                "is_active": "on",
            },
        )
        self.assertEqual(update_response.status_code, 302)
        customer.refresh_from_db()
        self.assertEqual(customer.email, "cust1-updated@example.com")
        self.assertEqual(customer.customer_profile.phone_number, "+2222222")

        delete_response = self.client.post(
            reverse("dashboard:customer-delete", args=[customer.pk]),
        )
        self.assertEqual(delete_response.status_code, 302)
        self.assertFalse(User.objects.filter(pk=customer.pk).exists())

    def test_onboarding_rejects_common_password(self):
        self.client.force_login(self.staff)

        response = self.client.post(
            reverse("dashboard:onboard-client", args=[self.site.pk]),
            {
                "first_name": "Client",
                "last_name": "Owner",
                "email": "weak-owner@example.com",
                "username": "weak-owner",
                "password": "password123",
                "role": "owner",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="weak-owner").exists())
        self.assertContains(response, "This password is too common.")

    def test_payment_can_be_updated_and_deleted(self):
        subscription = Subscription.objects.create(
            site=self.site,
            monthly_rate="100.00",
            billing_day=1,
            grace_period_days=7,
            next_due_date=date(2026, 5, 1),
        )
        payment = SubscriptionPayment.objects.create(
            subscription=subscription,
            amount="100.00",
            period_start=date(2026, 4, 1),
            period_end=date(2026, 4, 30),
            recorded_by=self.staff,
        )
        self.client.force_login(self.billing_staff)

        update_response = self.client.post(
            reverse("dashboard:payment-update", args=[payment.pk]),
            {
                "amount": "110.00",
                "period_start": "2026-04-01",
                "period_end": "2026-05-31",
                "method": SubscriptionPayment.METHOD_MOBILE_MONEY,
                "reference": "MOMO-12345",
                "notes": "Corrected amount",
            },
        )
        self.assertEqual(update_response.status_code, 302)
        payment.refresh_from_db()
        self.assertEqual(str(payment.amount), "110.00")
        self.assertEqual(payment.method, SubscriptionPayment.METHOD_MOBILE_MONEY)
        self.assertEqual(payment.reference, "MOMO-12345")
        self.assertEqual(payment.notes, "Corrected amount")
        subscription.refresh_from_db()
        self.assertEqual(subscription.next_due_date, date(2026, 6, 1))

        delete_response = self.client.post(
            reverse("dashboard:payment-delete", args=[payment.pk]),
        )
        self.assertEqual(delete_response.status_code, 302)
        self.assertFalse(SubscriptionPayment.objects.filter(pk=payment.pk).exists())
        subscription.refresh_from_db()
        self.assertEqual(subscription.next_due_date, date(2026, 4, 1))
        self.assertEqual(subscription.status, Subscription.STATUS_SUSPENDED)

    def test_reactivate_with_past_due_date_is_rejected(self):
        subscription = Subscription.objects.create(
            site=self.site,
            monthly_rate="100.00",
            billing_day=1,
            grace_period_days=7,
            next_due_date=date(2026, 5, 1),
            status=Subscription.STATUS_SUSPENDED,
            suspended_at=timezone.now(),
        )
        self.client.force_login(self.billing_staff)

        response = self.client.post(
            reverse("dashboard:subscription-reactivate", args=[subscription.pk]),
            {
                "next_due_date": (date.today() - timedelta(days=1)).isoformat(),
            },
        )

        self.assertEqual(response.status_code, 302)
        subscription.refresh_from_db()
        self.assertEqual(subscription.status, Subscription.STATUS_SUSPENDED)
        self.assertIsNotNone(subscription.suspended_at)

    @patch("apps.dashboard.views.send_reactivation_notice.delay")
    def test_reactivate_with_future_due_date_restores_cancelled_plan(self, mock_notice):
        subscription = Subscription.objects.create(
            site=self.site,
            monthly_rate="100.00",
            billing_day=1,
            grace_period_days=7,
            next_due_date=date(2026, 5, 1),
            status=Subscription.STATUS_CANCELLED,
            suspended_at=timezone.now(),
        )
        self.client.force_login(self.billing_staff)

        response = self.client.post(
            reverse("dashboard:subscription-reactivate", args=[subscription.pk]),
            {
                "next_due_date": (timezone.localdate() + timedelta(days=15)).isoformat(),
            },
        )

        self.assertEqual(response.status_code, 302)
        subscription.refresh_from_db()
        self.assertEqual(subscription.status, Subscription.STATUS_ACTIVE)
        self.assertIsNone(subscription.suspended_at)
        mock_notice.assert_called_once_with(str(subscription.id))

    @patch("apps.dashboard.views.send_broadcast_push_notifications.delay")
    def test_broadcast_can_be_updated_and_resent(self, mock_delay):
        customer = User.objects.create_user(
            username="broadcast-customer",
            email="broadcast@example.com",
            password="Secret123!",
        )
        self.client.force_login(self.staff)
        message = BroadcastMessage.objects.create(
            title="Maintenance",
            body="Window tonight",
            sent_by=self.staff,
            status=BroadcastMessage.STATUS_FAILED,
        )

        update_response = self.client.post(
            reverse("dashboard:broadcast-update", args=[message.pk]),
            {
                "title": "Updated Maintenance",
                "body": "Updated body",
                "type": "billing",
                "recipient_id": str(customer.pk),
            },
        )
        self.assertEqual(update_response.status_code, 302)
        message.refresh_from_db()
        self.assertEqual(message.title, "Updated Maintenance")
        self.assertEqual(message.message_type, BroadcastMessage.TYPE_BILLING)
        self.assertEqual(message.recipient, customer)

        resend_response = self.client.post(
            reverse("dashboard:broadcast-resend", args=[message.pk]),
        )
        self.assertEqual(resend_response.status_code, 302)
        self.assertEqual(BroadcastMessage.objects.filter(title="Updated Maintenance").count(), 2)
        mock_delay.assert_called_once()


class OperationsZoneTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username="ops-zone-staff",
            email="ops-zone@example.com",
            password="Secret123!",
            is_staff=True,
        )
        StaffOperatorProfile.objects.get_or_create(
            user=self.staff,
            defaults={"role": OperatorRole.OPERATIONS},
        )
        self.auditor = User.objects.create_user(
            username="ops-zone-auditor",
            email="ops-auditor@example.com",
            password="Secret123!",
            is_staff=True,
        )
        StaffOperatorProfile.objects.create(user=self.auditor, role=OperatorRole.AUDITOR)
        self.site = Site.objects.create(
            name="Zone Test Site",
            hik_site_id="hik-zone-1",
            latitude="5.603700",
            longitude="-0.187000",
        )

    def test_site_map_includes_zone_metadata(self):
        zone = OperationsZone.objects.create(name="Accra Central", color="#10b981", sort_order=1)
        self.site.operations_zone = zone
        self.site.save(update_fields=["operations_zone"])

        self.client.force_login(self.staff)
        response = self.client.get(reverse("dashboard:site-map"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Accra Central")
        self.assertContains(response, "zones-data")

    def test_map_zone_create_and_assign_site(self):
        self.client.force_login(self.staff)
        create_response = self.client.post(
            reverse("dashboard:map-zones"),
            {
                "name": "East Legon",
                "color": "#6366f1",
                "description": "East coverage",
                "sort_order": "2",
            },
        )
        self.assertEqual(create_response.status_code, 302)
        zone = OperationsZone.objects.get(name="East Legon")
        self.assertEqual(zone.color, "#6366f1")

        update_response = self.client.post(
            reverse("dashboard:update-site", args=[self.site.pk]),
            {
                "name": self.site.name,
                "hik_site_id": self.site.hik_site_id,
                "operations_zone": str(zone.pk),
                "timezone": "UTC",
                "is_active": "on",
            },
        )
        self.assertEqual(update_response.status_code, 302)
        self.site.refresh_from_db()
        self.assertEqual(self.site.operations_zone_id, zone.pk)

    def test_map_zone_duplicate_name_rejected(self):
        OperationsZone.objects.create(name="Duplicate")
        self.client.force_login(self.staff)
        response = self.client.post(
            reverse("dashboard:map-zones"),
            {"name": "duplicate", "color": "#6366f1", "sort_order": "0"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(OperationsZone.objects.filter(name__iexact="duplicate").count(), 1)

    def test_auditor_cannot_manage_map_zones(self):
        self.client.force_login(self.auditor)
        response = self.client.get(reverse("dashboard:map-zones"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("dashboard:home"))

    def test_inactive_zone_preserved_on_site_update(self):
        hidden = OperationsZone.objects.create(name="Legacy Zone", is_active=False)
        self.site.operations_zone = hidden
        self.site.save(update_fields=["operations_zone"])

        self.client.force_login(self.staff)
        get_response = self.client.get(reverse("dashboard:update-site", args=[self.site.pk]))
        self.assertContains(get_response, "Legacy Zone")
        self.assertContains(get_response, "(hidden)")

        post_response = self.client.post(
            reverse("dashboard:update-site", args=[self.site.pk]),
            {
                "name": "Renamed Site",
                "hik_site_id": self.site.hik_site_id,
                "operations_zone": str(hidden.pk),
                "timezone": "UTC",
                "is_active": "on",
            },
        )
        self.assertEqual(post_response.status_code, 302)
        self.site.refresh_from_db()
        self.assertEqual(self.site.operations_zone_id, hidden.pk)
        self.assertEqual(self.site.name, "Renamed Site")

    def test_site_directory_filters_by_zone(self):
        zone = OperationsZone.objects.create(name="Filter Zone")
        self.site.operations_zone = zone
        self.site.save(update_fields=["operations_zone"])
        Site.objects.create(name="Other", hik_site_id="hik-zone-2", operations_zone=zone)

        self.client.force_login(self.staff)
        response = self.client.get(reverse("dashboard:sites"), {"zone": str(zone.pk)})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Zone Test Site")
        self.assertContains(response, "Other")
        self.assertNotContains(response, "Directory is Empty")

    def test_site_map_accepts_zone_query_param(self):
        zone = OperationsZone.objects.create(name="URL Zone")
        self.site.operations_zone = zone
        self.site.save(update_fields=["operations_zone"])

        self.client.force_login(self.staff)
        response = self.client.get(reverse("dashboard:site-map"), {"zone": str(zone.pk)})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "activeZoneFilter")

    def test_build_guard_map_payload_scopes_site_lookup(self):
        from apps.dashboard.api_views import build_guard_map_payload

        OperationsZone.objects.create(name="Unused")
        with patch("apps.dashboard.api_views.build_command_center_snapshot") as mock_snapshot:
            mock_snapshot.return_value = {
                "guards": [],
                "open_panic_count": 0,
                "active_dispatch_count": 0,
                "generated_at": timezone.now().isoformat(),
            }
            with patch.object(Site.objects, "filter") as mock_filter:
                build_guard_map_payload()
                mock_filter.assert_not_called()
