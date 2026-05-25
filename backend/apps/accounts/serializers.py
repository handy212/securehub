from django.contrib.auth import authenticate
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm
from django.contrib.auth.models import User, update_last_login
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from rest_framework.exceptions import AuthenticationFailed
from rest_framework import serializers
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import CustomerProfile, FCMDevice


class UserSerializer(serializers.ModelSerializer):
    billing_status = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("id", "username", "email", "first_name", "last_name", "billing_status")

    def get_billing_status(self, obj):
        from apps.sites.models import Subscription
        # A user is interrupted if ANY site they own (via access_list) is suspended or cancelled
        interrupted = Subscription.objects.filter(
            site__access_list__user=obj,
            site__access_list__role="owner",
            status__in=[Subscription.STATUS_SUSPENDED, Subscription.STATUS_CANCELLED]
        ).exists()
        return "interrupted" if interrupted else "active"


class CustomerProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = CustomerProfile
        fields = ("user", "phone_number", "is_mobile_user")


class FCMDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = FCMDevice
        fields = ("token", "platform")

    def validate_token(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Token must not be empty.")
        return value.strip()


class GoogleLoginSerializer(serializers.Serializer):
    id_token = serializers.CharField()

    def validate_id_token(self, value):
        from google.oauth2 import id_token
        from google.auth.transport import requests as google_requests
        from django.conf import settings

        try:
            # Verify the ID token using Google's public keys.
            idinfo = id_token.verify_oauth2_token(
                value, google_requests.Request(), settings.GOOGLE_CLIENT_ID
            )

            # ID token is valid. Check issuer.
            if idinfo["iss"] not in ["accounts.google.com", "https://accounts.google.com"]:
                raise serializers.ValidationError("Wrong issuer.")

            if not idinfo.get("email_verified", False):
                raise serializers.ValidationError("Google account email is not verified.")

            return idinfo
        except Exception as e:
            raise serializers.ValidationError(f"Invalid Google ID token: {str(e)}")


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()


def resolve_username_for_login(identifier: str) -> str:
    value = str(identifier or "").strip()
    if not value:
        return value
    if User.objects.filter(username=value).exists():
        return value
    user = User.objects.filter(email__iexact=value).order_by("id").first()
    return user.username if user else value


class CustomerTokenObtainPairSerializer(TokenObtainPairSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields[self.username_field].required = False
        self.fields["email"] = serializers.EmailField(write_only=True, required=False)

    def validate(self, attrs):
        identifier = attrs.get(self.username_field) or attrs.get("email") or ""
        authenticate_kwargs = {
            self.username_field: resolve_username_for_login(identifier),
            "password": attrs["password"],
        }
        try:
            authenticate_kwargs["request"] = self.context["request"]
        except KeyError:
            pass

        self.user = authenticate(**authenticate_kwargs)

        if not api_settings.USER_AUTHENTICATION_RULE(self.user):
            raise AuthenticationFailed(
                self.error_messages["no_active_account"],
                code="no_active_account",
            )

        if self.user.is_staff or self.user.is_superuser:
            raise AuthenticationFailed(
                "Staff accounts must use the operator console sign-in flow.",
                code="staff_console_only",
            )

        refresh = self.get_token(self.user)
        data = {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }

        if api_settings.UPDATE_LAST_LOGIN:
            update_last_login(None, self.user)

        return data


class PasswordResetRequestSerializer(serializers.Serializer):
    identifier = serializers.CharField(write_only=True, required=False, allow_blank=True)
    email = serializers.EmailField(write_only=True, required=False)

    def _email_for_identifier(self) -> str:
        identifier = self.validated_data.get("identifier") or self.validated_data.get("email") or ""
        identifier = identifier.strip()
        if not identifier:
            return ""
        user = User.objects.filter(username=identifier).first()
        if user:
            return user.email
        user = User.objects.filter(email__iexact=identifier).order_by("id").first()
        return user.email if user else identifier

    def save(self, **kwargs):
        email = self._email_for_identifier()
        form = PasswordResetForm(data={"email": email})
        if form.is_valid():
            form.save(
                request=self.context.get("request"),
                use_https=self.context.get("request").is_secure() if self.context.get("request") else False,
                email_template_name="dashboard/auth/password_reset_email.txt",
                subject_template_name="dashboard/auth/password_reset_subject.txt",
                **kwargs,
            )


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField(write_only=True)
    token = serializers.CharField(write_only=True)
    new_password1 = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password2 = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        try:
            user_id = force_str(urlsafe_base64_decode(attrs["uid"]))
            user = User.objects.get(pk=user_id)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            raise serializers.ValidationError({"token": "The password reset link is invalid."})

        if not default_token_generator.check_token(user, attrs["token"]):
            raise serializers.ValidationError({"token": "The password reset link is invalid or expired."})

        form = SetPasswordForm(
            user,
            {
                "new_password1": attrs["new_password1"],
                "new_password2": attrs["new_password2"],
            },
        )
        if not form.is_valid():
            raise serializers.ValidationError(form.errors)

        attrs["form"] = form
        return attrs

    def save(self, **kwargs):
        self.validated_data["form"].save()
