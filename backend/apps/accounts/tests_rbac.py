from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from apps.accounts.models import StaffOperatorProfile
from apps.accounts.permissions import user_has_console_permission
from apps.accounts.rbac import CONSOLE_ROUTE_PERMISSIONS, OperatorRole, Perm, permissions_for_role
from apps.dashboard.urls import urlpatterns as dashboard_urlpatterns


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

    def test_dashboard_routes_are_mapped_or_explicitly_exempt(self):
        auth_routes = {
            "login",
            "logout",
            "password-reset",
            "password-reset-done",
            "password-reset-confirm",
            "password-reset-complete",
        }
        non_staff_routes = {
            "client-guarding",
            "client-guarding-report-acknowledge",
            "client-guarding-reports-export",
        }
        route_names = {pattern.name for pattern in dashboard_urlpatterns if getattr(pattern, "name", None)}
        missing = route_names - set(CONSOLE_ROUTE_PERMISSIONS) - auth_routes - non_staff_routes

        self.assertEqual(missing, set())

    def test_operator_role_permission_matrix(self):
        expected = {
            OperatorRole.PLATFORM_ADMIN: {
                Perm.MANAGE_STAFF,
                Perm.MANAGE_SETTINGS,
                Perm.MANAGE_GUARDING,
                Perm.MANAGE_BILLING,
            },
            OperatorRole.OPERATIONS: {
                Perm.MANAGE_SITES,
                Perm.MANAGE_CUSTOMERS,
                Perm.MANAGE_EMERGENCY,
                Perm.MANAGE_BROADCAST,
                Perm.GLOBAL_SYNC,
            },
            OperatorRole.GUARDING: {Perm.VIEW_GUARDING, Perm.MANAGE_GUARDING},
            OperatorRole.DISPATCHER: {Perm.VIEW_GUARDING, Perm.MANAGE_GUARDING, Perm.MANAGE_EMERGENCY},
            OperatorRole.BILLING: {Perm.VIEW_BILLING, Perm.MANAGE_BILLING},
            OperatorRole.SUPPORT: {Perm.VIEW_CUSTOMERS, Perm.MANAGE_CUSTOMERS, Perm.VIEW_LOGS},
            OperatorRole.AUDITOR: {Perm.VIEW_SITES, Perm.VIEW_GUARDING, Perm.VIEW_BILLING, Perm.VIEW_LOGS},
        }
        forbidden = {
            OperatorRole.OPERATIONS: {Perm.MANAGE_STAFF, Perm.MANAGE_SETTINGS, Perm.MANAGE_BILLING},
            OperatorRole.GUARDING: {Perm.MANAGE_STAFF, Perm.MANAGE_BILLING, Perm.MANAGE_SITES},
            OperatorRole.DISPATCHER: {Perm.MANAGE_STAFF, Perm.MANAGE_BILLING, Perm.MANAGE_CUSTOMERS},
            OperatorRole.BILLING: {Perm.MANAGE_STAFF, Perm.MANAGE_GUARDING, Perm.MANAGE_SITES},
            OperatorRole.SUPPORT: {Perm.MANAGE_STAFF, Perm.MANAGE_SITES, Perm.MANAGE_GUARDING},
            OperatorRole.AUDITOR: {Perm.MANAGE_STAFF, Perm.MANAGE_SITES, Perm.MANAGE_GUARDING},
        }

        for role, permissions in expected.items():
            granted = permissions_for_role(role)
            self.assertTrue(permissions.issubset(granted), role)
        for role, permissions in forbidden.items():
            granted = permissions_for_role(role)
            self.assertTrue(granted.isdisjoint(permissions), role)
