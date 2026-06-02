from django.contrib.auth.models import User
from django.conf import settings
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import CustomerProfile, FCMDevice
from .profile import build_user_profile_payload
from .serializers import (
    CustomerProfileSerializer,
    FCMDeviceSerializer,
    CustomerTokenObtainPairSerializer,
    GoogleLoginSerializer,
    LogoutSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
)


class LoginRateThrottle(AnonRateThrottle):
    scope = "login"


class ThrottledTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomerTokenObtainPairSerializer
    throttle_classes = [LoginRateThrottle]


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(build_user_profile_payload(request.user))


class FCMDeviceView(APIView):
    """
    POST  /api/v1/notifications/register-device/
        Register or refresh an FCM token for the authenticated user.
        If the token already exists (any user), it is re-assigned to the
        current user and marked active — handles device token reuse after
        app reinstall.

    DELETE /api/v1/notifications/register-device/
        Deactivate the token on logout. Token is soft-deleted (is_active=False)
        rather than removed so historical delivery records stay intact.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = FCMDeviceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data["token"]
        platform = serializer.validated_data.get("platform", FCMDevice.PLATFORM_ANDROID)

        # Upsert: update existing token row or create a new one.
        FCMDevice.objects.update_or_create(
            token=token,
            defaults={"user": request.user, "platform": platform, "is_active": True},
        )
        return Response({"registered": True}, status=status.HTTP_200_OK)

    def delete(self, request):
        token = request.data.get("token", "").strip()
        if token:
            FCMDevice.objects.filter(
                user=request.user, token=token
            ).update(is_active=False)
        else:
            # Deactivate all devices for this user (full logout)
            FCMDevice.objects.filter(user=request.user).update(is_active=False)
        return Response(status=status.HTTP_204_NO_CONTENT)


class GoogleLoginView(APIView):
    """
    POST /api/v1/auth/google/
    Expects {"id_token": "..."}.
    Validates the token with Google, finds/creates the user, and returns JWT.
    """

    permission_classes = []
    throttle_classes = [LoginRateThrottle]

    def post(self, request):
        serializer = GoogleLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        idinfo = serializer.validated_data["id_token"]
        email = idinfo.get("email")
        first_name = idinfo.get("given_name", "")
        last_name = idinfo.get("family_name", "")
        google_subject = idinfo.get("sub")

        if not email:
            return Response(
                {"error": "Email not provided by Google."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        profile = None
        if google_subject:
            profile = CustomerProfile.objects.select_related("user").filter(
                google_subject=google_subject
            ).first()

        user = profile.user if profile else User.objects.filter(email=email).first()
        created = False

        if user and (user.is_staff or user.is_superuser):
            return Response(
                {"error": "Staff accounts must use the operator console sign-in flow."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if user and not user.is_active:
            return Response(
                {"error": "This account is inactive. Please contact support."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if not user:
            if not getattr(settings, "SECUREHUB_GOOGLE_AUTO_CREATE_USERS", False):
                return Response(
                    {"error": "This Google account has not been invited to SecureHub yet."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            username = email
            if User.objects.filter(username=username).exists():
                import uuid

                username = f"{email.split('@')[0]}_{uuid.uuid4().hex[:6]}"

            user = User.objects.create(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
            )
            user.set_unusable_password()
            user.save()
            created = True

        profile, _ = CustomerProfile.objects.get_or_create(
            user=user,
            defaults={
                "is_mobile_user": True,
                "google_subject": google_subject or None,
            },
        )

        if profile.google_subject and google_subject and profile.google_subject != google_subject:
            return Response(
                {"error": "This account is already linked to a different Google identity."},
                status=status.HTTP_409_CONFLICT,
            )

        updates = []
        if google_subject and not profile.google_subject:
            profile.google_subject = google_subject
            updates.append("google_subject")
        if not profile.is_mobile_user:
            profile.is_mobile_user = True
            updates.append("is_mobile_user")
        if updates:
            updates.append("updated_at")
            profile.save(update_fields=updates)

        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "username": user.username,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "is_new": created,
                },
            },
            status=status.HTTP_200_OK if not created else status.HTTP_201_CREATED,
        )


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            refresh = RefreshToken(serializer.validated_data["refresh"])
            token_user_id = str(refresh.payload.get(api_settings.USER_ID_CLAIM, ""))
            if token_user_id != str(request.user.id):
                return Response(
                    {"error": "Refresh token does not belong to the authenticated user."},
                    status=status.HTTP_403_FORBIDDEN,
                )
            refresh.blacklist()
        except TokenError as exc:
            return Response(
                {"error": f"Invalid refresh token: {exc}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(status=status.HTTP_205_RESET_CONTENT)


class PasswordResetRequestView(APIView):
    permission_classes = []
    throttle_classes = [LoginRateThrottle]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {
                "detail": (
                    "If an active account matches those details, password reset "
                    "instructions will be sent."
                )
            },
            status=status.HTTP_200_OK,
        )


class PasswordResetConfirmAPIView(APIView):
    permission_classes = []
    throttle_classes = [LoginRateThrottle]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "Password has been reset."}, status=status.HTTP_200_OK)
