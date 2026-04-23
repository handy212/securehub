from django.http import Http404
from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied

from .models import CustomerSiteAccess


def user_can_access_all_sites(user) -> bool:
    return bool(user and user.is_authenticated and (user.is_staff or user.is_superuser))


def get_accessible_site_ids_for_user(user):
    if not user or not user.is_authenticated:
        return CustomerSiteAccess.objects.none().values_list("site_id", flat=True)
    if user_can_access_all_sites(user):
        from .models import Site

        return Site.objects.values_list("id", flat=True)
    return CustomerSiteAccess.objects.filter(user=user).values_list("site_id", flat=True)


class HasSiteAccess(permissions.BasePermission):
    """
    Checks that the authenticated user has been granted access to the site
    identified by ``site_id`` in the URL kwargs.

    Also enforces subscription status: if the site's subscription is suspended
    or cancelled, access is blocked with HTTP 403.

    Raises Http404 for unknown/unauthorised site IDs to prevent enumeration.
    """

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        # Staff and superusers have unrestricted access to all sites
        if user_can_access_all_sites(user):
            return True

        site_id = view.kwargs.get("site_id") or view.kwargs.get("pk")
        if not site_id:
            return True  # No site_id in URL — defer to queryset filtering

        access = CustomerSiteAccess.objects.select_related(
            "site__subscription"
        ).filter(user=user, site_id=site_id).first()

        if not access:
            raise Http404

        # Subscription gate: block access when suspended or cancelled
        try:
            sub = access.site.subscription
            if sub.is_access_blocked():
                raise PermissionDenied(
                    detail=(
                        "Access to this site has been suspended due to a billing issue. "
                        "Please contact support to reactivate your subscription."
                    )
                )
        except access.site.__class__.subscription.RelatedObjectDoesNotExist:
            # No subscription record yet — allow access (site may not be onboarded yet)
            pass

        return True


class CanControlAlarm(HasSiteAccess):
    """
    Checks that the user has the ``can_control_alarm`` flag for the site.
    Inherits the subscription gate from HasSiteAccess.
    """

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False

        if user_can_access_all_sites(request.user):
            return True

        site_id = view.kwargs.get("site_id") or view.kwargs.get("pk")
        access = CustomerSiteAccess.objects.filter(
            user=request.user, site_id=site_id
        ).first()
        return bool(access and access.can_control_alarm)


class IsSubscriptionActive(permissions.BasePermission):
    """
    Enforces a strict, global subscription gate for customers.
    If the user OWNS any site whose subscription is currently suspended
    or cancelled, all access to core app features is blocked.

    Exceptions: Staff and superusers are never blocked.
    """

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        if user_can_access_all_sites(user):
            return True

        # Check if the user owns ANY site that is now suspended/cancelled
        # This acts as a "hard lockout" until payment is settled.
        blocked_owned_sites = CustomerSiteAccess.objects.filter(
            user=user,
            role=CustomerSiteAccess.ROLE_OWNER,
            site__subscription__status__in=[
                "suspended",
                "cancelled",
            ],
        ).exists()

        if blocked_owned_sites:
            raise PermissionDenied(
                detail=(
                    "Access to the mobile app has been suspended due to an outstanding "
                    "balance on one or more of your sites. Please settle any overdue "
                    "payments to regain access."
                )
            )

        return True
