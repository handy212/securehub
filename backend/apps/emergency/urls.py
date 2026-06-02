from django.urls import path

from . import views

urlpatterns = [
    path("status/", views.EmergencyStatusView.as_view(), name="emergency-status"),
    path("requests/", views.EmergencyRequestListCreateView.as_view(), name="emergency-requests"),
    path(
        "requests/<uuid:request_id>/location/",
        views.EmergencyLocationUpdateView.as_view(),
        name="emergency-location",
    ),
    path(
        "requests/<uuid:request_id>/cancel/",
        views.EmergencyCancelView.as_view(),
        name="emergency-cancel",
    ),
    path(
        "requests/<uuid:request_id>/<str:action>/",
        views.EmergencyStaffTransitionView.as_view(),
        name="emergency-staff-transition",
    ),
]
