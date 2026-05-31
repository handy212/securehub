from __future__ import annotations

from datetime import datetime, time, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import CustomerProfile, StaffOperatorProfile
from apps.accounts.rbac import OperatorRole
from apps.alarms.models import AlarmEvent
from apps.guarding.models import (
    Checkpoint,
    CheckpointScan,
    ClientPortalAccess,
    DispatchTask,
    FieldReport,
    GuardCredential,
    GuardPost,
    GuardProfile,
    PatrolRoute,
    PatrolRouteCheckpoint,
    PatrolRound,
    Shift,
    ShiftAssignment,
)
from apps.sites.models import (
    AlarmPanelDevice,
    CustomerSiteAccess,
    OperationsZone,
    Site,
    Subsystem,
    Subscription,
    SubscriptionPackage,
    Zone,
)


class Command(BaseCommand):
    help = "Seed a rich demo dataset for console, alarm customer, guarding client, and guard workflows."

    DEMO_PASSWORD = "DemoPass123!"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset-passwords",
            action="store_true",
            help="Reset demo user passwords to DemoPass123!.",
        )

    def handle(self, *args, **options):
        reset_passwords = options["reset_passwords"]
        now = timezone.now()
        today = timezone.localdate()
        warehouse_shift_start = self._demo_datetime(today, days=1, hour=9)
        showroom_shift_start = self._demo_datetime(today, days=2, hour=10)

        admin = self._user(
            "demo-admin",
            "admin@example.com",
            first_name="Demo",
            last_name="Admin",
            is_staff=True,
            is_superuser=True,
            reset_password=reset_passwords,
        )
        self._operator_profile(admin, OperatorRole.PLATFORM_ADMIN)

        ops = self._staff("demo-ops", "ops@example.com", "Olivia", "Operations", OperatorRole.OPERATIONS, reset_passwords)
        guarding = self._staff("demo-guarding", "guarding@example.com", "Grace", "Guarding", OperatorRole.GUARDING, reset_passwords)
        dispatcher = self._staff("demo-dispatch", "dispatch@example.com", "Daniel", "Dispatch", OperatorRole.DISPATCHER, reset_passwords)
        billing = self._staff("demo-billing", "billing@example.com", "Binta", "Billing", OperatorRole.BILLING, reset_passwords)
        support = self._staff("demo-support", "support@example.com", "Sam", "Support", OperatorRole.SUPPORT, reset_passwords)
        auditor = self._staff("demo-auditor", "auditor@example.com", "Amina", "Auditor", OperatorRole.AUDITOR, reset_passwords)

        owner = self._customer("owner", "owner@example.com", "Site", "Owner", "+233200100001", reset_passwords)
        viewer = self._customer("viewer", "viewer@example.com", "Read", "Only", "+233200100002", reset_passwords)
        guarding_client = self._customer("guard-client", "guard.client@example.com", "Kwame", "Client", "+233200100003", reset_passwords)

        accra_zone, _ = OperationsZone.objects.update_or_create(
            name="Accra Central",
            defaults={"color": "#10b981", "description": "Core demo response area", "sort_order": 1, "is_active": True},
        )
        east_zone, _ = OperationsZone.objects.update_or_create(
            name="East Legon",
            defaults={"color": "#f59e0b", "description": "Secondary demo area", "sort_order": 2, "is_active": True},
        )

        warehouse = self._site(
            hik_site_id="demo-site-001",
            name="Warehouse North",
            address="15 Industrial Estate",
            city="Accra",
            country="Ghana",
            latitude=Decimal("5.603716000"),
            longitude=Decimal("-0.186964000"),
            operations_zone=accra_zone,
        )
        showroom = self._site(
            hik_site_id="demo-site-002",
            name="Retail Showroom",
            address="211 River Street",
            city="Accra",
            country="Ghana",
            latitude=Decimal("5.651000000"),
            longitude=Decimal("-0.148000000"),
            operations_zone=east_zone,
        )

        CustomerSiteAccess.objects.update_or_create(
            user=owner,
            site=warehouse,
            defaults={"role": CustomerSiteAccess.ROLE_OWNER, "can_control_alarm": True},
        )
        CustomerSiteAccess.objects.update_or_create(
            user=viewer,
            site=showroom,
            defaults={"role": CustomerSiteAccess.ROLE_VIEWER, "can_control_alarm": False},
        )

        package, _ = SubscriptionPackage.objects.update_or_create(
            name="Demo Guard + Alarm",
            defaults={
                "monthly_rate": Decimal("299.00"),
                "includes_emergency_service": True,
                "emergency_monthly_rate": Decimal("49.00"),
                "grace_period_days": 7,
                "description": "Demo package for testing billing, alarm, and guarding flows.",
                "is_active": True,
            },
        )
        for site in [warehouse, showroom]:
            Subscription.objects.update_or_create(
                site=site,
                defaults={
                    "package": package,
                    "monthly_rate": package.monthly_rate,
                    "billing_day": 1,
                    "next_due_date": today + timedelta(days=21),
                    "grace_period_days": package.grace_period_days,
                    "status": Subscription.STATUS_ACTIVE,
                    "notes": "Seeded demo subscription.",
                },
            )

        warehouse_subsystem = self._alarm_stack(warehouse, "demo-device-001", "DEMO-SN-001", "Main Warehouse")
        showroom_subsystem = self._alarm_stack(showroom, "demo-device-002", "DEMO-SN-002", "Showroom Floor")

        self._alarm_event(warehouse, warehouse_subsystem, "demo-event-001", "Front Door Alarm", AlarmEvent.SEVERITY_HIGH)
        self._alarm_event(showroom, showroom_subsystem, "demo-event-002", "Back Office Tamper", AlarmEvent.SEVERITY_MEDIUM)

        guard_user = self._user(
            "guard-ama",
            "guard.ama@example.com",
            first_name="Ama",
            last_name="Mensah",
            reset_password=reset_passwords,
        )
        backup_guard_user = self._user(
            "guard-kofi",
            "guard.kofi@example.com",
            first_name="Kofi",
            last_name="Boateng",
            reset_password=reset_passwords,
        )
        guard = self._guard(guard_user, "G-DEMO-001", "Ama", "Mensah", "+233200200001")
        backup_guard = self._guard(backup_guard_user, "G-DEMO-002", "Kofi", "Boateng", "+233200200002")
        self._credential(guard, "Security License", "PSA Ghana", "LIC-DEMO-001")
        self._credential(guard, "First Aid Training", "Red Cross", "FIRST-AID-DEMO")
        self._credential(backup_guard, "Security License", "PSA Ghana", "LIC-DEMO-002")

        main_gate, _ = GuardPost.objects.update_or_create(
            site=warehouse,
            name="Main Gate",
            defaults={
                "code": "WH-GATE",
                "description": "Vehicle and visitor gate.",
                "latitude": warehouse.latitude,
                "longitude": warehouse.longitude,
                "is_active": True,
            },
        )
        lobby, _ = GuardPost.objects.update_or_create(
            site=showroom,
            name="Lobby Desk",
            defaults={
                "code": "RS-LOBBY",
                "description": "Front desk and customer entrance.",
                "latitude": showroom.latitude,
                "longitude": showroom.longitude,
                "is_active": True,
            },
        )

        shift = self._shift(main_gate, warehouse_shift_start, 8, "Demo warehouse day shift")
        assignment, _ = ShiftAssignment.objects.update_or_create(
            shift=shift,
            guard=guard,
            defaults={"status": ShiftAssignment.Status.ASSIGNED, "assigned_by": guarding},
        )
        lobby_shift = self._shift(lobby, showroom_shift_start, 8, "Demo showroom shift")
        ShiftAssignment.objects.update_or_create(
            shift=lobby_shift,
            guard=backup_guard,
            defaults={"status": ShiftAssignment.Status.ACCEPTED, "assigned_by": guarding, "accepted_at": now},
        )

        ClientPortalAccess.objects.update_or_create(
            user=guarding_client,
            site=warehouse,
            defaults={
                "role": ClientPortalAccess.Role.MANAGER,
                "can_view_reports": True,
                "can_view_patrols": True,
                "can_view_attendance": True,
                "can_view_guards": True,
                "can_acknowledge_reports": True,
            },
        )

        report, _ = FieldReport.objects.update_or_create(
            site=warehouse,
            title="Demo daily activity report",
            defaults={
                "post": main_gate,
                "assignment": assignment,
                "guard": guard,
                "report_type": FieldReport.ReportType.DAILY_ACTIVITY,
                "status": FieldReport.Status.APPROVED,
                "body": "All scheduled patrols completed. Visitor log reviewed. No incidents reported.",
                "visible_to_client": True,
                "submitted_at": now - timedelta(hours=1),
                "reviewed_by": guarding,
                "reviewed_at": now - timedelta(minutes=30),
            },
        )

        route = self._patrol_route(main_gate)
        round_, _ = PatrolRound.objects.update_or_create(
            route=route,
            assignment=assignment,
            scheduled_start=warehouse_shift_start + timedelta(hours=2),
            defaults={
                "scheduled_end": warehouse_shift_start + timedelta(hours=2, minutes=30),
                "status": PatrolRound.Status.SCHEDULED,
                "notes": "Demo scheduled patrol round.",
            },
        )
        for checkpoint in route.checkpoints.all():
            CheckpointScan.objects.get_or_create(
                patrol_round=round_,
                checkpoint=checkpoint,
                defaults={
                    "guard": guard,
                    "scanned_at": now - timedelta(minutes=15),
                    "latitude": checkpoint.latitude,
                    "longitude": checkpoint.longitude,
                    "within_geofence": True,
                },
            )

        DispatchTask.objects.update_or_create(
            title="Demo alarm response",
            site=warehouse,
            defaults={
                "assigned_guard": guard,
                "status": DispatchTask.Status.ASSIGNED,
                "priority": DispatchTask.Priority.HIGH,
                "description": "Investigate warehouse front door alarm.",
                "target_latitude": warehouse.latitude,
                "target_longitude": warehouse.longitude,
                "created_by": dispatcher,
                "assigned_at": now,
            },
        )

        self.stdout.write(self.style.SUCCESS("Rich demo data seeded successfully."))
        self.stdout.write("Demo password for all seeded users: DemoPass123!")
        self.stdout.write("Operator logins: demo-admin, demo-ops, demo-guarding, demo-dispatch, demo-billing, demo-support, demo-auditor")
        self.stdout.write("Alarm customer logins: owner, viewer")
        self.stdout.write("Guarding client portal login: guard-client")
        self.stdout.write("Guard mobile login: guard-ama")
        self.stdout.write("Client portal URL: /console/client/guarding/")
        self.stdout.write("Back office URL: /console/guarding/back-office/?tab=templates")

    def _user(self, username, email, *, first_name="", last_name="", is_staff=False, is_superuser=False, reset_password=False):
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
                "is_staff": is_staff,
                "is_superuser": is_superuser,
            },
        )
        updates = []
        for field, value in {
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "is_staff": is_staff,
            "is_superuser": is_superuser,
            "is_active": True,
        }.items():
            if getattr(user, field) != value:
                setattr(user, field, value)
                updates.append(field)
        if created or reset_password or not user.has_usable_password():
            user.set_password(self.DEMO_PASSWORD)
            updates.append("password")
        if updates:
            user.save(update_fields=sorted(set(updates)))
        return user

    def _staff(self, username, email, first_name, last_name, role, reset_password):
        user = self._user(
            username,
            email,
            first_name=first_name,
            last_name=last_name,
            is_staff=True,
            reset_password=reset_password,
        )
        self._operator_profile(user, role)
        return user

    def _customer(self, username, email, first_name, last_name, phone, reset_password):
        user = self._user(username, email, first_name=first_name, last_name=last_name, reset_password=reset_password)
        profile, _ = CustomerProfile.objects.get_or_create(user=user)
        profile.phone_number = phone
        profile.is_mobile_user = True
        profile.save(update_fields=["phone_number", "is_mobile_user", "updated_at"])
        return user

    def _operator_profile(self, user, role):
        StaffOperatorProfile.objects.update_or_create(user=user, defaults={"role": role})

    def _site(self, *, hik_site_id, name, address, city, country, latitude, longitude, operations_zone):
        site, _ = Site.objects.update_or_create(
            hik_site_id=hik_site_id,
            defaults={
                "name": name,
                "address": address,
                "city": city,
                "country": country,
                "latitude": latitude,
                "longitude": longitude,
                "operations_zone": operations_zone,
                "is_active": True,
            },
        )
        return site

    def _alarm_stack(self, site, hik_device_id, serial_number, subsystem_name):
        device, _ = AlarmPanelDevice.objects.update_or_create(
            hik_device_id=hik_device_id,
            defaults={
                "site": site,
                "name": f"{site.name} Main Panel",
                "serial_number": serial_number,
                "is_online": True,
                "work_status": AlarmPanelDevice.WORK_DISARMED,
                "battery_status": AlarmPanelDevice.BATTERY_OK,
            },
        )
        subsystem, _ = Subsystem.objects.update_or_create(
            hik_subsystem_id=f"{hik_device_id}-subsystem-1",
            defaults={
                "site": site,
                "device": device,
                "name": subsystem_name,
                "subsystem_number": 1,
                "status": Subsystem.STATUS_DISARMED,
            },
        )
        for number, name in [(1, "Front Door"), (2, "Loading Bay"), (3, "Office Motion")]:
            Zone.objects.update_or_create(
                subsystem=subsystem,
                zone_number=number,
                defaults={"name": name, "state": Zone.STATE_NORMAL},
            )
        return subsystem

    def _alarm_event(self, site, subsystem, source_event_id, event_name, severity):
        zone = subsystem.zones.order_by("zone_number").first()
        AlarmEvent.objects.update_or_create(
            source_event_id=source_event_id,
            defaults={
                "site": site,
                "subsystem": subsystem,
                "zone": zone,
                "event_type": "MobileZoneInstantAlarm",
                "event_category": AlarmEvent.CATEGORY_ALARM,
                "severity": severity,
                "payload": {"event_name": event_name, "source": "demo"},
                "occurred_at": timezone.now() - timedelta(hours=2),
            },
        )

    def _guard(self, user, employee_number, first_name, last_name, phone):
        guard, _ = GuardProfile.objects.update_or_create(
            employee_number=employee_number,
            defaults={
                "user": user,
                "first_name": first_name,
                "last_name": last_name,
                "phone_number": phone,
                "email": user.email,
                "status": GuardProfile.Status.ACTIVE,
                "hire_date": timezone.localdate() - timedelta(days=120),
            },
        )
        return guard

    def _credential(self, guard, name, authority, reference):
        GuardCredential.objects.update_or_create(
            guard=guard,
            name=name,
            defaults={
                "credential_type": GuardCredential.CredentialType.LICENSE,
                "issuing_authority": authority,
                "reference_number": reference,
                "issued_on": timezone.localdate() - timedelta(days=180),
                "expires_on": timezone.localdate() + timedelta(days=365),
                "verified": True,
            },
        )

    def _shift(self, post, starts_at, hours, notes):
        shift, _ = Shift.objects.update_or_create(
            post=post,
            starts_at=starts_at.replace(second=0, microsecond=0),
            defaults={
                "ends_at": starts_at.replace(second=0, microsecond=0) + timedelta(hours=hours),
                "status": Shift.Status.PUBLISHED,
                "required_guards": 1,
                "notes": notes,
            },
        )
        return shift

    def _demo_datetime(self, today, *, days, hour, minute=0):
        naive = datetime.combine(today + timedelta(days=days), time(hour, minute))
        return timezone.make_aware(naive, timezone.get_current_timezone())

    def _patrol_route(self, post):
        checkpoint_specs = [
            ("Gate Checkpoint", "DEMO-GATE-QR", post.latitude, post.longitude, 1),
            ("Loading Bay Checkpoint", "DEMO-LOADING-QR", post.latitude, post.longitude, 2),
        ]
        route, _ = PatrolRoute.objects.update_or_create(
            post=post,
            name="Demo perimeter route",
            defaults={"description": "Short route for demo patrol proof.", "expected_duration_minutes": 30, "is_active": True},
        )
        for name, code, lat, lon, sequence in checkpoint_specs:
            checkpoint, _ = Checkpoint.objects.update_or_create(
                code=code,
                defaults={
                    "post": post,
                    "name": name,
                    "checkpoint_type": Checkpoint.CheckpointType.QR,
                    "latitude": lat,
                    "longitude": lon,
                    "instructions": "Scan and visually inspect the area.",
                    "is_active": True,
                },
            )
            PatrolRouteCheckpoint.objects.update_or_create(
                route=route,
                checkpoint=checkpoint,
                defaults={"sequence": sequence},
            )
        return route
