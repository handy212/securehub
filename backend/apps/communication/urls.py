from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    BroadcastMessageViewSet,
    MarkMessageViewedView,
    UserMessageListView,
    WebNotificationSummaryView,
)

router = DefaultRouter()
router.register(r"broadcast", BroadcastMessageViewSet, basename="broadcast")

urlpatterns = [
    path("", include(router.urls)),
    path("messages/", UserMessageListView.as_view(), name="user-messages"),
    path("messages/summary/", WebNotificationSummaryView.as_view(), name="message-summary"),
    path("messages/<uuid:pk>/viewed/", MarkMessageViewedView.as_view(), name="message-viewed"),
]
