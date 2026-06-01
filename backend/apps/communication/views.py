from django.utils import timezone
from rest_framework import generics, status, viewsets, permissions
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.db.models import Q
from django.shortcuts import get_object_or_404

from .models import BroadcastMessage, BroadcastMessageView
from .serializers import BroadcastMessageSerializer

MESSAGE_INBOX_STATUSES = (
    BroadcastMessage.STATUS_PENDING,
    BroadcastMessage.STATUS_SENT,
    BroadcastMessage.STATUS_FAILED,
)


def _message_recipient_filter(user):
    profile = getattr(user, "customer_profile", None)
    group_id = getattr(profile, "group_id", None)

    query = Q(recipient__isnull=True, recipient_group__isnull=True) | Q(recipient=user)
    if group_id:
        query |= Q(recipient_group_id=group_id)
    return query


def user_message_queryset(user):
    return (
        BroadcastMessage.objects.filter(
            _message_recipient_filter(user),
            status__in=MESSAGE_INBOX_STATUSES,
        )
        .select_related("recipient", "recipient_group")
        .prefetch_related("views")
        .order_by("-created_at")
    )


def serialize_web_notification(message, user):
    return {
        "id": str(message.id),
        "title": message.title,
        "body": message.body,
        "message_type": message.message_type,
        "status": message.status,
        "created_at": message.created_at.isoformat(),
        "created_at_display": timezone.localtime(message.created_at).strftime("%d %b %H:%M"),
        "is_viewed": message.views.filter(user=user).exists(),
    }


class BroadcastMessageViewSet(viewsets.ModelViewSet):
    queryset = BroadcastMessage.objects.all().order_by("-created_at")
    serializer_class = BroadcastMessageSerializer
    permission_classes = [permissions.IsAdminUser]

    def perform_create(self, serializer):
        from .tasks import send_broadcast_push_notifications
        message = serializer.save()
        send_broadcast_push_notifications.delay(str(message.id))


class UserMessageListView(generics.ListAPIView):
    """
    Mobile inbox: sent messages addressed to the current user — direct,
    via their group, or broadcast to all.
    """
    serializer_class = BroadcastMessageSerializer
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return user_message_queryset(self.request.user)[:50]


class WebNotificationSummaryView(APIView):
    """
    Lightweight web-console notification poll endpoint.
    """
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        queryset = user_message_queryset(request.user)
        return Response(
            {
                "unread_count": queryset.exclude(views__user=request.user).count(),
                "notifications": [
                    serialize_web_notification(message, request.user)
                    for message in queryset[:8]
                ],
            }
        )


class MarkMessageViewedView(APIView):
    """
    Mobile app calls POST here when the user opens a notification.
    Idempotent — safe to call multiple times.
    """
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        message = get_object_or_404(
            BroadcastMessage, pk=pk, status__in=MESSAGE_INBOX_STATUSES
        )
        if not BroadcastMessage.objects.filter(
            _message_recipient_filter(request.user),
            pk=message.pk,
            status__in=MESSAGE_INBOX_STATUSES,
        ).exists():
            raise PermissionDenied("You cannot mark this message as viewed.")
        BroadcastMessageView.objects.get_or_create(message=message, user=request.user)
        return Response({"viewed": True}, status=status.HTTP_200_OK)
