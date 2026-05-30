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
        self.operations_user = User.objects.create_user(
            username="operations",
            email="operations@example.com",
            password="testpass123",
            is_staff=True,
        )
        StaffOperatorProfile.objects.create(
            user=self.operations_user,
            role=OperatorRole.OPERATIONS,
        )
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

    def test_operations_role_can_access_site_map(self):
        self.client.login(username="operations", password="testpass123")
        response = self.client.get(reverse("dashboard:site-map"))
        self.assertEqual(response.status_code, 200)

    def test_operations_role_cannot_access_settings(self):
        self.client.login(username="operations", password="testpass123")
        response = self.client.get(reverse("dashboard:settings"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("dashboard:home"))

    def test_operations_role_cannot_manage_subscriptions(self):
        self.client.login(username="operations", password="testpass123")
        response = self.client.get(reverse("dashboard:subscriptions"))
        self.assertEqual(response.status_code, 200)
        response = self.client.post(
            reverse("dashboard:subscription-create"),
            {
                "site_id": "",
                "monthly_rate": "99.00",
                "billing_day": "1",
                "grace_period_days": "7",
                "next_due_date": "2026-12-01",
            },
        )
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
