from unittest.mock import patch
from datetime import timedelta

from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.emergency.models import (
    AccountEmergencyService,
    EmergencyLocationUpdate,
    EmergencyRequest,
    EmergencyServicePlan,
    SiteEmergencyService,
)
from apps.sites.models import CustomerSiteAccess, Site, Subscription, SubscriptionPackage


class EmergencyApiTests(APITestCase):
    def setUp(self):
        self.customer = User.objects.create_user(
            username="customer",
            password="StrongPass123!",
            email="customer@example.com",
        )
        self.staff = User.objects.create_user(
            username="operator",
            password="StrongPass123!",
            email="operator@example.com",
            is_staff=True,
        )
        self.site = Site.objects.create(
            name="Main Residence",
            hik_site_id="site-001",
            latitude="5.603716000",
            longitude="-0.186964000",
        )
        self.other_site = Site.objects.create(name="Other Site", hik_site_id="site-002")
        CustomerSiteAccess.objects.create(
            user=self.customer,
            site=self.site,
            role=CustomerSiteAccess.ROLE_OWNER,
            can_control_alarm=True,
        )
        self.plan = EmergencyServicePlan.objects.create(
            name="Emergency Patrol",
            monthly_rate="50.00",
        )
        self.payload = {
            "site_id": str(self.site.id),
            "trigger_context": EmergencyRequest.CONTEXT_AWAY,
            "latitude": "5.604000000",
            "longitude": "-0.187000000",
            "accuracy_m": "12.50",
            "contact_phone": "+233200000000",
            "note": "Need patrol support",
        }

    def authenticate(self, user):
        self.client.force_authenticate(user=user)

    def test_status_reports_disabled_without_account_or_site_addon(self):
        self.authenticate(self.customer)

        response = self.client.get(reverse("emergency-status"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["enabled"])
        self.assertFalse(response.data["account_enabled"])
        self.assertFalse(response.data["site_enabled"])

    @patch("apps.emergency.views.dispatch_emergency_notifications.delay")
    def test_create_request_rejected_without_emergency_addon(self, mock_notify):
        self.authenticate(self.customer)

        response = self.client.post(reverse("emergency-requests"), self.payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("emergency_service", response.data)
        mock_notify.assert_not_called()

    @patch("apps.emergency.views.dispatch_emergency_notifications.delay")
    def test_account_addon_allows_away_from_site_request_without_site_id(self, mock_notify):
        AccountEmergencyService.objects.create(
            user=self.customer,
            plan=self.plan,
            monthly_rate="50.00",
            next_due_date=timezone.localdate(),
        )
        self.authenticate(self.customer)
        payload = {**self.payload}
        payload.pop("site_id")

        response = self.client.post(reverse("emergency-requests"), payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(response.data["site"])
        self.assertEqual(EmergencyLocationUpdate.objects.count(), 1)
        mock_notify.assert_called_once()

    @patch("apps.emergency.views.dispatch_emergency_notifications.delay")
    def test_site_addon_allows_request_for_assigned_site(self, mock_notify):
        SiteEmergencyService.objects.create(
            site=self.site,
            plan=self.plan,
            monthly_rate="50.00",
            next_due_date=timezone.localdate(),
        )
        self.authenticate(self.customer)

        response = self.client.post(reverse("emergency-requests"), self.payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(str(response.data["site"]), str(self.site.id))
        self.assertEqual(response.data["status"], EmergencyRequest.STATUS_OPEN)
        mock_notify.assert_called_once()

    def test_location_update_refreshes_latest_location_for_active_request(self):
        AccountEmergencyService.objects.create(user=self.customer, plan=self.plan, monthly_rate="50.00")
        emergency = EmergencyRequest.objects.create(
            customer=self.customer,
            latitude="5.604000000",
            longitude="-0.187000000",
        )
        self.authenticate(self.customer)

        response = self.client.post(
            reverse("emergency-location", kwargs={"request_id": emergency.id}),
            {
                "latitude": "5.605000000",
                "longitude": "-0.188000000",
                "accuracy_m": "8.00",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        emergency.refresh_from_db()
        self.assertEqual(str(emergency.latitude), "5.605000000")
        self.assertEqual(emergency.location_updates.count(), 1)

    def test_location_update_rejected_after_request_is_cancelled(self):
        AccountEmergencyService.objects.create(user=self.customer, plan=self.plan, monthly_rate="50.00")
        emergency = EmergencyRequest.objects.create(
            customer=self.customer,
            status=EmergencyRequest.STATUS_CANCELLED,
            latitude="5.604000000",
            longitude="-0.187000000",
        )
        self.authenticate(self.customer)

        response = self.client.post(
            reverse("emergency-location", kwargs={"request_id": emergency.id}),
            {"latitude": "5.605000000", "longitude": "-0.188000000"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_staff_can_transition_request_to_dispatched(self):
        emergency = EmergencyRequest.objects.create(
            customer=self.customer,
            site=self.site,
            latitude="5.604000000",
            longitude="-0.187000000",
        )
        self.authenticate(self.staff)

        response = self.client.post(
            reverse(
                "emergency-staff-transition",
                kwargs={"request_id": emergency.id, "action": "dispatch"},
            ),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        emergency.refresh_from_db()
        self.assertEqual(emergency.status, EmergencyRequest.STATUS_DISPATCHED)
        self.assertEqual(emergency.dispatched_by, self.staff)

    def test_staff_can_open_emergency_service_management_page(self):
        self.client.force_login(self.staff)

        response = self.client.get(reverse("dashboard:emergency-services"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, "Emergency Add-ons")

    def test_emergency_console_is_incident_queue_without_embedded_map(self):
        EmergencyRequest.objects.create(
            customer=self.customer,
            site=self.site,
            latitude="5.604000000",
            longitude="-0.187000000",
        )
        self.client.force_login(self.staff)

        response = self.client.get(reverse("dashboard:emergency"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, "Emergency Dispatch")
        self.assertContains(response, "Incident Queue")
        self.assertContains(response, "Client Map")
        self.assertNotContains(response, "Map System")
        self.assertNotContains(response, 'id="map"')
        self.assertNotContains(response, 'id="sites-data"')

    def test_client_map_receives_active_emergency_requests(self):
        EmergencyRequest.objects.create(
            customer=self.customer,
            site=self.site,
            latitude="5.604000000",
            longitude="-0.187000000",
        )
        self.client.force_login(self.staff)

        response = self.client.get(reverse("dashboard:site-map"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, 'id="emergencies-data"')
        self.assertEqual(len(response.context["emergencies_data"]), 1)
        self.assertEqual(response.context["emergencies_data"][0]["customer"], self.customer.username)
        self.assertEqual(response.context["emergencies_data"][0]["site"], self.site.name)

    def test_billing_page_renders_emergency_addon_state(self):
        Subscription.objects.create(
            site=self.site,
            monthly_rate="120.00",
            billing_day=1,
            grace_period_days=7,
            next_due_date=timezone.localdate(),
        )
        SiteEmergencyService.objects.create(
            site=self.site,
            monthly_rate="45.00",
            status="active",
            next_due_date=timezone.localdate(),
        )
        self.client.force_login(self.staff)

        response = self.client.get(reverse("dashboard:subscriptions"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, "Emergency MRR")
        self.assertContains(response, "Combined MRR")
        self.assertContains(response, "Patrol active")
        self.assertContains(response, "GH₵45.00/mo")

    def test_staff_can_create_site_emergency_service_from_console(self):
        self.client.force_login(self.staff)

        response = self.client.post(
            reverse("dashboard:site-emergency-create"),
            {
                "site_id": str(self.site.id),
                "plan_id": str(self.plan.id),
                "monthly_rate": "55.00",
                "status": "active",
                "next_due_date": str(timezone.localdate()),
            },
        )

        self.assertRedirects(response, reverse("dashboard:emergency-services"))
        service = SiteEmergencyService.objects.get(site=self.site)
        self.assertEqual(str(service.monthly_rate), "55.00")

    def test_staff_can_update_and_delete_emergency_plan(self):
        self.client.force_login(self.staff)

        response = self.client.post(
            reverse("dashboard:emergency-plan-update", kwargs={"plan_id": self.plan.pk}),
            {
                "name": "Priority Patrol",
                "monthly_rate": "75.00",
                "description": "Priority response",
                "is_active": "1",
            },
        )

        self.assertRedirects(response, reverse("dashboard:emergency-services"))
        self.plan.refresh_from_db()
        self.assertEqual(self.plan.name, "Priority Patrol")
        self.assertEqual(str(self.plan.monthly_rate), "75.00")

        response = self.client.post(reverse("dashboard:emergency-plan-delete", kwargs={"plan_id": self.plan.pk}))

        self.assertRedirects(response, reverse("dashboard:emergency-services"))
        self.assertFalse(EmergencyServicePlan.objects.filter(pk=self.plan.pk).exists())

    def test_staff_can_delete_site_emergency_service(self):
        service = SiteEmergencyService.objects.create(site=self.site, monthly_rate="45.00", status="active")
        self.client.force_login(self.staff)

        response = self.client.post(reverse("dashboard:site-emergency-delete", kwargs={"service_id": service.pk}))

        self.assertRedirects(response, reverse("dashboard:emergency-services"))
        self.assertFalse(SiteEmergencyService.objects.filter(pk=service.pk).exists())

    def test_staff_can_delete_account_emergency_service(self):
        service = AccountEmergencyService.objects.create(user=self.customer, monthly_rate="50.00", status="active")
        self.client.force_login(self.staff)

        response = self.client.post(reverse("dashboard:account-emergency-delete", kwargs={"service_id": service.pk}))

        self.assertRedirects(response, reverse("dashboard:emergency-services"))
        self.assertFalse(AccountEmergencyService.objects.filter(pk=service.pk).exists())

    def test_new_subscription_can_include_emergency_addon(self):
        self.client.force_login(self.staff)
        unsubscribed_site = Site.objects.create(name="New Customer Site", hik_site_id="site-new")
        core_package = SubscriptionPackage.objects.create(
            name="Premium",
            monthly_rate="120.00",
            includes_emergency_service=True,
            emergency_monthly_rate="45.00",
        )

        response = self.client.post(
            reverse("dashboard:subscription-create"),
            {
                "site_id": str(unsubscribed_site.id),
                "package_id": str(core_package.id),
                "monthly_rate": "120.00",
                "billing_day": "1",
                "grace_period_days": "7",
                "next_due_date": str(timezone.localdate()),
                "emergency_enabled": "1",
                "emergency_monthly_rate": "45.00",
            },
        )

        self.assertRedirects(response, reverse("dashboard:subscriptions"))
        service = SiteEmergencyService.objects.get(site=unsubscribed_site)
        self.assertEqual(str(service.monthly_rate), "45.00")
        self.assertEqual(service.status, "active")

    def test_edit_subscription_can_cancel_emergency_addon(self):
        sub = Subscription.objects.create(
            site=self.site,
            monthly_rate="120.00",
            billing_day=1,
            grace_period_days=7,
            next_due_date=timezone.localdate(),
        )
        SiteEmergencyService.objects.create(site=self.site, monthly_rate="45.00", status="active")
        self.client.force_login(self.staff)

        response = self.client.post(
            reverse("dashboard:subscription-update", kwargs={"pk": sub.pk}),
            {
                "monthly_rate": "120.00",
                "billing_day": "1",
                "grace_period_days": "7",
                "next_due_date": str(timezone.localdate()),
                "notes": "",
            },
        )

        self.assertRedirects(response, reverse("dashboard:subscriptions"))
        service = SiteEmergencyService.objects.get(site=self.site)
        self.assertEqual(service.status, "cancelled")

    def test_subscription_payment_syncs_emergency_due_date(self):
        sub = Subscription.objects.create(
            site=self.site,
            monthly_rate="120.00",
            billing_day=1,
            grace_period_days=7,
            next_due_date=timezone.localdate(),
        )
        service = SiteEmergencyService.objects.create(site=self.site, monthly_rate="45.00", status="overdue")
        self.client.force_login(self.staff)
        start = timezone.localdate()
        end = start.replace(day=min(start.day + 1, 28))

        response = self.client.post(
            reverse("dashboard:subscription-pay", kwargs={"pk": sub.pk}),
            {
                "amount": "165.00",
                "period_start": str(start),
                "period_end": str(end),
                "method": "cash",
            },
        )

        self.assertRedirects(response, reverse("dashboard:subscriptions"))
        service.refresh_from_db()
        self.assertEqual(service.next_due_date, end + timedelta(days=1))
        self.assertEqual(service.status, "active")
