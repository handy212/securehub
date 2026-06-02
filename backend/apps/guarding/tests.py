from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.urls import reverse
from django.utils import timezone
from decimal import Decimal
from rest_framework import status
from rest_framework.test import APITestCase

from .applicant_intake import validate_public_application

from apps.sites.models import Site
from apps.accounts.models import StaffOperatorProfile
from apps.accounts.rbac import OperatorRole

from .models import (
    Checkpoint,
    CheckpointScan,
    ClockEvent,
    ClientPortalAccess,
    DispatchTask,
    FieldReport,
    GuardApplicant,
    GuardApplicantDocument,
    GuardApplicantProfile,
    GuardContract,
    GuardCredential,
    GuardInvoice,
    GuardPanicAlert,
    GuardLocationPing,
    GuardPost,
    GuardProfile,
    GuardTimesheet,
    PatrolRoute,
    PatrolRouteCheckpoint,
    PatrolRound,
    Shift,
    ShiftAssignment,
    ShiftSwapRequest,
    WelfareCheck,
)
from .asset_models import (
    GuardAssetDepot,
    GuardAssetStock,
    GuardAssetType,
    GuardAssetUnit,
    GuardingAssetPolicy,
    PostAssetKit,
    PostAssetKitLine,
    ShiftAssetManifest,
    ShiftAssetManifestLine,
)
from .asset_services import (
    add_manifest_line,
    build_manifest_for_assignment,
    close_manifest,
    delete_manifest_line,
    issue_manifest_line,
    rebuild_manifest_for_assignment,
    update_manifest_line,
)
from .services import build_command_center_snapshot, ensure_guard_compliance_ready, guard_compliance_issues, hire_applicant
from .tasks import mark_overdue_patrol_rounds, mark_overdue_welfare_checks


def _public_apply_post_data(**overrides):
    data = {
        "first_name": "Kofi",
        "last_name": "Mensah",
        "phone_number": "+233200000100",
        "email": "kofi@example.com",
        "declaration_signed": "1",
        "declaration_signature_name": "Kofi Mensah",
        "document_type": ["national_id", "photo", "cv"],
        "document_title": ["National ID", "Passport photo", "CV / Resume"],
        "education_level": ["Senior High School"],
        "education_institution": ["Accra Academy"],
        "education_year": ["2015"],
        "education_certificates": [""],
        "employment_company": ["SecureCo"],
        "employment_position": ["Guard"],
        "employment_duties": [""],
        "employment_supervisor": [""],
        "employment_supervisor_contact": [""],
        "employment_started_on": [""],
        "employment_ended_on": [""],
        "employment_years": [""],
        "employment_reason": [""],
        "reference_name": ["Jane Doe"],
        "reference_company": ["Ref Ltd"],
        "reference_position": ["Manager"],
        "reference_phone": ["+233200000200"],
    }
    data.update(overrides)
    return data


def _public_apply_files():
    return [
        SimpleUploadedFile("id.pdf", b"%PDF-id", content_type="application/pdf"),
        SimpleUploadedFile("photo.jpg", b"\xff\xd8photo", content_type="image/jpeg"),
        SimpleUploadedFile("cv.pdf", b"%PDF-cv", content_type="application/pdf"),
    ]


