from unittest.mock import patch
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core.cache import cache
from django.core import mail
from django.test.utils import override_settings
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken
from .models import CustomerProfile

class GoogleLoginTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.url = reverse("google-login")
        self.logout_url = reverse("token-logout")
        self.refresh_url = reverse("token-refresh")

    @patch("google.oauth2.id_token.verify_oauth2_token")
    @override_settings(SECUREHUB_GOOGLE_AUTO_CREATE_USERS=True)
    def test_google_login_new_user_success(self, mock_verify):
        # Mock Google validation response
        mock_verify.return_value = {
            "iss": "https://accounts.google.com",
            "sub": "1234567890",
            "email": "testuser@gmail.com",
            "email_verified": True,
            "given_name": "Test",
            "family_name": "User",
        }

        response = self.client.post(self.url, {"id_token": "valid-token"})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertEqual(response.data["user"]["email"], "testuser@gmail.com")
        
        # Verify user and profile creation
        user = User.objects.get(email="testuser@gmail.com")
        self.assertEqual(user.first_name, "Test")
        self.assertEqual(user.last_name, "User")
        profile = CustomerProfile.objects.get(user=user)
        self.assertEqual(profile.google_subject, "1234567890")

    @patch("google.oauth2.id_token.verify_oauth2_token")
    def test_google_login_rejects_uninvited_new_user_by_default(self, mock_verify):
        mock_verify.return_value = {
            "iss": "https://accounts.google.com",
            "sub": "new-subject",
            "email": "newuser@gmail.com",
            "email_verified": True,
            "given_name": "New",
            "family_name": "User",
        }

        response = self.client.post(self.url, {"id_token": "valid-token"})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(User.objects.filter(email="newuser@gmail.com").exists())

    @patch("google.oauth2.id_token.verify_oauth2_token")
    def test_google_login_existing_user_success(self, mock_verify):
        # Pre-create user
        user = User.objects.create_user(
            username="existinguser",
            email="existing@gmail.com",
            first_name="Existing",
            last_name="User"
        )
        
        # Mock Google validation response
        mock_verify.return_value = {
            "iss": "https://accounts.google.com",
            "sub": "1234567890",
            "email": "existing@gmail.com",
            "email_verified": True,
            "given_name": "ChangedName",
            "family_name": "User",
        }

        response = self.client.post(self.url, {"id_token": "valid-token"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["user"]["id"], user.id)
        self.assertFalse(response.data["user"]["is_new"])
        self.assertEqual(
            CustomerProfile.objects.get(user=user).google_subject,
            "1234567890",
        )

    @patch("google.oauth2.id_token.verify_oauth2_token")
    def test_google_login_invalid_token(self, mock_verify):
        # Mock verification failure
        mock_verify.side_effect = ValueError("Invalid token")

        response = self.client.post(self.url, {"id_token": "invalid-token"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("id_token", response.data)

    @patch("google.oauth2.id_token.verify_oauth2_token")
    def test_google_login_rejects_unverified_email(self, mock_verify):
        mock_verify.return_value = {
            "iss": "https://accounts.google.com",
            "sub": "subject-1",
            "email": "testuser@gmail.com",
            "email_verified": False,
        }

        response = self.client.post(self.url, {"id_token": "valid-token"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("id_token", response.data)

    @patch("google.oauth2.id_token.verify_oauth2_token")
    def test_google_login_rejects_conflicting_google_subject(self, mock_verify):
        user = User.objects.create_user(
            username="bound-user",
            email="bound@gmail.com",
        )
        CustomerProfile.objects.update_or_create(
            user=user,
            defaults={"google_subject": "existing-subject"},
        )
        mock_verify.return_value = {
            "iss": "https://accounts.google.com",
            "sub": "different-subject",
            "email": "bound@gmail.com",
            "email_verified": True,
        }

        response = self.client.post(self.url, {"id_token": "valid-token"})

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    @patch("google.oauth2.id_token.verify_oauth2_token")
    def test_google_login_rejects_staff_account_email(self, mock_verify):
        User.objects.create_user(
            username="operator",
            email="operator@example.com",
            password="Secret123!",
            is_staff=True,
        )
        mock_verify.return_value = {
            "iss": "https://accounts.google.com",
            "sub": "staff-subject",
            "email": "operator@example.com",
            "email_verified": True,
        }

        response = self.client.post(self.url, {"id_token": "valid-token"})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["error"], "Staff accounts must use the operator console sign-in flow.")

    @patch("google.oauth2.id_token.verify_oauth2_token")
    def test_google_login_rejects_inactive_user(self, mock_verify):
        User.objects.create_user(
            username="inactive-customer",
            email="inactive@example.com",
            password="Secret123!",
            is_active=False,
        )
        mock_verify.return_value = {
            "iss": "https://accounts.google.com",
            "sub": "inactive-subject",
            "email": "inactive@example.com",
            "email_verified": True,
        }

        response = self.client.post(self.url, {"id_token": "valid-token"})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["error"], "This account is inactive. Please contact support.")

    def test_password_login_rejects_staff_accounts(self):
        User.objects.create_user(
            username="staff-api-login",
            email="staff-api@example.com",
            password="Secret123!",
            is_staff=True,
        )

        response = self.client.post(
            reverse("token-obtain-pair"),
            {"username": "staff-api-login", "password": "Secret123!"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(
            response.data["detail"],
            "Staff accounts must use the operator console sign-in flow.",
        )

    def test_password_login_accepts_email_in_username_field(self):
        User.objects.create_user(
            username="email-login-user",
            email="email-login@example.com",
            password="Secret123!",
        )

        response = self.client.post(
            reverse("token-obtain-pair"),
            {"username": "email-login@example.com", "password": "Secret123!"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_password_login_accepts_email_field(self):
        User.objects.create_user(
            username="explicit-email-login-user",
            email="explicit-email-login@example.com",
            password="Secret123!",
        )

        response = self.client.post(
            reverse("token-obtain-pair"),
            {"email": "explicit-email-login@example.com", "password": "Secret123!"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_logout_blacklists_refresh_token(self):
        user = User.objects.create_user(username="logout-user", password="Secret123!")
        refresh = RefreshToken.for_user(user)
        access = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

        response = self.client.post(self.logout_url, {"refresh": str(refresh)}, format="json")

        self.assertEqual(response.status_code, status.HTTP_205_RESET_CONTENT)

        refresh_response = self.client.post(
            self.refresh_url,
            {"refresh": str(refresh)},
            format="json",
        )
        self.assertEqual(refresh_response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_rejects_refresh_token_for_different_user(self):
        user = User.objects.create_user(username="logout-owner", password="Secret123!")
        other = User.objects.create_user(username="logout-other", password="Secret123!")
        access = str(RefreshToken.for_user(user).access_token)
        other_refresh = RefreshToken.for_user(other)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

        response = self.client.post(
            self.logout_url,
            {"refresh": str(other_refresh)},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        refresh_response = self.client.post(
            self.refresh_url,
            {"refresh": str(other_refresh)},
            format="json",
        )
        self.assertEqual(refresh_response.status_code, status.HTTP_200_OK)

    def test_password_reset_request_sends_email_for_username(self):
        User.objects.create_user(
            username="recoverable-user",
            email="recoverable@example.com",
            password="Secret123!",
        )

        response = self.client.post(
            reverse("password-reset-request"),
            {"identifier": "recoverable-user"},
            format="json",
            HTTP_HOST="testserver",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("/console/password-reset/", mail.outbox[0].body)

    def test_password_reset_request_does_not_reveal_unknown_account(self):
        response = self.client.post(
            reverse("password-reset-request"),
            {"identifier": "nobody@example.com"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 0)

    def test_password_reset_confirm_sets_new_password(self):
        user = User.objects.create_user(
            username="reset-confirm-user",
            email="reset-confirm@example.com",
            password="OldPass123!",
        )
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)

        response = self.client.post(
            reverse("password-reset-confirm-api"),
            {
                "uid": uid,
                "token": token,
                "new_password1": "NewPass123!",
                "new_password2": "NewPass123!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertTrue(user.check_password("NewPass123!"))

    def test_password_reset_confirm_rejects_invalid_token(self):
        user = User.objects.create_user(
            username="reset-invalid-user",
            email="reset-invalid@example.com",
            password="OldPass123!",
        )
        uid = urlsafe_base64_encode(force_bytes(user.pk))

        response = self.client.post(
            reverse("password-reset-confirm-api"),
            {
                "uid": uid,
                "token": "bad-token",
                "new_password1": "NewPass123!",
                "new_password2": "NewPass123!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
