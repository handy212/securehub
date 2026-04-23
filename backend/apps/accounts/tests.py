from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase

from .models import CustomerProfile


class CustomerProfileSignalTests(TestCase):
    def test_profile_is_created_with_user(self):
        user = User.objects.create_user(username="new-user", password="Secret123!")

        self.assertTrue(CustomerProfile.objects.filter(user=user).exists())

    def test_seed_demo_creates_expected_login_users(self):
        stdout = StringIO()
        call_command("seed_demo", stdout=stdout)

        self.assertTrue(User.objects.filter(username="owner").exists())
        self.assertTrue(User.objects.filter(username="viewer").exists())
        self.assertIn("owner / DemoPass123!", stdout.getvalue())
