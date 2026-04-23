from django.contrib.auth.models import User
from rest_framework import serializers

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
