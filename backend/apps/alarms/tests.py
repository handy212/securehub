import hashlib
import hmac
import json
import time
from datetime import timedelta
from urllib.parse import parse_qs, urlparse
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.core.checks import Tags, run_checks
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.alarms.models import AlarmEvent, ArmDisarmCommand, NotificationDelivery
from apps.alarms.tasks import dispatch_alarm_notifications, poll_mq_events
from apps.hik_adapter.exceptions import HikPartnerError
from apps.sites.models import AlarmPanelDevice, AlarmPeripheral, CustomerSiteAccess, Site, Subsystem, Zone


@override_settings(
    HIK_PARTNER={
        "BASE_URL": "https://example.hik-partner-pro.local",
        "API_KEY": "test-key",
        "API_SECRET": "test-secret",
        "DRY_RUN": True,
    }
)
class BackendApiTests(APITestCase):
    def setUp(self):
        self.password = "StrongPass123!"
        self.owner = User.objects.create_user(
            username="owner",
            password=self.password,
            email="owner@example.com",
        )
        self.viewer = User.objects.create_user(
            username="viewer",
            password=self.password,
            email="viewer@example.com",
        )
        self.stranger = User.objects.create_user(
            username="stranger",
            password=self.password,
            email="stranger@example.com",
        )

        self.site = Site.objects.create(
            name="Warehouse North",
            address="15 Industrial Estate",
            city="Manchester",
            country="UK",
            hik_site_id="hik-site-1",
        )
        self.viewer_site = Site.objects.create(
            name="Retail Showroom",
            address="211 River Street",
            city="Leeds",
            country="UK",
            hik_site_id="hik-site-2",
        )
        CustomerSiteAccess.objects.create(
            user=self.owner,
            site=self.site,
            role=CustomerSiteAccess.ROLE_OWNER,
            can_control_alarm=True,
        )
        CustomerSiteAccess.objects.create(
            user=self.viewer,
            site=self.viewer_site,
            role=CustomerSiteAccess.ROLE_VIEWER,
            can_control_alarm=False,
        )

        self.device = AlarmPanelDevice.objects.create(
            site=self.site,
            name="Main Panel",
            serial_number="SN-0001",
            hik_device_id="hik-device-1",
            is_online=True,
        )
        self.subsystem = Subsystem.objects.create(
            site=self.site,
            device=self.device,
            name="Main Warehouse",
            hik_subsystem_id="subsystem-1",
            subsystem_number=1,
            status=Subsystem.STATUS_DISARMED,
        )
        self.zone = Zone.objects.create(
            subsystem=self.subsystem,
            name="Front Door",
            zone_number=1,
            state=Zone.STATE_NORMAL,
        )
        AlarmEvent.objects.create(
            site=self.site,
            subsystem=self.subsystem,
            zone=self.zone,
            event_type="alarm_triggered",
            source_event_id="evt-1",
            payload={"zone": "Front Door"},
            occurred_at=timezone.now(),
        )

    def authenticate(self, user):
        self.client.force_authenticate(user=user)

    def test_login_returns_jwt_tokens(self):
        response = self.client.post(
            reverse("token-obtain-pair"),
            {"username": self.owner.username, "password": self.password},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_root_path_returns_api_landing_payload(self):
        response = self.client.get(reverse("service-root"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["service"], "Alarm Hub Backend")
        self.assertEqual(response.data["status"], "ok")
        self.assertIn("sites", response.data["endpoints"])

    def test_health_check_returns_ok_without_authentication(self):
        response = self.client.get(reverse("health-check"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "ok")

    def test_console_redirect_preserves_full_query_string(self):
        response = self.client.get("/console/?tab=alerts&site=123")

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        parsed = urlparse(response["Location"])
        self.assertEqual(parsed.path, "/console/login/")
        self.assertEqual(parse_qs(parsed.query)["next"], ["/console/?tab=alerts&site=123"])

    def test_hik_health_requires_admin_user(self):
        self.authenticate(self.owner)
        customer_response = self.client.get(reverse("hik-health"))
        self.assertEqual(customer_response.status_code, status.HTTP_403_FORBIDDEN)

        admin = User.objects.create_user(
            username="admin-operator",
            password=self.password,
            email="admin@example.com",
            is_staff=True,
            is_superuser=True,
        )
        self.authenticate(admin)
        admin_response = self.client.get(reverse("hik-health"))

        self.assertEqual(admin_response.status_code, status.HTTP_200_OK)
        self.assertEqual(admin_response.data["data"]["configured"], True)
        self.assertEqual(admin_response.data["data"]["dry_run"], True)

    def test_site_list_returns_only_assigned_sites_and_permission_flag(self):
        self.authenticate(self.owner)
        response = self.client.get(reverse("site-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]["name"], self.site.name)
        self.assertTrue(response.data['results'][0]["can_control_alarm"])

        self.authenticate(self.viewer)
        viewer_response = self.client.get(reverse("site-list"))
        self.assertEqual(viewer_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(viewer_response.data['results']), 1)
        self.assertEqual(viewer_response.data['results'][0]["name"], self.viewer_site.name)
        self.assertFalse(viewer_response.data['results'][0]["can_control_alarm"])

    # ------------------------------------------------------------------ #
    #  Notification dispatch                                               #
    # ------------------------------------------------------------------ #

    @patch("apps.alarms.views.dispatch_alarm_notifications.delay")
    def test_command_triggers_notification_dispatch(self, mock_delay):
        """A successful arm/disarm command must dispatch a notification task."""
        self.authenticate(self.owner)
        self.client.post(
            reverse(
                "subsystem-command",
                kwargs={
                    "site_id": self.site.id,
                    "subsystem_id": self.subsystem.id,
                    "action": "arm",
                },
            ),
            {"idempotency_key": "notify-test"},
            format="json",
        )
        mock_delay.assert_called_once()

    # ------------------------------------------------------------------ #
    #  Multi-site isolation                                               #
    # ------------------------------------------------------------------ #

    def test_stranger_cannot_read_another_sites_events(self):
        """A user with no site access must receive 404, not a data leak."""
        other_site = Site.objects.create(
            name="Other Company HQ",
            hik_site_id="hik-site-other",
        )
        AlarmEvent.objects.create(
            site=other_site,
            event_type="alarm_triggered",
            source_event_id="evt-other",
            payload={},
            occurred_at=timezone.now(),
        )
        self.authenticate(self.stranger)
        response = self.client.get(
            reverse("site-events", kwargs={"site_id": other_site.id})
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    from unittest.mock import patch
    @patch("apps.sites.views.HikPartnerService.sync_alarm_status")
    def test_site_status_returns_aggregated_counts(self, mock_sync):
        self.authenticate(self.owner)
        response = self.client.get(
            reverse("site-status", kwargs={"site_id": self.site.id})
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["armed_subsystems"], 0)
        self.assertEqual(response.data["disarmed_subsystems"], 1)
        self.assertEqual(response.data["active_alarm_count"], 0)
        self.assertEqual(response.data["offline_device_count"], 0)
        self.assertEqual(len(response.data["subsystems"]), 1)
        self.assertTrue(response.data["subsystems"][0]["panelIsOnline"])

    def test_subsystem_command_updates_status_and_creates_event(self):
        self.authenticate(self.owner)
        response = self.client.post(
            reverse(
                "subsystem-command",
                kwargs={
                    "site_id": self.site.id,
                    "subsystem_id": self.subsystem.id,
                    "action": "arm",
                },
            ),
            {
                "idempotency_key": "arm-1",
                "reason": "Closing for the evening",
                "metadata": {"source": "test"},
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.subsystem.refresh_from_db()
        self.assertEqual(self.subsystem.status, Subsystem.STATUS_ARMED)

        command = ArmDisarmCommand.objects.get(id=response.data["id"])
        self.assertEqual(command.status, ArmDisarmCommand.STATUS_SUCCESS)
        self.assertEqual(command.idempotency_key, "arm-1")
        self.assertEqual(command.request_payload["reason"], "Closing for the evening")
        self.assertEqual(
            command.response_payload["isapi_uri"],
            "/ISAPI/SecurityCP/control/arm/1?ways=away&format=json",
        )
        self.assertEqual(
            command.response_payload["transparent_request"]["headers"]["X-Devserial"],
            self.device.serial_number,
        )
        self.assertTrue(
            AlarmEvent.objects.filter(
                site=self.site,
                subsystem=self.subsystem,
                event_type="arm_success",
            ).exists()
        )

    def test_subsystem_command_rejects_known_offline_panel(self):
        self.device.is_online = False
        self.device.save(update_fields=["is_online"])
        self.authenticate(self.owner)

        response = self.client.post(
            reverse(
                "subsystem-command",
                kwargs={
                    "site_id": self.site.id,
                    "subsystem_id": self.subsystem.id,
                    "action": "arm",
                },
            ),
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data["code"], "panel_offline")
        self.assertEqual(ArmDisarmCommand.objects.count(), 0)

    @patch("apps.alarms.views.HikPartnerService.execute_subsystem_command")
    def test_subsystem_command_returns_conflict_when_hik_reports_unreachable(self, mock_execute):
        mock_execute.side_effect = HikPartnerError(
            "Panel is offline or unreachable.",
            error_code="LAP020011",
        )
        self.authenticate(self.owner)

        response = self.client.post(
            reverse(
                "subsystem-command",
                kwargs={
                    "site_id": self.site.id,
                    "subsystem_id": self.subsystem.id,
                    "action": "arm",
                },
            ),
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data["code"], "panel_offline")
        command = ArmDisarmCommand.objects.get()
        self.assertEqual(command.status, ArmDisarmCommand.STATUS_FAILED)

    def test_subsystem_command_is_idempotent(self):
        self.authenticate(self.owner)
        url = reverse(
            "subsystem-command",
            kwargs={
                "site_id": self.site.id,
                "subsystem_id": self.subsystem.id,
                "action": "disarm",
            },
        )

        first = self.client.post(
            url,
            {"idempotency_key": "same-key", "metadata": {"source": "first"}},
            format="json",
        )
        second = self.client.post(
            url,
            {"idempotency_key": "same-key", "metadata": {"source": "second"}},
            format="json",
        )

        self.assertEqual(first.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(first.data["id"], second.data["id"])
        self.assertEqual(
            ArmDisarmCommand.objects.filter(idempotency_key="same-key").count(),
            1,
        )

    def test_subsystem_command_denies_read_only_user(self):
        read_only_site = Site.objects.create(
            name="Read Only Site",
            hik_site_id="hik-site-3",
        )
        read_only_device = AlarmPanelDevice.objects.create(
            site=read_only_site,
            name="Read Only Panel",
            serial_number="SN-0003",
            hik_device_id="hik-device-3",
        )
        read_only_subsystem = Subsystem.objects.create(
            site=read_only_site,
            device=read_only_device,
            name="Read Only Subsystem",
            hik_subsystem_id="subsystem-3",
            subsystem_number=1,
        )
        CustomerSiteAccess.objects.create(
            user=self.viewer,
            site=read_only_site,
            role=CustomerSiteAccess.ROLE_VIEWER,
            can_control_alarm=False,
        )

        self.authenticate(self.viewer)
        response = self.client.post(
            reverse(
                "subsystem-command",
                kwargs={
                    "site_id": read_only_site.id,
                    "subsystem_id": read_only_subsystem.id,
                    "action": "arm",
                },
            ),
            {"idempotency_key": "viewer-arm"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_site_events_are_scoped_to_authorized_user(self):
        self.authenticate(self.owner)
        response = self.client.get(
            reverse("site-events", kwargs={"site_id": self.site.id})
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]["event_type"], "alarm_triggered")

        self.authenticate(self.stranger)
        forbidden = self.client.get(
            reverse("site-events", kwargs={"site_id": self.site.id})
        )
        self.assertEqual(forbidden.status_code, status.HTTP_404_NOT_FOUND)

    def test_site_commands_list_returns_command_history(self):
        self.authenticate(self.owner)
        self.client.post(
            reverse(
                "subsystem-command",
                kwargs={
                    "site_id": self.site.id,
                    "subsystem_id": self.subsystem.id,
                    "action": "arm",
                },
            ),
            {"idempotency_key": "history-1"},
            format="json",
        )

        response = self.client.get(
            reverse("site-commands", kwargs={"site_id": self.site.id})
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]["action"], "arm")

    @patch("apps.alarms.views.HikPartnerService.execute_subsystem_command")
    def test_failed_subsystem_command_is_audited_and_keeps_local_state(self, mock_execute):
        mock_execute.side_effect = Exception("Panel rejected command")
        self.authenticate(self.owner)

        response = self.client.post(
            reverse(
                "subsystem-command",
                kwargs={
                    "site_id": self.site.id,
                    "subsystem_id": self.subsystem.id,
                    "action": "arm",
                },
            ),
            {"idempotency_key": "failed-arm"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.subsystem.refresh_from_db()
        self.assertEqual(self.subsystem.status, Subsystem.STATUS_DISARMED)

        command = ArmDisarmCommand.objects.get(idempotency_key="failed-arm")
        self.assertEqual(command.status, ArmDisarmCommand.STATUS_FAILED)
        self.assertIn("Panel rejected command", command.failure_reason)


class NotificationDispatchRetryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="notify-user",
            email="notify@example.com",
            password="Secret123!",
        )
        self.site = Site.objects.create(name="Retry Site", hik_site_id="retry-site-1")
        CustomerSiteAccess.objects.create(
            user=self.user,
            site=self.site,
            role=CustomerSiteAccess.ROLE_OWNER,
            can_control_alarm=True,
        )
        self.event = AlarmEvent.objects.create(
            site=self.site,
            event_type="alarm_triggered",
            event_category=AlarmEvent.CATEGORY_ALARM,
            severity=AlarmEvent.SEVERITY_HIGH,
            payload={"event_name": "Alarm Triggered"},
            occurred_at=timezone.now(),
        )

    @patch("apps.alarms.tasks._send_fcm_notification")
    @patch("apps.alarms.tasks._send_email")
    def test_retry_does_not_duplicate_push_after_email_failure(self, mock_send_email, mock_send_fcm):
        mock_send_email.side_effect = RuntimeError("smtp down")
        mock_send_fcm.return_value = 1

        first_result = dispatch_alarm_notifications.apply(args=[str(self.event.id)], throw=False)
        self.assertIn(first_result.state, {"RETRY", "FAILURE"})
        self.assertEqual(mock_send_fcm.call_count, 1)

        second_result = dispatch_alarm_notifications.apply(args=[str(self.event.id)], throw=False)
        self.assertIn(second_result.state, {"RETRY", "FAILURE"})
        self.assertGreaterEqual(mock_send_email.call_count, 2)
        self.assertEqual(mock_send_fcm.call_count, 1)

        push_deliveries = NotificationDelivery.objects.filter(
            event=self.event,
            channel="push",
            provider="firebase",
            recipient=self.user.email,
        )
        self.assertEqual(push_deliveries.count(), 1)
        self.assertEqual(push_deliveries.first().status, NotificationDelivery.STATUS_SENT)


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,
    HIK_PARTNER={
        "BASE_URL": "https://example.hik-partner-pro.local",
        "API_KEY": "test-key",
        "API_SECRET": "test-secret",
        "DRY_RUN": False,
    },
)
class AlarmTaskTests(TestCase):
    @staticmethod
    def test_poll_mq_events_skips_in_celery_eager_mode():
        result = poll_mq_events.apply().get()

        assert result["skipped"] is True
        assert result["reason"] == "celery eager mode"


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=False,
    HIK_PARTNER={
        "BASE_URL": "https://example.hik-partner-pro.local",
        "API_KEY": "test-key",
        "API_SECRET": "test-secret",
        "WEBHOOK_SIGN_SECRET": "Webhook123",
        "DELIVERY_MODE": "webhook",
        "DRY_RUN": False,
    },
)
class AlarmTaskDeliveryModeTests(TestCase):
    @staticmethod
    def test_poll_mq_events_skips_when_delivery_mode_is_webhook():
        result = poll_mq_events.apply().get()

        assert result["skipped"] is True
        assert result["reason"] == "delivery mode disabled polling"


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=False,
    HIK_PARTNER={
        "BASE_URL": "https://example.hik-partner-pro.local",
        "API_KEY": "test-key",
        "API_SECRET": "test-secret",
        "DELIVERY_MODE": "mq",
        "DRY_RUN": False,
    },
)
class PollMqAckBehaviourTests(TestCase):
    @patch("apps.hik_adapter.client.HikPartnerClient.confirm_messages")
    @patch("apps.hik_adapter.services.HikPartnerService.process_mq_message")
    @patch("apps.hik_adapter.client.HikPartnerClient.poll_messages")
    def test_poll_mq_events_confirms_batch_after_successful_processing(
        self,
        mock_poll_messages,
        mock_process,
        mock_confirm,
    ):
        mock_poll_messages.return_value = {
            "data": {
                "batchId": "batch-1",
                "list": [{"deviceSerial": "SN-1"}],
            }
        }
        mock_process.return_value = MagicMock()

        result = poll_mq_events.apply(throw=True).get()

        self.assertEqual(result["processed"], 1)
        mock_confirm.assert_called_once_with("batch-1")

    @patch("apps.hik_adapter.client.HikPartnerClient.confirm_messages")
    @patch("apps.hik_adapter.services.HikPartnerService.process_mq_message")
    @patch("apps.hik_adapter.client.HikPartnerClient.poll_messages")
    def test_poll_mq_events_does_not_confirm_batch_when_processing_fails(
        self,
        mock_poll_messages,
        mock_process,
        mock_confirm,
    ):
        mock_poll_messages.return_value = {
            "data": {
                "batchId": "batch-2",
                "list": [{"deviceSerial": "SN-1"}],
            }
        }
        mock_process.side_effect = RuntimeError("broken message")

        result = poll_mq_events.apply(throw=False)

        self.assertIn(result.state, {"RETRY", "FAILURE"})
        mock_confirm.assert_not_called()


class FirebaseCredentialChecksTests(TestCase):
    @override_settings(FIREBASE_CREDENTIALS_PATH="/home/dev/SecureHub/backend/firebase/example.json")
    def test_check_rejects_credentials_path_inside_repo(self):
        errors = run_checks(tags=[Tags.security])
        error_ids = {error.id for error in errors}

        self.assertIn("securehub.E001", error_ids)
        self.assertIn("securehub.E002", error_ids)

    @override_settings(FIREBASE_CREDENTIALS_PATH="relative/firebase.json")
    def test_check_warns_for_relative_credentials_path(self):
        errors = run_checks(tags=[Tags.security])
        error_ids = {error.id for error in errors}

        self.assertIn("securehub.W001", error_ids)

    @override_settings(FIREBASE_CREDENTIALS_PATH="")
    def test_check_rejects_google_application_credentials_inside_repo(self):
        with patch.dict(
            "os.environ",
            {"GOOGLE_APPLICATION_CREDENTIALS": "/home/dev/SecureHub/backend/firebase/example.json"},
        ):
            errors = run_checks(tags=[Tags.security])

        error_ids = {error.id for error in errors}
        self.assertIn("securehub.E001", error_ids)
        self.assertIn("securehub.E002", error_ids)

    @override_settings(
        DEBUG=False,
        TESTING=False,
        SECRET_KEY="alarmhub-dev-secret-key-change-me-before-production-2026",
    )
    def test_check_rejects_default_secret_key_when_debug_disabled(self):
        errors = run_checks(tags=[Tags.security])
        error_ids = {error.id for error in errors}

        self.assertIn("securehub.E003", error_ids)


class FirebaseMessagingInitTests(TestCase):
    @override_settings(FIREBASE_CREDENTIALS_PATH="/tmp/firebase-admin.json")
    @patch("firebase_admin.initialize_app")
    @patch("firebase_admin.get_app")
    @patch("firebase_admin.credentials.Certificate")
    def test_helper_uses_service_account_path_when_present(
        self,
        mock_certificate,
        mock_get_app,
        mock_initialize_app,
    ):
        from apps.alarms.firebase import get_firebase_messaging

        mock_get_app.side_effect = ValueError("no app")

        messaging = get_firebase_messaging()

        self.assertIsNotNone(messaging)
        mock_certificate.assert_called_once_with("/tmp/firebase-admin.json")
        mock_initialize_app.assert_called_once()

    @override_settings(FIREBASE_CREDENTIALS_PATH="")
    @patch("firebase_admin.initialize_app")
    @patch("firebase_admin.get_app")
    def test_helper_falls_back_to_adc_when_path_not_set(
        self,
        mock_get_app,
        mock_initialize_app,
    ):
        from apps.alarms.firebase import get_firebase_messaging

        mock_get_app.side_effect = ValueError("no app")

        messaging = get_firebase_messaging()

        self.assertIsNotNone(messaging)
        mock_initialize_app.assert_called_once_with()


# --------------------------------------------------------------------------- #
#  MQ ingestion + state sync tests                                            #
# --------------------------------------------------------------------------- #

_HIK_SETTINGS = {
    "BASE_URL": "https://example.hik-partner-pro.local",
    "API_KEY": "test-key",
    "API_SECRET": "test-secret",
    "WEBHOOK_SIGN_SECRET": "Webhook123",
    "DELIVERY_MODE": "mq",
    "DRY_RUN": True,
}


@override_settings(HIK_PARTNER=_HIK_SETTINGS)
class MqIngestionTests(TestCase):
    """Unit-level tests for HikPartnerService.process_mq_message()."""

    def setUp(self):
        self.site = Site.objects.create(
            name="MQ Test Site",
            hik_site_id="mq-site-1",
        )
        self.device = AlarmPanelDevice.objects.create(
            site=self.site,
            name="Panel",
            serial_number="SN-MQ-001",
            hik_device_id="hik-mq-1",
            is_online=True,
        )
        self.subsystem = Subsystem.objects.create(
            site=self.site,
            device=self.device,
            name="Area 1",
            hik_subsystem_id="mq-sub-1",
            subsystem_number=1,
            status=Subsystem.STATUS_DISARMED,
        )
        self.zone = Zone.objects.create(
            subsystem=self.subsystem,
            name="Front Door",
            zone_number=1,
            state=Zone.STATE_NORMAL,
        )

    def _make_msg(self, event_desc, extra_cid=None, trigger_time="12345"):
        """Build a minimal CID MQ message dict."""
        cid = {"system": 1, "zone": 1}
        if extra_cid:
            cid.update(extra_cid)
        return {
            "deviceSerial": self.device.serial_number,
            "alarmData": json.dumps({
                "eventType": "cidEvent",
                "eventDescription": event_desc,
                "triggerTime": trigger_time,
                "CIDEvent": cid,
            }),
        }

    def test_process_mq_message_creates_alarm_event(self):
        """A well-formed MQ message must produce an AlarmEvent linked to the site."""
        from apps.hik_adapter.services import HikPartnerService
        msg = self._make_msg("AwayArm")
        event = HikPartnerService().process_mq_message(msg)

        self.assertIsNotNone(event)
        self.assertEqual(event.event_type, "AwayArm")
        self.assertEqual(event.site, self.site)

    def test_process_mq_message_uses_hik_trigger_time_when_parseable(self):
        """A parseable Hik triggerTime should become the persisted occurred_at."""
        from apps.hik_adapter.services import HikPartnerService
        msg = {
            "deviceSerial": self.device.serial_number,
            "alarmData": json.dumps({
                "eventType": "cidEvent",
                "eventDescription": "AwayArm",
                "triggerTime": "2025-10-01T12:34:56+00:00",
                "CIDEvent": {"system": 1, "zone": 1},
            }),
        }

        event = HikPartnerService().process_mq_message(msg)
        self.assertEqual(event.occurred_at.isoformat(), "2025-10-01T12:34:56+00:00")

    def test_process_mq_message_arms_subsystem(self):
        """An AwayArm event must update the subsystem status to ARMED."""
        from apps.hik_adapter.services import HikPartnerService
        HikPartnerService().process_mq_message(self._make_msg("AwayArm"))

        self.subsystem.refresh_from_db()
        self.assertEqual(self.subsystem.status, Subsystem.STATUS_ARMED)

    def test_duplicate_mq_event_is_not_created(self):
        """Sending the same message twice must produce exactly one AlarmEvent."""
        from apps.hik_adapter.services import HikPartnerService
        msg = self._make_msg("AwayArm", trigger_time="99999")
        service = HikPartnerService()

        service.process_mq_message(msg)
        service.process_mq_message(msg)  # duplicate

        self.assertEqual(
            AlarmEvent.objects.filter(site=self.site, event_type="AwayArm").count(),
            1,
            "Duplicate MQ message must not create a second AlarmEvent.",
        )

    def test_bypass_zone_event_updates_zone_state(self):
        """A BypassZone event must set the target zone to STATE_BYPASSED."""
        from apps.hik_adapter.services import HikPartnerService
        HikPartnerService().process_mq_message(self._make_msg("BypassZone"))

        self.zone.refresh_from_db()
        self.assertEqual(
            self.zone.state, Zone.STATE_BYPASSED,
            "Zone state must be BYPASSED after a BypassZone MQ event.",
        )

    def test_restore_event_returns_zone_to_normal(self):
        """A ZoneRestore event must set the zone back to STATE_NORMAL."""
        from apps.hik_adapter.services import HikPartnerService
        self.zone.state = Zone.STATE_ALARM
        self.zone.save()

        HikPartnerService().process_mq_message(self._make_msg("ZoneRestore"))

        self.zone.refresh_from_db()
        self.assertEqual(self.zone.state, Zone.STATE_NORMAL)

    def test_disarm_clears_zone_alarms(self):
        """A Disarm event must bulk-reset any zones currently in ALARM state."""
        from apps.hik_adapter.services import HikPartnerService
        self.zone.state = Zone.STATE_ALARM
        self.zone.save()
        self.subsystem.status = Subsystem.STATUS_ARMED
        self.subsystem.save()

        HikPartnerService().process_mq_message(self._make_msg("Disarm", extra_cid={}))

        self.zone.refresh_from_db()
        self.assertEqual(self.zone.state, Zone.STATE_NORMAL)

    def test_invalid_mq_payload_does_not_crash(self):
        """A message with no recognisable deviceSerial must return None gracefully."""
        from apps.hik_adapter.services import HikPartnerService
        event = HikPartnerService().process_mq_message({"invalid": "data"})
        self.assertIsNone(event)

    def test_mq_message_with_unknown_serial_is_skipped(self):
        """A message from an unregistered device serial must return None."""
        from apps.hik_adapter.services import HikPartnerService
        msg = self._make_msg("AwayArm")
        msg["deviceSerial"] = "UNKNOWN-SN-9999"
        event = HikPartnerService().process_mq_message(msg)
        self.assertIsNone(event)

    def test_events_are_ordered_by_latest_first(self):
        """AlarmEvent default ordering must put the most recent event first."""
        older = AlarmEvent.objects.create(
            site=self.site,
            event_type="first_event",
            payload={},
            occurred_at=timezone.now() - timedelta(minutes=5),
        )
        newer = AlarmEvent.objects.create(
            site=self.site,
            event_type="second_event",
            payload={},
            occurred_at=timezone.now(),
        )
        events = list(AlarmEvent.objects.filter(site=self.site))
        self.assertEqual(events[0].id, newer.id)
        self.assertEqual(events[1].id, older.id)

    def test_disarm_event_from_keyfob_user_creates_keyfob_records(self):
        """A CID disarm attributed to a key fob should create local keyfob inventory."""
        from apps.hik_adapter.services import HikPartnerService

        subsystem_two = Subsystem.objects.create(
            site=self.site,
            device=self.device,
            name="Partition 2",
            hik_subsystem_id="mq-sub-2",
            subsystem_number=2,
            status=Subsystem.STATUS_ARMED,
        )
        msg = {
            "deviceSerial": self.device.serial_number,
            "alarmData": json.dumps({
                "eventType": "cidEvent",
                "eventDescription": "CID event",
                "triggerTime": "2026-04-11T19:51:30",
                "CIDEvent": {
                    "code": 1401,
                    "system": 2,
                    "systemName": "Partition 2",
                    "userNo": 323,
                    "evttype": "13",
                    "description": "disarm",
                    "userName": "handy key fob 2",
                },
            }),
        }

        HikPartnerService().process_mq_message(msg)

        keyfob_zone = Zone.objects.get(
            subsystem=subsystem_two,
            device_type=Zone.DEVICE_TYPE_KEYFOB,
            zone_number=323,
        )
        self.assertEqual(keyfob_zone.name, "handy key fob 2")
        self.assertTrue(
            AlarmPeripheral.objects.filter(
                device=self.device,
                peripheral_type=AlarmPeripheral.TYPE_KEYFOB,
                peripheral_number=323,
                name="handy key fob 2",
            ).exists()
        )

    def test_add_ex_module_event_creates_output_module_with_device_name(self):
        """A relay-module enrollment event should create an output module, not a keyfob."""
        from apps.hik_adapter.services import HikPartnerService

        msg = {
            "deviceSerial": self.device.serial_number,
            "alarmData": json.dumps({
                "eventType": "cidEvent",
                "eventDescription": "CID event",
                "triggerTime": "2026-04-11T20:22:33",
                "CIDEvent": {
                    "ModNo": 1,
                    "code": 3977,
                    "userNo": 502,
                    "evttype": "13",
                    "description": "addExModule",
                    "deviceNo": 7,
                    "userName": "sackey@responseoneghana.com",
                    "deviceName": "Relay Module 1",
                    "isTalk": "0",
                },
            }),
        }

        HikPartnerService().process_mq_message(msg)

        self.assertTrue(
            AlarmPeripheral.objects.filter(
                device=self.device,
                peripheral_type=AlarmPeripheral.TYPE_OUTPUT_MODULE,
                peripheral_number=1,
                name="Relay Module 1",
            ).exists()
        )
        self.assertFalse(
            AlarmPeripheral.objects.filter(
                device=self.device,
                peripheral_type=AlarmPeripheral.TYPE_KEYFOB,
                peripheral_number=1,
            ).exists()
        )

    def test_alarm_event_with_device_number_is_not_misclassified_as_keyfob(self):
        """Descriptions like 'alarm' must not trip the control-device arm heuristic."""
        from apps.hik_adapter.services import HikPartnerService

        msg = {
            "deviceSerial": self.device.serial_number,
            "alarmData": json.dumps({
                "eventType": "cidEvent",
                "eventDescription": "CID event",
                "triggerTime": "2026-04-11T20:30:00",
                "CIDEvent": {
                    "code": 1103,
                    "system": 1,
                    "zone": 3,
                    "evttype": "11",
                    "description": "alarm",
                    "zoneName": "Wireless Cam Sensor",
                    "deviceNo": 5,
                },
            }),
        }

        HikPartnerService().process_mq_message(msg)

        self.assertFalse(
            AlarmPeripheral.objects.filter(
                device=self.device,
                peripheral_type=AlarmPeripheral.TYPE_KEYFOB,
                peripheral_number=5,
            ).exists()
        )


# --------------------------------------------------------------------------- #
#  Webhook ingestion tests                                                    #
# --------------------------------------------------------------------------- #

@override_settings(HIK_PARTNER=_HIK_SETTINGS)
class WebhookTests(APITestCase):
    """Tests for the HikWebhookView signature verification and async dispatch."""

    def setUp(self):
        self.site = Site.objects.create(
            name="Webhook Test Site",
            hik_site_id="webhook-site-1",
        )
        self.device = AlarmPanelDevice.objects.create(
            site=self.site,
            name="Webhook Panel",
            serial_number="SN-WH-001",
            hik_device_id="hik-wh-1",
            is_online=True,
        )
        self.url = reverse("hik-webhook")

    def _make_signature(self, timestamp, batch_id, secret="Webhook123"):
        message = f"{timestamp}.{batch_id}".encode()
        return "sha256=" + hmac.new(
            secret.encode(), message, hashlib.sha256
        ).hexdigest()

    def _post_webhook(self, payload, timestamp=None, batch_id="batch-1", secret="Webhook123"):
        timestamp = timestamp or str(int(time.time() * 1000))
        signature = self._make_signature(timestamp, batch_id, secret)
        return self.client.post(
            self.url,
            payload,
            format="json",
            HTTP_X_HOOK_SIGNATURE=signature,
            HTTP_X_HOOK_TIMESTAMP=timestamp,
            HTTP_X_HOOK_BATCH_ID=batch_id,
        )

    @patch("apps.alarms.views.process_webhook_messages.delay")
    def test_webhook_accepts_valid_signature(self, mock_delay):
        """A POST with a valid HMAC signature must return 200 and queue the task."""
        response = self._post_webhook(
            {"deviceSerial": self.device.serial_number,
             "alarmData": {"eventDescription": "AwayArm"}}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["code"], "0")
        mock_delay.assert_called_once()

    def test_webhook_rejects_invalid_signature(self):
        """A POST signed with the wrong secret must be rejected with 401."""
        response = self._post_webhook(
            {"deviceSerial": self.device.serial_number,
             "alarmData": {"eventDescription": "AwayArm"}},
            secret="wrong-secret",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_webhook_rejects_stale_timestamp(self):
        """A POST with a timestamp older than 1 minute must be rejected."""
        old_timestamp = str(int((time.time() - 70) * 1000))
        response = self._post_webhook(
            {"deviceSerial": self.device.serial_number,
             "alarmData": {"eventDescription": "AwayArm"}},
            timestamp=old_timestamp,
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_webhook_get_handshake_returns_200_with_signature(self):
        """GET on the webhook endpoint must return 200 and a valid X-Hook-Signature."""
        timestamp = str(int(time.time() * 1000))
        batch_id = "test-verification-batch"
        
        response = self.client.get(
            self.url,
            HTTP_X_HOOK_TIMESTAMP=timestamp,
            HTTP_X_HOOK_BATCH_ID=batch_id,
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["code"], "0")
        
        # Verify the signature header exists and is valid
        expected_sig = self._make_signature(timestamp, batch_id)
        self.assertEqual(response.headers.get("X-Hook-Signature"), expected_sig)

    @patch("apps.alarms.views.process_webhook_messages.delay")
    def test_webhook_empty_body_returns_accepted(self, mock_delay):
        """An empty (or non-dict) body after signature check must return 200, not crash."""
        response = self._post_webhook({})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Empty message list — task should NOT be dispatched
        mock_delay.assert_not_called()
