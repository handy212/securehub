from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from apps.accounts.models import StaffOperatorProfile
from apps.accounts.permissions import user_has_console_permission
from apps.accounts.rbac import OperatorRole, Perm


class ConsoleRBACTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password="testpass123",
            is_staff=True,
            is_superuser=True,
        )
        self.billing_user = User.objects.create_user(
            username="billing",
            email="billing@example.com",
            password="testpass123",
            is_staff=True,
        )
        StaffOperatorProfile.objects.create(user=self.billing_user, role=OperatorRole.BILLING)
        self.client = Client()

    def test_billing_role_cannot_access_staff_users(self):
        self.client.login(username="billing", password="testpass123")
        response = self.client.get(reverse("dashboard:user-list"))
        self.assertEqual(response.status_code, 403)

    def test_billing_role_can_access_subscriptions(self):
        self.client.login(username="billing", password="testpass123")
        response = self.client.get(reverse("dashboard:subscriptions"))
        self.assertEqual(response.status_code, 200)

    def test_billing_role_redirected_from_guarding(self):
        self.client.login(username="billing", password="testpass123")
        response = self.client.get(reverse("dashboard:guarding-overview"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("dashboard:home"))

    def test_superuser_has_all_permissions(self):
        for permission in Perm.__dict__.values():
            if isinstance(permission, str) and permission.startswith("console."):
                self.assertTrue(user_has_console_permission(self.admin, permission))

    def test_staff_user_create_assigns_role(self):
        self.client.login(username="admin", password="testpass123")
        response = self.client.post(
            reverse("dashboard:user-create"),
            {
                "username": "dispatcher1",
                "email": "dispatcher1@example.com",
                "password": "testpass123",
                "first_name": "Dispatch",
                "last_name": "User",
                "role": OperatorRole.DISPATCHER,
            },
        )
        self.assertEqual(response.status_code, 302)
        created = User.objects.get(username="dispatcher1")
        self.assertEqual(created.operator_profile.role, OperatorRole.DISPATCHER)
