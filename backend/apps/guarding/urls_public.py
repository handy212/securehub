from django.urls import path

from .public_views import PublicGuardApplySuccessView, PublicGuardApplyView

urlpatterns = [
    path("", PublicGuardApplyView.as_view(), name="guarding-public-apply"),
    path(
        "success/<uuid:applicant_id>/",
        PublicGuardApplySuccessView.as_view(),
        name="guarding-public-apply-success",
    ),
]
