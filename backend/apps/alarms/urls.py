from django.urls import path
from . import views

urlpatterns = [
    path("webhook/", views.HikWebhookView.as_view(), name="hik-webhook"),
    path("events/", views.GlobalEventListView.as_view(), name="global-events"),
    path(
        "sites/<uuid:site_id>/events/<uuid:event_id>/picture/",
        views.AlarmPictureURLView.as_view(),
        name="alarm-picture-url",
    ),
]
