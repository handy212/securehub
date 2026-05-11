from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import CustomerGroup

from .models import BroadcastMessage, BroadcastMessageView


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