class PublicGuardApplyTests(APITestCase):
    """Public /apply/guard/ intake flow (HTML form, not API)."""

    def setUp(self):
        self.public_client = Client()

    def test_get_apply_page_renders_form(self):
        response = self.public_client.get("/apply/guard/")
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn("id=\"guard-apply-form\"", html)
        self.assertIn("novalidate", html)
        self.assertIn("window.guardApplyForm", html)
        self.assertIn("Security guard application", html)
        self.assertIn("data-required-doc", html)

    def test_full_submission_redirects_to_success(self):
        payload = _public_apply_post_data(
            height_cm="175",
            weight_kg="70",
            skill_communication="4",
            skill_computer="3",
        )
        payload["document_file"] = _public_apply_files()
        response = self.public_client.post("/apply/guard/", payload)
        self.assertEqual(response.status_code, 302)
        applicant = GuardApplicant.objects.get(first_name="Kofi", last_name="Mensah")
        self.assertTrue(response.url.endswith(f"/apply/guard/success/{applicant.pk}/"))
        success = self.public_client.get(response.url)
        self.assertContains(success, "Application submitted")
        self.assertContains(success, applicant.full_name)
        profile = applicant.profile
        self.assertEqual(profile.height_cm, 175)
        self.assertEqual(profile.weight_kg, 70)
        self.assertEqual(profile.skill_communication, 4)

    def test_invalid_skill_rating_rejected(self):
        payload = _public_apply_post_data(skill_communication="9")
        payload["document_file"] = _public_apply_files()
        response = self.public_client.post("/apply/guard/", payload)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/apply/guard/")
        self.assertFalse(GuardApplicant.objects.filter(first_name="Kofi").exists())
        retry = self.public_client.get("/apply/guard/")
        self.assertContains(retry, "1 to 5")

    def test_validation_error_preserves_session(self):
        payload = _public_apply_post_data(first_name="", last_name="")
        payload["document_file"] = _public_apply_files()
        response = self.public_client.post("/apply/guard/", payload)
        self.assertEqual(response.status_code, 302)
        retry = self.public_client.get("/apply/guard/")
        self.assertContains(retry, "First name and last name are required")

    def test_validate_public_application_documents(self):
        from django.test import RequestFactory

        request = RequestFactory().post(
            "/apply/guard/",
            {
                "first_name": "A",
                "last_name": "B",
                "phone_number": "1",
                "declaration_signed": "1",
                "declaration_signature_name": "A B",
            },
        )
        with self.assertRaises(ValueError) as ctx:
            validate_public_application(request)
        self.assertIn("required documents", str(ctx.exception).lower())


