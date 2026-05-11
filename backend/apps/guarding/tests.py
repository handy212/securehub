from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.sites.models import Site

from .models import ClockEvent, FieldReport, GuardPanicAlert, GuardPost, GuardProfile, Shift, ShiftAssignment


class GuardingApiTests(APITestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username="operator",
            password="StrongPass123!",
            is_staff=True,
        )
        self.guard_user = User.objects.create_user(
            username="guard1",
            password="StrongPass123!",
            first_name="Ama",
            last_name="Mensah",
        )
        self.site = Site.objects.create(
            name="Warehouse",
            hik_site_id="guard-site-1",
            latitude="5.603716000",
            longitude="-0.186964000",
        )
        self.guard = GuardProfile.objects.create(
            user=self.guard_user,
            employee_number="G-001",
            first_name="Ama",
            last_name="Mensah",
            phone_number="+233200000001",
        )
        self.post = GuardPost.objects.create(
            site=self.site,
            name="Main Gate",
            latitude="5.603716000",
            longitude="-0.186964000",
        )
        self.shift = Shift.objects.create(
            post=self.post,
            starts_at=timezone.now(),
            ends_at=timezone.now() + timezone.timedelta(hours=8),
            status=Shift.Status.PUBLISHED,
        )
        self.assignment = ShiftAssignment.objects.create(shift=self.shift, guard=self.guard)

    def authenticate(self, user):
        self.client.force_authenticate(user=user)

    def test_staff_can_create_guard_post(self):
        self.authenticate(self.staff)

        response = self.client.post(
            reverse("guard-post-list"),
            {
                "site": str(self.site.id),
                "name": "Loading Bay",
                "code": "LOAD",
                "geofence_radius_m": 100,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(GuardPost.objects.filter(name="Loading Bay").exists())

    def test_non_staff_cannot_use_management_endpoint(self):
        self.authenticate(self.guard_user)

        response = self.client.get(reverse("guard-profile-list"))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_guard_can_list_own_shifts(self):
        self.authenticate(self.guard_user)

        response = self.client.get(reverse("guard-my-shifts"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["post_name"], "Main Gate")

    def test_guard_can_clock_in(self):
        self.authenticate(self.guard_user)

        response = self.client.post(
            reverse("guard-my-clock", kwargs={"assignment_id": self.assignment.id}),
            {
                "event_type": ClockEvent.EventType.CLOCK_IN,
                "latitude": "5.603716000",
                "longitude": "-0.186964000",
                "within_geofence": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.status, ShiftAssignment.Status.CLOCKED_IN)
        self.assertIsNotNone(self.assignment.clocked_in_at)

    def test_guard_can_submit_field_report_for_assignment(self):
        self.authenticate(self.guard_user)

        response = self.client.post(
            reverse("guard-my-reports"),
            {
                "assignment": str(self.assignment.id),
                "site": str(self.site.id),
                "report_type": FieldReport.ReportType.INCIDENT,
                "title": "Gate Incident",
                "body": "Visitor attempted access without appointment.",
                "latitude": "5.603716000",
                "longitude": "-0.186964000",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        report = FieldReport.objects.get(title="Gate Incident")
        self.assertEqual(report.guard, self.guard)
        self.assertEqual(report.site, self.site)
        self.assertEqual(report.post, self.post)

    def test_guard_can_raise_panic_alert(self):
        self.authenticate(self.guard_user)

        response = self.client.post(
            reverse("guard-my-panic"),
            {
                "assignment": str(self.assignment.id),
                "latitude": "5.603716000",
                "longitude": "-0.186964000",
                "note": "Need supervisor support.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        alert = GuardPanicAlert.objects.get()
        self.assertEqual(alert.guard, self.guard)
        self.assertEqual(alert.site, self.site)
        self.assertEqual(alert.status, GuardPanicAlert.Status.OPEN)

