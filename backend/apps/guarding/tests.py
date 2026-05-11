from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.sites.models import Site

from .models import (
    Checkpoint,
    ClockEvent,
    DispatchTask,
    FieldReport,
    GuardApplicant,
    GuardPanicAlert,
    GuardPost,
    GuardProfile,
    PatrolRoute,
    PatrolRouteCheckpoint,
    PatrolRound,
    Shift,
    ShiftAssignment,
    WelfareCheck,
)
from .tasks import mark_overdue_patrol_rounds, mark_overdue_welfare_checks


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

        accept_response = self.client.post(
            reverse("guard-my-shift-action", kwargs={"assignment_id": self.assignment.id, "action": "accept"}),
            format="json",
        )
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

        self.assertEqual(accept_response.status_code, status.HTTP_200_OK)
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

    def test_staff_can_hire_applicant_into_guard_profile(self):
        applicant = GuardApplicant.objects.create(
            first_name="Kojo",
            last_name="Boateng",
            phone_number="+233200000002",
            email="kojo@example.com",
            status=GuardApplicant.Status.OFFERED,
        )
        self.authenticate(self.staff)

        response = self.client.post(
            reverse("guard-applicant-hire", kwargs={"pk": applicant.id}),
            {"employee_number": "G-002"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        applicant.refresh_from_db()
        self.assertEqual(applicant.status, GuardApplicant.Status.HIRED)
        self.assertEqual(applicant.hired_guard.employee_number, "G-002")

    def test_shift_requires_end_after_start(self):
        self.authenticate(self.staff)

        response = self.client.post(
            reverse("guard-shift-list"),
            {
                "post": str(self.post.id),
                "starts_at": timezone.now().isoformat(),
                "ends_at": (timezone.now() - timezone.timedelta(hours=1)).isoformat(),
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("ends_at", response.data)

    def test_guard_can_accept_assignment(self):
        self.authenticate(self.guard_user)

        response = self.client.post(
            reverse(
                "guard-my-shift-action",
                kwargs={"assignment_id": self.assignment.id, "action": "accept"},
            ),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.status, ShiftAssignment.Status.ACCEPTED)

    def test_patrol_route_rejects_checkpoint_from_another_post(self):
        other_post = GuardPost.objects.create(site=self.site, name="Rear Gate")
        route = PatrolRoute.objects.create(post=self.post, name="Main Patrol")
        checkpoint = Checkpoint.objects.create(post=other_post, name="Rear Door", code="rear-door")
        self.authenticate(self.staff)

        response = self.client.post(
            reverse("guard-patrol-route-checkpoint-list"),
            {
                "route": str(route.id),
                "checkpoint": str(checkpoint.id),
                "sequence": 1,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("checkpoint", response.data)

    def test_guard_can_complete_patrol_after_all_route_checkpoints_are_scanned(self):
        route = PatrolRoute.objects.create(post=self.post, name="Main Patrol")
        checkpoint = Checkpoint.objects.create(post=self.post, name="Front Door", code="front-door")
        PatrolRouteCheckpoint.objects.create(route=route, checkpoint=checkpoint, sequence=1)
        patrol_round = PatrolRound.objects.create(
            route=route,
            assignment=self.assignment,
            scheduled_start=timezone.now(),
            scheduled_end=timezone.now() + timezone.timedelta(minutes=30),
        )
        self.authenticate(self.guard_user)

        scan_response = self.client.post(
            reverse("guard-my-scan", kwargs={"patrol_round_id": patrol_round.id}),
            {
                "checkpoint": str(checkpoint.id),
                "latitude": "5.603716000",
                "longitude": "-0.186964000",
                "within_geofence": True,
            },
            format="json",
        )
        complete_response = self.client.post(
            reverse("guard-my-patrol-complete", kwargs={"patrol_round_id": patrol_round.id}),
            format="json",
        )

        self.assertEqual(scan_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(complete_response.status_code, status.HTTP_200_OK)
        patrol_round.refresh_from_db()
        self.assertEqual(patrol_round.status, PatrolRound.Status.COMPLETED)

    def test_staff_can_review_field_report(self):
        report = FieldReport.objects.create(
            site=self.site,
            post=self.post,
            assignment=self.assignment,
            guard=self.guard,
            report_type=FieldReport.ReportType.DAILY_ACTIVITY,
            title="DAR",
        )
        self.authenticate(self.staff)

        response = self.client.post(
            reverse("guard-field-report-review", kwargs={"pk": report.id}),
            {"status": FieldReport.Status.APPROVED, "note": "Looks good."},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        report.refresh_from_db()
        self.assertEqual(report.status, FieldReport.Status.APPROVED)
        self.assertEqual(report.reviewed_by, self.staff)

    def test_guard_can_progress_assigned_dispatch_task(self):
        task = DispatchTask.objects.create(
            site=self.site,
            assigned_guard=self.guard,
            status=DispatchTask.Status.ASSIGNED,
            priority=DispatchTask.Priority.HIGH,
            title="Check alarm",
        )
        self.authenticate(self.guard_user)

        accept_response = self.client.post(
            reverse(
                "guard-my-dispatch-action",
                kwargs={"task_id": task.id, "action": "accept"},
            ),
            format="json",
        )
        en_route_response = self.client.post(
            reverse(
                "guard-my-dispatch-action",
                kwargs={"task_id": task.id, "action": "en-route"},
            ),
            format="json",
        )
        arrive_response = self.client.post(
            reverse(
                "guard-my-dispatch-action",
                kwargs={"task_id": task.id, "action": "arrive"},
            ),
            format="json",
        )

        self.assertEqual(accept_response.status_code, status.HTTP_200_OK)
        self.assertEqual(en_route_response.status_code, status.HTTP_200_OK)
        self.assertEqual(arrive_response.status_code, status.HTTP_200_OK)
        task.refresh_from_db()
        self.assertEqual(task.status, DispatchTask.Status.ARRIVED)
        self.assertIsNotNone(task.accepted_at)
        self.assertIsNotNone(task.arrived_at)

    def test_overdue_tasks_mark_patrols_and_welfare_checks_missed(self):
        route = PatrolRoute.objects.create(post=self.post, name="Overdue Patrol")
        patrol_round = PatrolRound.objects.create(
            route=route,
            assignment=self.assignment,
            scheduled_start=timezone.now() - timezone.timedelta(hours=2),
            scheduled_end=timezone.now() - timezone.timedelta(hours=1),
        )
        welfare_check = WelfareCheck.objects.create(
            assignment=self.assignment,
            due_at=timezone.now() - timezone.timedelta(minutes=10),
        )

        self.assertEqual(mark_overdue_patrol_rounds(), 1)
        self.assertEqual(mark_overdue_welfare_checks(), 1)
        patrol_round.refresh_from_db()
        welfare_check.refresh_from_db()
        self.assertEqual(patrol_round.status, PatrolRound.Status.MISSED)
        self.assertEqual(welfare_check.status, WelfareCheck.Status.MISSED)