class GuardingApiTests(APITestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username="operator",
            password="StrongPass123!",
            is_staff=True,
        )
        StaffOperatorProfile.objects.create(user=self.staff, role=OperatorRole.GUARDING)
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
            emergency_contact_name="Emergency Contact",
            emergency_contact_phone="+233200000099",
        )
        GuardCredential.objects.create(
            guard=self.guard,
            credential_type=GuardCredential.CredentialType.LICENSE,
            name="Security License",
            verified=True,
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

    def test_guard_can_list_pending_welfare_checks(self):
        check = WelfareCheck.objects.create(
            assignment=self.assignment,
            due_at=timezone.now() + timezone.timedelta(minutes=15),
            status=WelfareCheck.Status.PENDING,
        )
        self.authenticate(self.guard_user)
        response = self.client.get(reverse("guard-my-welfare-checks"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], str(check.id))
        self.assertEqual(response.data[0]["site_name"], self.site.name)

    def test_guard_can_confirm_recently_missed_welfare_check(self):
        check = WelfareCheck.objects.create(
            assignment=self.assignment,
            due_at=timezone.now() - timezone.timedelta(minutes=10),
            status=WelfareCheck.Status.MISSED,
        )
        self.authenticate(self.guard_user)

        response = self.client.post(
            reverse("guard-my-welfare-confirm", args=[check.id]),
            {"note": "Safe"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        check.refresh_from_db()
        self.assertEqual(check.status, WelfareCheck.Status.CONFIRMED)
        self.assertEqual(check.response_note, "Safe")

    def test_guard_can_submit_field_report(self):
        self.authenticate(self.guard_user)
        response = self.client.post(
            reverse("guard-my-reports"),
            {
                "assignment": str(self.assignment.id),
                "report_type": FieldReport.ReportType.INCIDENT,
                "title": "Gate incident",
                "body": "Visitor refused entry.",
                "status": FieldReport.Status.SUBMITTED,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(FieldReport.objects.filter(title="Gate incident", guard=self.guard).exists())

    def test_profile_returns_guard_account_kind(self):
        self.authenticate(self.guard_user)
        response = self.client.get("/api/v1/profile/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["account_kind"], "guard")
        self.assertEqual(response.data["guard_profile_id"], str(self.guard.id))

    def test_guard_can_list_patrol_rounds(self):
        route = PatrolRoute.objects.create(post=self.post, name="Perimeter")
        checkpoint = Checkpoint.objects.create(
            post=self.post,
            name="Gate A",
            code="GATE-A",
        )
        PatrolRouteCheckpoint.objects.create(route=route, checkpoint=checkpoint, sequence=1)
        patrol_round = PatrolRound.objects.create(
            route=route,
            assignment=self.assignment,
            scheduled_start=timezone.now(),
            scheduled_end=timezone.now() + timezone.timedelta(hours=1),
        )
        self.authenticate(self.guard_user)
        response = self.client.get(reverse("guard-my-patrol-rounds"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        rows = response.data["results"] if isinstance(response.data, dict) else response.data
        self.assertEqual(len(rows), 1)
        self.assertEqual(str(rows[0]["id"]), str(patrol_round.id))

    def test_checkpoint_scan_idempotent_by_client_scan_id(self):
        route = PatrolRoute.objects.create(post=self.post, name="Perimeter")
        checkpoint = Checkpoint.objects.create(post=self.post, name="Gate A", code="GATE-A")
        PatrolRouteCheckpoint.objects.create(route=route, checkpoint=checkpoint, sequence=1)
        patrol_round = PatrolRound.objects.create(
            route=route,
            assignment=self.assignment,
            scheduled_start=timezone.now(),
            scheduled_end=timezone.now() + timezone.timedelta(hours=1),
            status=PatrolRound.Status.IN_PROGRESS,
        )
        self.authenticate(self.guard_user)
        payload = {
            "checkpoint": str(checkpoint.id),
            "client_scan_id": "scan-uuid-1",
            "within_geofence": True,
        }
        url = reverse("guard-my-scan", kwargs={"patrol_round_id": patrol_round.id})
        first = self.client.post(url, payload, format="json")
        second = self.client.post(url, payload, format="json")
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_201_CREATED)
        self.assertEqual(first.data["id"], second.data["id"])
        self.assertEqual(CheckpointScan.objects.filter(patrol_round=patrol_round).count(), 1)

    def test_staff_command_center_snapshot(self):
        self.authenticate(self.staff)
        response = self.client.get(reverse("guard-command-center"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("guards", response.data)

    def test_guard_can_list_own_shifts(self):
        self.authenticate(self.guard_user)

        response = self.client.get(reverse("guard-my-shifts"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        rows = response.data["results"] if isinstance(response.data, dict) else response.data
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["post_name"], "Main Gate")

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
        self.assertEqual(response.data["location_label"], "Main Gate - Warehouse")
        self.assertEqual(response.data["coordinates"], "5.603716, -0.186964")
        self.assertIn("google.com/maps", response.data["map_url"])
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.status, ShiftAssignment.Status.CLOCKED_IN)
        self.assertIsNotNone(self.assignment.clocked_in_at)
        self.assertTrue(
            GuardLocationPing.objects.filter(
                guard=self.guard,
                assignment=self.assignment,
                latitude="5.603716000",
                longitude="-0.186964000",
            ).exists()
        )

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
        self.assertEqual(response.data["location_label"], "Main Gate - Warehouse")
        self.assertEqual(response.data["coordinates"], "5.603716, -0.186964")
        self.assertIn("google.com/maps", response.data["map_url"])
        alert = GuardPanicAlert.objects.get()
        self.assertEqual(alert.guard, self.guard)
        self.assertEqual(alert.site, self.site)
        self.assertEqual(alert.status, GuardPanicAlert.Status.OPEN)
        ping = GuardLocationPing.objects.get()
        self.assertEqual(ping.guard, self.guard)
        self.assertEqual(ping.assignment, self.assignment)
        self.assertEqual(ping.latitude, alert.latitude)
        self.assertEqual(ping.longitude, alert.longitude)

    def test_guard_panic_location_places_guard_on_command_map(self):
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
        snapshot = build_command_center_snapshot()
        self.assertEqual(len(snapshot["guards"]), 1)
        self.assertEqual(snapshot["guards"][0]["guard_id"], str(self.guard.id))
        self.assertEqual(snapshot["guards"][0]["latitude"], GuardPanicAlert.objects.get().latitude)

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
        self.assertEqual(applicant.hired_guard.status, GuardProfile.Status.INACTIVE)

    def test_guard_compliance_issues_require_contact_and_credential(self):
        bare_guard = GuardProfile.objects.create(
            employee_number="G-099",
            first_name="Test",
            last_name="Guard",
        )
        issues = guard_compliance_issues(bare_guard)
        self.assertIn("Emergency contact name is required.", issues)
        self.assertIn("At least one verified, non-expired credential is required.", issues)

        bare_guard.emergency_contact_name = "Parent"
        bare_guard.emergency_contact_phone = "+233200000099"
        bare_guard.save(update_fields=["emergency_contact_name", "emergency_contact_phone", "updated_at"])
        issues = guard_compliance_issues(bare_guard)
        self.assertEqual(len(issues), 1)

        GuardCredential.objects.create(
            guard=bare_guard,
            credential_type=GuardCredential.CredentialType.LICENSE,
            name="Security License",
            verified=True,
        )
        self.assertEqual(guard_compliance_issues(bare_guard), [])

    def test_cannot_activate_guard_without_compliance(self):
        bare_guard = GuardProfile.objects.create(
            employee_number="G-098",
            first_name="Inactive",
            last_name="Guard",
            status=GuardProfile.Status.INACTIVE,
        )
        self.authenticate(self.staff)
        response = self.client.patch(
            reverse("guard-profile-detail", kwargs={"pk": bare_guard.id}),
            {"status": GuardProfile.Status.ACTIVE},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_compliant_guard_can_be_activated_and_assigned(self):
        self.guard.emergency_contact_name = "Parent"
        self.guard.emergency_contact_phone = "+233200000099"
        self.guard.save(update_fields=["emergency_contact_name", "emergency_contact_phone", "updated_at"])
        GuardCredential.objects.create(
            guard=self.guard,
            credential_type=GuardCredential.CredentialType.LICENSE,
            name="Security License",
            verified=True,
        )
        ensure_guard_compliance_ready(self.guard)
        self.guard.status = GuardProfile.Status.ACTIVE
        self.guard.save(update_fields=["status", "updated_at"])

        other_shift = Shift.objects.create(
            post=self.post,
            starts_at=timezone.now() + timezone.timedelta(days=2),
            ends_at=timezone.now() + timezone.timedelta(days=2, hours=8),
            status=Shift.Status.PUBLISHED,
        )
        self.authenticate(self.staff)
        response = self.client.post(
            reverse("guard-shift-assignment-list"),
            {"shift": str(other_shift.id), "guard": str(self.guard.id)},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_hire_applicant_copies_location_metadata(self):
        applicant = GuardApplicant.objects.create(
            first_name="Esi",
            last_name="Owusu",
            status=GuardApplicant.Status.OFFERED,
            address="12 Ring Road",
            city="Accra",
            country="Ghana",
            national_id="GHA-123456789",
            emergency_contact_name="Ama Contact",
            emergency_contact_phone="+233200000010",
        )
        GuardApplicantProfile.objects.create(applicant=applicant, security_training_completed=True)
        guard = hire_applicant(applicant, employee_number="G-010", actor=self.staff)
        self.assertEqual(guard.status, GuardProfile.Status.INACTIVE)
        self.assertEqual(guard.home_address, "12 Ring Road")
        self.assertEqual(guard.metadata.get("city"), "Accra")
        self.assertEqual(guard.metadata.get("country"), "Ghana")
        self.assertEqual(guard.metadata.get("national_id"), "GHA-123456789")
        self.assertEqual(guard.emergency_contact_name, "Ama Contact")
        self.assertEqual(guard.emergency_contact_phone, "+233200000010")
        self.assertTrue(guard.training_records.filter(name="Security Training").exists())

    def test_hire_applicant_copies_documents(self):
        applicant = GuardApplicant.objects.create(
            first_name="Doc",
            last_name="Test",
            status=GuardApplicant.Status.OFFERED,
        )
        GuardApplicantDocument.objects.create(
            applicant=applicant,
            document_type=GuardApplicantDocument.DocumentType.NATIONAL_ID,
            title="Ghana Card",
            file=SimpleUploadedFile("ghana-card.pdf", b"pdf-content", content_type="application/pdf"),
        )
        guard = hire_applicant(applicant, employee_number="G-011", actor=self.staff)
        self.assertEqual(guard.documents.count(), 1)

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

    def test_assignment_requires_post_qualification(self):
        self.post.required_credentials = ["Gate License"]
        self.post.save(update_fields=["required_credentials", "updated_at"])
        other_guard = GuardProfile.objects.create(
            employee_number="G-003",
            first_name="Kwame",
            last_name="Owusu",
            emergency_contact_name="Contact",
            emergency_contact_phone="+233200000003",
        )
        self.authenticate(self.staff)

        blocked = self.client.post(
            reverse("guard-shift-assignment-list"),
            {"shift": str(self.shift.id), "guard": str(other_guard.id)},
            format="json",
        )
        GuardCredential.objects.create(
            guard=other_guard,
            credential_type=GuardCredential.CredentialType.LICENSE,
            name="Gate License",
            verified=True,
        )
        allowed = self.client.post(
            reverse("guard-shift-assignment-list"),
            {"shift": str(self.shift.id), "guard": str(other_guard.id)},
            format="json",
        )

        self.assertEqual(blocked.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(allowed.status_code, status.HTTP_201_CREATED)

    def test_guard_can_request_shift_swap_and_staff_can_approve(self):
        target_guard = GuardProfile.objects.create(
            employee_number="G-004",
            first_name="Esi",
            last_name="Adjei",
        )
        self.authenticate(self.guard_user)
        create_response = self.client.post(
            reverse("guard-my-shift-swaps"),
            {
                "assignment": str(self.assignment.id),
                "target_guard": str(target_guard.id),
                "reason": "Family appointment",
            },
            format="json",
        )
        swap = ShiftSwapRequest.objects.get()
        self.authenticate(self.staff)
        review_response = self.client.post(
            reverse("guard-shift-swap-review", kwargs={"pk": swap.id}),
            {"status": ShiftSwapRequest.Status.APPROVED, "note": "Covered."},
            format="json",
        )

        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(review_response.status_code, status.HTTP_200_OK)
        self.assignment.refresh_from_db()
        swap.refresh_from_db()
        self.assertEqual(self.assignment.guard, target_guard)
        self.assertEqual(swap.status, ShiftSwapRequest.Status.APPROVED)

    def test_client_can_acknowledge_approved_visible_report(self):
        client_user = User.objects.create_user(username="client", password="StrongPass123!")
        ClientPortalAccess.objects.create(
            user=client_user,
            site=self.site,
            can_view_reports=True,
            can_acknowledge_reports=True,
        )
        report = FieldReport.objects.create(
            site=self.site,
            post=self.post,
            assignment=self.assignment,
            guard=self.guard,
            report_type=FieldReport.ReportType.DAILY_ACTIVITY,
            title="Client DAR",
            status=FieldReport.Status.APPROVED,
            visible_to_client=True,
        )
        self.authenticate(client_user)

        response = self.client.post(
            reverse("guard-client-report-acknowledge", kwargs={"report_id": report.id}),
            {"comment": "Seen"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(report.client_acknowledgements.count(), 1)

    def test_client_portal_snapshot_exposes_safe_mobile_payload(self):
        client_user = User.objects.create_user(username="mobile-client", password="StrongPass123!")
        ClientPortalAccess.objects.create(
            user=client_user,
            site=self.site,
            can_view_reports=True,
            can_view_patrols=True,
            can_view_attendance=True,
            can_view_guards=True,
            can_acknowledge_reports=True,
        )
        FieldReport.objects.create(
            site=self.site,
            post=self.post,
            assignment=self.assignment,
            guard=self.guard,
            report_type=FieldReport.ReportType.DAILY_ACTIVITY,
            title="Mobile DAR",
            body="Visible operational summary.",
            status=FieldReport.Status.APPROVED,
            visible_to_client=True,
        )
        route = PatrolRoute.objects.create(post=self.post, name="Perimeter")
        checkpoint = Checkpoint.objects.create(post=self.post, name="Gate", code="GATE")
        PatrolRouteCheckpoint.objects.create(route=route, checkpoint=checkpoint, sequence=1)
        round_ = PatrolRound.objects.create(
            route=route,
            assignment=self.assignment,
            scheduled_start=timezone.now(),
            scheduled_end=timezone.now() + timezone.timedelta(minutes=30),
        )
        CheckpointScan.objects.create(patrol_round=round_, checkpoint=checkpoint, guard=self.guard)
        self.authenticate(client_user)

        response = self.client.get(reverse("guard-client-portal"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["counts"]["guards"], 1)
        self.assertEqual(response.data["known_guards"][0]["guard_name"], "Ama Mensah")
        self.assertEqual(response.data["known_guards"][0]["employee_number"], "G-001")
        self.assertEqual(response.data["known_guards"][0]["verified_credentials"], ["Security License"])
        self.assertEqual(response.data["reports"][0]["title"], "Mobile DAR")
        payload = str(response.data)
        self.assertNotIn("+233200000001", payload)
        self.assertNotIn("Emergency Contact", payload)
        self.assertNotIn("+233200000099", payload)

    def test_client_portal_snapshot_requires_client_access(self):
        user = User.objects.create_user(username="no-client-access", password="StrongPass123!")
        self.authenticate(user)

        response = self.client.get(reverse("guard-client-portal"))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_guarding_staff_api_requires_guarding_console_permission(self):
        operations_user = User.objects.create_user(
            username="ops-api-user",
            password="StrongPass123!",
            is_staff=True,
        )
        StaffOperatorProfile.objects.create(user=operations_user, role=OperatorRole.OPERATIONS)

        self.authenticate(operations_user)
        denied_response = self.client.get(reverse("guard-profile-list"))
        self.assertEqual(denied_response.status_code, status.HTTP_403_FORBIDDEN)

        self.authenticate(self.staff)
        allowed_response = self.client.get(reverse("guard-profile-list"))
        self.assertEqual(allowed_response.status_code, status.HTTP_200_OK)

    def test_guard_mobile_user_cannot_access_staff_guarding_api(self):
        self.authenticate(self.guard_user)

        response = self.client.get(reverse("guard-profile-list"))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_client_access_api_rejects_operator_accounts(self):
        self.authenticate(self.staff)

        response = self.client.post(
            reverse("guard-client-access-list"),
            {
                "user": self.staff.pk,
                "site": self.site.pk,
                "role": ClientPortalAccess.Role.VIEWER,
                "can_view_reports": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(ClientPortalAccess.objects.filter(user=self.staff, site=self.site).exists())

    def test_staff_can_generate_invoice_from_approved_timesheet(self):
        GuardContract.objects.create(
            site=self.site,
            post=self.post,
            name="Warehouse Guarding",
            status=GuardContract.Status.ACTIVE,
            starts_on=timezone.localdate() - timezone.timedelta(days=1),
            bill_rate=Decimal("20.00"),
            pay_rate=Decimal("10.00"),
        )
        period_start = timezone.now() - timezone.timedelta(hours=1)
        timesheet = GuardTimesheet.objects.create(
            assignment=self.assignment,
            guard=self.guard,
            site=self.site,
            post=self.post,
            period_start=period_start,
            period_end=timezone.now(),
            regular_minutes=60,
            bill_amount=Decimal("160.00"),
            pay_amount=Decimal("80.00"),
            status=GuardTimesheet.Status.APPROVED,
        )
        self.authenticate(self.staff)

        response = self.client.post(
            reverse("guard-invoice-generate"),
            {
                "site": str(self.site.id),
                "period_start": timezone.localtime(period_start).date().isoformat(),
                "period_end": timezone.localdate().isoformat(),
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        invoice = GuardInvoice.objects.get()
        timesheet.refresh_from_db()
        self.assertEqual(invoice.total, Decimal("160.00"))
        self.assertEqual(invoice.lines.count(), 1)
        self.assertEqual(timesheet.status, GuardTimesheet.Status.EXPORTED)

    def test_public_apply_creates_applicant_and_children(self):
        payload = _public_apply_post_data(security_training_completed="1")
        payload["document_file"] = _public_apply_files()
        response = self.client.post("/apply/guard/", payload)
        self.assertEqual(response.status_code, 302)
        applicant = GuardApplicant.objects.get(first_name="Kofi", last_name="Mensah")
        self.assertEqual(applicant.source, "public_web")
        self.assertTrue(applicant.declaration_signed_at)
        self.assertTrue(applicant.metadata.get("public_submission"))
        self.assertTrue(hasattr(applicant, "profile"))
        self.assertEqual(applicant.education_records.count(), 1)
        self.assertEqual(applicant.employment_records.count(), 1)
        self.assertEqual(applicant.references.count(), 1)
        self.assertEqual(applicant.documents.count(), 3)

    def test_public_apply_requires_mandatory_documents(self):
        response = self.client.post(
            "/apply/guard/",
            {
                "first_name": "Kofi",
                "last_name": "Mensah",
                "phone_number": "+233200000100",
                "declaration_signed": "1",
                "declaration_signature_name": "Kofi Mensah",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/apply/guard/")
        self.assertFalse(GuardApplicant.objects.filter(first_name="Kofi", last_name="Mensah").exists())

    def test_guard_profile_metadata_saved_from_console(self):
        self.client.force_login(self.staff)
        response = self.client.post(
            reverse("dashboard:guarding-guards"),
            {
                "action": "guard",
                "employee_number": "G-099",
                "first_name": "Kwame",
                "last_name": "Boateng",
                "phone_number": "+233200000150",
                "national_id": "GHA-999",
                "city": "Kumasi",
                "country": "Ghana",
                "emergency_contact_name": "Contact",
                "emergency_contact_phone": "+233200000151",
                "status": "inactive",
            },
        )
        self.assertEqual(response.status_code, 302)
        guard = GuardProfile.objects.get(employee_number="G-099")
        self.assertEqual(guard.metadata.get("national_id"), "GHA-999")
        self.assertEqual(guard.metadata.get("city"), "Kumasi")

    def test_staff_can_download_applicant_pdf(self):
        applicant = GuardApplicant.objects.create(
            first_name="Ama",
            last_name="Public",
            phone_number="+233200000101",
            source="public_web",
            declaration_signature_name="Ama Public",
            declaration_signed_at=timezone.now(),
        )
        GuardApplicantProfile.objects.create(applicant=applicant)
        self.client.force_login(self.staff)
        response = self.client.get(
            reverse("dashboard:guarding-applicant-pdf", kwargs={"applicant_id": applicant.id})
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertTrue(response.content.startswith(b"%PDF"))


class GuardAssetManagementTests(APITestCase):
    def setUp(self):
        self.staff = User.objects.create_user(username="assetop", password="pass", is_staff=True)
        StaffOperatorProfile.objects.create(user=self.staff, role=OperatorRole.GUARDING)
        self.guard_user = User.objects.create_user(username="assetguard", password="pass")
        self.site = Site.objects.create(name="Asset Site", hik_site_id="asset-site-1")
        self.guard = GuardProfile.objects.create(
            user=self.guard_user,
            employee_number="G-ASSET",
            first_name="Asset",
            last_name="Guard",
            phone_number="+233200000300",
            emergency_contact_name="EC",
            emergency_contact_phone="+233200000301",
        )
        GuardCredential.objects.create(
            guard=self.guard,
            credential_type=GuardCredential.CredentialType.LICENSE,
            name="License",
            verified=True,
        )
        self.post = GuardPost.objects.create(site=self.site, name="Gate")
        self.depot = GuardAssetDepot.objects.create(name="Main Armory", site=self.site)
        self.radio_type = GuardAssetType.objects.create(
            name="Radio",
            code="RADIO",
            tracking_mode=GuardAssetType.TrackingMode.SERIAL,
        )
        self.key_type = GuardAssetType.objects.create(
            name="Keys",
            code="KEYS",
            tracking_mode=GuardAssetType.TrackingMode.QUANTITY,
        )
        self.unit = GuardAssetUnit.objects.create(
            asset_type=self.radio_type,
            depot=self.depot,
            asset_tag="RAD-001",
        )
        GuardAssetStock.objects.create(asset_type=self.key_type, depot=self.depot, quantity_on_hand=5)
        kit = PostAssetKit.objects.create(post=self.post, name="Standard", is_default=True)
        PostAssetKitLine.objects.create(kit=kit, asset_type=self.radio_type, quantity_required=1)
        PostAssetKitLine.objects.create(kit=kit, asset_type=self.key_type, quantity_required=2)
        self.shift = Shift.objects.create(
            post=self.post,
            starts_at=timezone.now(),
            ends_at=timezone.now() + timezone.timedelta(hours=8),
            status=Shift.Status.PUBLISHED,
        )
        self.assignment = ShiftAssignment.objects.create(shift=self.shift, guard=self.guard)

    def test_build_manifest_creates_lines_from_kit(self):
        manifest = build_manifest_for_assignment(self.assignment, depot=self.depot)
        self.assertEqual(manifest.lines.count(), 2)
        self.assertEqual(manifest.status, ShiftAssetManifest.Status.DRAFT)

    def test_issue_serial_and_quantity_lines(self):
        manifest = build_manifest_for_assignment(self.assignment, depot=self.depot)
        radio_line = manifest.lines.get(asset_type=self.radio_type)
        key_line = manifest.lines.get(asset_type=self.key_type)
        issue_manifest_line(radio_line, asset_unit=self.unit, issued_by=self.staff)
        issue_manifest_line(key_line, quantity=2, issued_by=self.staff, depot=self.depot)
        radio_line.refresh_from_db()
        key_line.refresh_from_db()
        self.unit.refresh_from_db()
        self.assertEqual(radio_line.status, ShiftAssetManifestLine.Status.ISSUED)
        self.assertEqual(key_line.issued_qty, 2)
        self.assertEqual(self.unit.status, GuardAssetUnit.Status.ISSUED)

    def test_strict_policy_blocks_clock_in_without_issue(self):
        GuardingAssetPolicy.objects.create(
            post=self.post,
            default_mode=GuardingAssetPolicy.EnforcementMode.STRICT,
            enforce_issue_before_clock_in=True,
        )
        build_manifest_for_assignment(self.assignment, depot=self.depot)
        self.client.force_authenticate(user=self.guard_user)
        self.client.post(
            reverse("guard-my-shift-action", kwargs={"assignment_id": self.assignment.id, "action": "accept"}),
            format="json",
        )
        response = self.client.post(
            reverse("guard-my-clock", kwargs={"assignment_id": self.assignment.id}),
            {"event_type": ClockEvent.EventType.CLOCK_IN},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_advisory_allows_clock_in_without_issue(self):
        from .models import GuardingEventLog

        GuardingAssetPolicy.objects.create(
            post=self.post,
            default_mode=GuardingAssetPolicy.EnforcementMode.ADVISORY,
        )
        build_manifest_for_assignment(self.assignment, depot=self.depot)
        self.client.force_authenticate(user=self.guard_user)
        self.client.post(
            reverse("guard-my-shift-action", kwargs={"assignment_id": self.assignment.id, "action": "accept"}),
            format="json",
        )
        response = self.client.post(
            reverse("guard-my-clock", kwargs={"assignment_id": self.assignment.id}),
            {"event_type": ClockEvent.EventType.CLOCK_IN},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            GuardingEventLog.objects.filter(
                event_type="asset_advisory_clock_in",
                guard=self.guard,
            ).exists()
        )

    def test_cannot_issue_more_quantity_than_stock(self):
        from django.core.exceptions import ValidationError

        manifest = build_manifest_for_assignment(self.assignment, depot=self.depot)
        key_line = manifest.lines.get(asset_type=self.key_type)
        with self.assertRaises(ValidationError):
            issue_manifest_line(key_line, quantity=99, issued_by=self.staff, depot=self.depot)

    def test_cannot_issue_more_than_expected_quantity(self):
        from django.core.exceptions import ValidationError

        manifest = build_manifest_for_assignment(self.assignment, depot=self.depot)
        key_line = manifest.lines.get(asset_type=self.key_type)
        issue_manifest_line(key_line, quantity=2, issued_by=self.staff, depot=self.depot)
        key_line.refresh_from_db()
        with self.assertRaises(ValidationError):
            issue_manifest_line(key_line, quantity=1, issued_by=self.staff, depot=self.depot)

    def test_cannot_reissue_serial_line_or_close_with_returnable_assets_out(self):
        from django.core.exceptions import ValidationError

        second_unit = GuardAssetUnit.objects.create(
            asset_type=self.radio_type,
            depot=self.depot,
            asset_tag="RAD-002",
        )
        manifest = build_manifest_for_assignment(self.assignment, depot=self.depot)
        radio_line = manifest.lines.get(asset_type=self.radio_type)
        key_line = manifest.lines.get(asset_type=self.key_type)
        issue_manifest_line(radio_line, asset_unit=self.unit, issued_by=self.staff)
        issue_manifest_line(key_line, quantity=2, issued_by=self.staff, depot=self.depot)

        with self.assertRaises(ValidationError):
            issue_manifest_line(radio_line, asset_unit=second_unit, issued_by=self.staff)
        with self.assertRaises(ValidationError):
            close_manifest(manifest, closed_by=self.staff)

    def test_rebuild_manifest_replaces_pending_lines(self):
        manifest = build_manifest_for_assignment(self.assignment, depot=self.depot)
        self.assertEqual(manifest.lines.count(), 2)
        vest = GuardAssetType.objects.create(
            name="Vest",
            code="VEST",
            tracking_mode=GuardAssetType.TrackingMode.QUANTITY,
        )
        add_manifest_line(manifest, asset_type=vest, expected_qty=3)
        self.assertEqual(manifest.lines.count(), 3)
        rebuild_manifest_for_assignment(self.assignment, depot=self.depot)
        manifest.refresh_from_db()
        self.assertEqual(manifest.lines.count(), 2)
        self.assertFalse(manifest.lines.filter(asset_type=vest).exists())

    def test_manifest_line_crud_on_draft(self):
        manifest = build_manifest_for_assignment(self.assignment, depot=self.depot)
        vest = GuardAssetType.objects.create(
            name="Vest",
            code="VEST2",
            tracking_mode=GuardAssetType.TrackingMode.QUANTITY,
        )
        extra = add_manifest_line(manifest, asset_type=vest, expected_qty=2, notes="spare")
        extra = update_manifest_line(extra, expected_qty=4, notes="updated")
        self.assertEqual(extra.expected_qty, 4)
        delete_manifest_line(extra)
        self.assertEqual(manifest.lines.count(), 2)

    def test_asset_type_metadata_round_trip(self):
        asset_type = GuardAssetType.objects.create(
            name="Tagged",
            code="TAGGED",
            metadata={"vendor": "Acme", "warranty_months": 12},
            default_condition_check=False,
        )
        asset_type.refresh_from_db()
        self.assertEqual(asset_type.metadata["vendor"], "Acme")
        self.assertFalse(asset_type.default_condition_check)
