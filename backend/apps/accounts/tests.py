from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase

from .models import CustomerProfile
from .profile import build_user_profile_payload
from apps.guarding.models import ClientPortalAccess
from apps.sites.models import Site


class CustomerProfileSignalTests(TestCase):
    def test_profile_is_created_with_user(self):
        user = User.objects.create_user(username="new-user", password="Secret123!")

        self.assertTrue(CustomerProfile.objects.filter(user=user).exists())

    def test_seed_demo_creates_expected_login_users(self):
        stdout = StringIO()
        call_command("seed_demo", stdout=stdout)

        self.assertTrue(User.objects.filter(username="owner").exists())
        self.assertTrue(User.objects.filter(username="viewer").exists())
        self.assertTrue(User.objects.filter(username="guard-client").exists())
        guard_client = User.objects.get(username="guard-client")
        self.assertTrue(ClientPortalAccess.objects.filter(user=guard_client, can_view_guards=True).exists())
        self.assertTrue(Site.objects.filter(hik_site_id="demo-site-001").exists())
        self.assertIn("Guarding client portal login: guard-client", stdout.getvalue())

    def test_profile_payload_marks_guarding_client_access(self):
        user = User.objects.create_user(username="client-mobile", password="Secret123!")
        site = Site.objects.create(name="Client Site", hik_site_id="client-mobile-site")
        ClientPortalAccess.objects.create(user=user, site=site)

        payload = build_user_profile_payload(user)

        self.assertEqual(payload["account_kind"], "customer")
        self.assertTrue(payload["has_guarding_client_access"])
