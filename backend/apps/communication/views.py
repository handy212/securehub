from rest_framework import generics, status, viewsets, permissions
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Q
from django.shortcuts import get_object_or_404

from .models import BroadcastMessage, BroadcastMessageView
from .serializers import BroadcastMessageSerializer


def _message_recipient_filter(user):
    profile = getattr(user, "customer_profile", None)
    group_id = getattr(profile, "group_id", None)

    query = Q(recipient__isnull=True, recipient_group__isnull=True) | Q(recipient=user)
    if group_id:
        query |= Q(recipient_group_id=group_id)
    return query


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
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return (
            BroadcastMessage.objects.filter(
                _message_recipient_filter(user),
                status=BroadcastMessage.STATUS_SENT,
            )
            .prefetch_related("views")
            .order_by("-created_at")[:50]
        )


class MarkMessageViewedView(APIView):
    """
    Mobile app calls POST here when the user opens a notification.
    Idempotent — safe to call multiple times.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        message = get_object_or_404(
            BroadcastMessage, pk=pk, status=BroadcastMessage.STATUS_SENT
        )
        if not BroadcastMessage.objects.filter(
            _message_recipient_filter(request.user),
            pk=message.pk,
            status=BroadcastMessage.STATUS_SENT,
        ).exists():
            raise PermissionDenied("You cannot mark this message as viewed.")
        BroadcastMessageView.objects.get_or_create(message=message, user=request.user)
        return Response({"viewed": True}, status=status.HTTP_200_OK)
