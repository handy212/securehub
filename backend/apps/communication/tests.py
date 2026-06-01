from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import CustomerGroup, FCMDevice
from apps.alarms.tasks import _send_generic_fcm_notification
from apps.communication.push import send_push_to_devices

from .models import BroadcastMessage, BroadcastMessageView
from .tasks import _dispatch_push


class FakeFCMException(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


class FakeFCMResponse:
    def __init__(self, success=True, exception=None):
        self.success = success
        self.exception = exception


class FakeFCMBatchResponse:
    def __init__(self, responses):
        self.responses = responses
        self.success_count = sum(1 for response in responses if response.success)
        self.failure_count = len(responses) - self.success_count


class FakeMessaging:
    class Notification:
        def __init__(self, title, body):
            self.title = title
            self.body = body

    class MulticastMessage:
        def __init__(self, notification, data, tokens):
            self.notification = notification
            self.data = data
            self.tokens = tokens

    def __init__(self, responses):
        self.responses = responses
        self.messages = []

    def send_each_for_multicast(self, message):
        self.messages.append(message)
        return FakeFCMBatchResponse(self.responses)


class BroadcastMessageAuthTests(APITestCase):
    def setUp(self):
        self.group = CustomerGroup.objects.create(name="Priority")
        self.user = User.objects.create_user(
            username="message-user",
            email="message-user@example.com",
            password="Secret123!",
        )
        self.other = User.objects.create_user(
            username="other-user",
            email="other-user@example.com",
            password="Secret123!",
        )
        self.user.customer_profile.group = self.group
        self.user.customer_profile.save(update_fields=["group", "updated_at"])

    def authenticate(self, user):
        self.client.force_authenticate(user=user)

    def test_user_cannot_mark_unaddressed_direct_message_viewed(self):
        message = BroadcastMessage.objects.create(
            title="Private",
            body="For someone else",
            recipient=self.other,
            status=BroadcastMessage.STATUS_SENT,
        )
        self.authenticate(self.user)

        response = self.client.post(reverse("message-viewed", args=[message.pk]))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(
            BroadcastMessageView.objects.filter(message=message, user=self.user).exists()
        )

    def test_user_can_mark_group_message_viewed(self):
        message = BroadcastMessage.objects.create(
            title="Group",
            body="For the group",
            recipient_group=self.group,
            status=BroadcastMessage.STATUS_SENT,
        )
        self.authenticate(self.user)

        response = self.client.post(reverse("message-viewed", args=[message.pk]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            BroadcastMessageView.objects.filter(message=message, user=self.user).exists()
        )

    def test_user_inbox_includes_in_app_message_when_external_push_failed(self):
        message = BroadcastMessage.objects.create(
            title="Local visible",
            body="Still appears in the web/mobile inbox.",
            status=BroadcastMessage.STATUS_FAILED,
        )
        self.authenticate(self.user)

        response = self.client.get(reverse("user-messages"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        rows = response.data.get("results", response.data)
        self.assertEqual(rows[0]["id"], str(message.id))

    def test_user_can_mark_failed_in_app_message_viewed(self):
        message = BroadcastMessage.objects.create(
            title="Local visible",
            body="No FCM required for in-app visibility.",
            status=BroadcastMessage.STATUS_FAILED,
        )
        self.authenticate(self.user)

        response = self.client.post(reverse("message-viewed", args=[message.pk]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            BroadcastMessageView.objects.filter(message=message, user=self.user).exists()
        )

    def test_web_notification_summary_returns_unread_count_and_recent_items(self):
        BroadcastMessage.objects.create(
            title="Visible one",
            body="First inbox item.",
            status=BroadcastMessage.STATUS_SENT,
        )
        viewed = BroadcastMessage.objects.create(
            title="Visible two",
            body="Already viewed.",
            status=BroadcastMessage.STATUS_SENT,
        )
        BroadcastMessageView.objects.create(message=viewed, user=self.user)
        self.authenticate(self.user)

        response = self.client.get(reverse("message-summary"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["unread_count"], 1)
        self.assertEqual(len(response.data["notifications"]), 2)
        self.assertIn("created_at_display", response.data["notifications"][0])


class PushDeliveryTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="push-user",
            email="push-user@example.com",
            password="Secret123!",
        )
        self.other = User.objects.create_user(
            username="push-other",
            email="push-other@example.com",
            password="Secret123!",
        )

    def _device(self, user, token):
        return FCMDevice.objects.create(user=user, token=token, platform=FCMDevice.PLATFORM_ANDROID)

    def test_send_push_to_devices_normalizes_payload_and_deactivates_invalid_tokens(self):
        active = self._device(self.user, "token-active")
        stale = self._device(self.user, "token-stale")
        messaging = FakeMessaging(
            [
                FakeFCMResponse(success=True),
                FakeFCMResponse(success=False, exception=FakeFCMException("unregistered")),
            ]
        )

        from unittest.mock import patch

        with patch("apps.communication.push.get_firebase_messaging", return_value=messaging):
            result = send_push_to_devices(
                FCMDevice.objects.filter(pk__in=[active.pk, stale.pk]),
                title="System alert",
                body="Review your dashboard",
                data={"type": "system", "site_id": 42, "skip": None},
            )

        self.assertEqual(result, {"sent": 1, "failed": 1})
        self.assertEqual(messaging.messages[0].tokens, ["token-active", "token-stale"])
        self.assertEqual(
            messaging.messages[0].data,
            {"type": "system", "site_id": "42"},
        )
        stale.refresh_from_db()
        self.assertFalse(stale.is_active)
        active.refresh_from_db()
        self.assertTrue(active.is_active)

    def test_broadcast_push_targets_mobile_devices_and_includes_route_payload(self):
        self._device(self.user, "token-user")
        self._device(self.other, "token-other")
        self.other.customer_profile.is_mobile_user = False
        self.other.customer_profile.save(update_fields=["is_mobile_user", "updated_at"])
        message = BroadcastMessage.objects.create(
            title="Guard update",
            body="A new guard dispatch was assigned.",
            message_type=BroadcastMessage.TYPE_ALERT,
            send_push=True,
            push_data={"route": "/guard/dispatch", "event_type": "dispatch", "ignored": None},
        )
        messaging = FakeMessaging([FakeFCMResponse(success=True)])

        from unittest.mock import patch

        with patch("apps.communication.push.get_firebase_messaging", return_value=messaging):
            result = _dispatch_push(message)

        self.assertEqual(result, {"sent": 1, "failed": 0})
        self.assertEqual(messaging.messages[0].tokens, ["token-user"])
        self.assertEqual(messaging.messages[0].data["type"], BroadcastMessage.TYPE_ALERT)
        self.assertEqual(messaging.messages[0].data["message_id"], str(message.id))
        self.assertEqual(messaging.messages[0].data["route"], "/guard/dispatch")
        self.assertEqual(messaging.messages[0].data["event_type"], "dispatch")
        self.assertNotIn("ignored", messaging.messages[0].data)

    def test_alarm_generic_push_uses_shared_multicast_sender(self):
        self._device(self.user, "token-alarm")
        messaging = FakeMessaging([FakeFCMResponse(success=True)])

        from unittest.mock import patch

        with patch("apps.communication.push.get_firebase_messaging", return_value=messaging):
            sent = _send_generic_fcm_notification(
                self.user,
                "Alarm",
                "Front door",
                {"type": "alarm", "event_id": 12},
            )

        self.assertEqual(sent, 1)
        self.assertEqual(messaging.messages[0].tokens, ["token-alarm"])
        self.assertEqual(
            messaging.messages[0].data,
            {"type": "alarm", "event_id": "12"},
        )
