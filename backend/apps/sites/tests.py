from unittest.mock import patch

from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.sites.models import AlarmPanelDevice, CustomerSiteAccess, Site, Subsystem


class StaffSiteAccessTests(APITestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username="staff",
            password="Secret123!",
            is_staff=True,
        )
        self.user = User.objects.create_user(
            username="viewer",
            password="Secret123!",
        )
        self.site = Site.objects.create(name="HQ", hik_site_id="hik-site-1")
        self.device = AlarmPanelDevice.objects.create(
            site=self.site,
            name="Panel 1",
            serial_number="SN-1",
            hik_device_id="device-1",
            is_online=True,
        )
        self.subsystem = Subsystem.objects.create(
            site=self.site,
            device=self.device,
            name="Partition 1",
            hik_subsystem_id="subsys-1",
        )

    def test_staff_can_list_sites_without_customer_access_row(self):
        self.client.force_authenticate(self.staff)

        response = self.client.get(reverse("site-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertTrue(response.data["results"][0]["canControlAlarm"])

    @patch("apps.alarms.views.HikPartnerService.execute_subsystem_command")
    def test_staff_can_execute_subsystem_command_without_customer_access_row(self, mock_execute):
        mock_execute.return_value = {"ok": True}
        self.client.force_authenticate(self.staff)

        response = self.client.post(
            reverse(
                "subsystem-command",
                kwargs={
                    "site_id": self.site.id,
                    "subsystem_id": self.subsystem.id,
                    "action": "arm",
                },
            ),
            {"idempotency_key": "staff-arm"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        mock_execute.assert_called_once()

    @patch("apps.sites.views.HikPartnerService.sync_site_devices")
    def test_staff_can_sync_site_inventory(self, mock_sync):
        mock_sync.return_value = {"synced_panels": 1}
        self.client.force_authenticate(self.staff)

        response = self.client.post(
            reverse("site-sync", kwargs={"pk": self.site.id}),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_sync.assert_called_once()

    @patch("apps.sites.views.HikPartnerService.sync_site_devices")
    def test_non_admin_cannot_sync_site_inventory(self, mock_sync):
        CustomerSiteAccess.objects.create(
            user=self.user,
            site=self.site,
            role=CustomerSiteAccess.ROLE_OWNER,
            can_control_alarm=True,
        )
        self.client.force_authenticate(self.user)

        response = self.client.post(
            reverse("site-sync", kwargs={"pk": self.site.id}),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        mock_sync.assert_not_called()

    def test_regular_user_only_sees_assigned_sites(self):
        other_site = Site.objects.create(name="Remote", hik_site_id="hik-site-2")
        CustomerSiteAccess.objects.create(user=self.user, site=other_site, role="viewer")
        self.client.force_authenticate(self.user)

        response = self.client.get(reverse("site-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], str(other_site.id))
