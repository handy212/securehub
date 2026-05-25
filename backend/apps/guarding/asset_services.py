"""Business logic for guard asset catalog, stock, and shift custody manifests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

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
from .models import GuardingEventLog, ShiftAssignment
from .services import create_workflow_event


@dataclass
class AssetReadinessResult:
    ok: bool
    mode: str
    blockers: list[str]
    advisory_warnings: list[str]


def resolve_asset_policy_for_assignment(assignment: ShiftAssignment) -> GuardingAssetPolicy | None:
    post = assignment.shift.post
    post_policy = (
        GuardingAssetPolicy.objects.filter(post=post, is_active=True).first()
        if post
        else None
    )
    if post_policy:
        return post_policy
    site = post.site if post else None
    if site:
        return GuardingAssetPolicy.objects.filter(site=site, is_active=True).first()
    return None


def resolve_enforcement_mode(assignment: ShiftAssignment) -> str:
    policy = resolve_asset_policy_for_assignment(assignment)
    if policy:
        return policy.default_mode
    return GuardingAssetPolicy.EnforcementMode.ADVISORY


def get_default_kit_for_post(post) -> PostAssetKit | None:
    kit = (
        PostAssetKit.objects.filter(post=post, is_active=True, is_default=True)
        .prefetch_related("lines__asset_type")
        .first()
    )
    if kit:
        return kit
    return (
        PostAssetKit.objects.filter(post=post, is_active=True)
        .prefetch_related("lines__asset_type")
        .order_by("name")
        .first()
    )


@transaction.atomic
def build_manifest_for_assignment(
    assignment: ShiftAssignment,
    *,
    depot: GuardAssetDepot | None = None,
    issued_by=None,
) -> ShiftAssetManifest:
    manifest, created = ShiftAssetManifest.objects.get_or_create(
        assignment=assignment,
        defaults={
            "enforcement_mode": resolve_enforcement_mode(assignment),
            "depot": depot,
            "issued_by": issued_by,
        },
    )
    if not created:
        return manifest

    kit = get_default_kit_for_post(assignment.shift.post)
    if kit:
        _populate_manifest_lines_from_kit(manifest, kit)
    return manifest


def _populate_manifest_lines_from_kit(manifest: ShiftAssetManifest, kit: PostAssetKit) -> None:
    for kit_line in kit.lines.select_related("asset_type"):
        if kit_line.is_optional:
            continue
        ShiftAssetManifestLine.objects.create(
            manifest=manifest,
            asset_type=kit_line.asset_type,
            expected_qty=kit_line.quantity_required,
            status=ShiftAssetManifestLine.Status.PENDING,
        )


@transaction.atomic
def rebuild_manifest_for_assignment(
    assignment: ShiftAssignment,
    *,
    depot: GuardAssetDepot | None = None,
    issued_by=None,
) -> ShiftAssetManifest:
    manifest = ShiftAssetManifest.objects.select_for_update().get(assignment=assignment)
    if manifest.status != ShiftAssetManifest.Status.DRAFT:
        raise ValidationError({"manifest": "Only draft manifests can be rebuilt from kit."})
    if manifest.lines.exclude(status=ShiftAssetManifestLine.Status.PENDING).exists():
        raise ValidationError({"manifest": "Cannot rebuild a manifest with issued or returned lines."})
    manifest.lines.all().delete()
    if depot:
        manifest.depot = depot
        manifest.save(update_fields=["depot", "updated_at"])
    kit = get_default_kit_for_post(assignment.shift.post)
    if kit:
        _populate_manifest_lines_from_kit(manifest, kit)
    return manifest


@transaction.atomic
def add_manifest_line(
    manifest: ShiftAssetManifest,
    *,
    asset_type: GuardAssetType,
    expected_qty: int = 1,
    notes: str = "",
) -> ShiftAssetManifestLine:
    manifest = ShiftAssetManifest.objects.select_for_update().get(pk=manifest.pk)
    if manifest.status != ShiftAssetManifest.Status.DRAFT:
        raise ValidationError({"manifest": "Lines can only be added to draft manifests."})
    if manifest.lines.filter(asset_type=asset_type).exists():
        raise ValidationError({"asset_type": "This asset type is already on the manifest."})
    return ShiftAssetManifestLine.objects.create(
        manifest=manifest,
        asset_type=asset_type,
        expected_qty=max(1, int(expected_qty)),
        notes=notes or "",
        status=ShiftAssetManifestLine.Status.PENDING,
    )


@transaction.atomic
def update_manifest_line(
    line: ShiftAssetManifestLine,
    *,
    expected_qty: int | None = None,
    notes: str | None = None,
) -> ShiftAssetManifestLine:
    line = ShiftAssetManifestLine.objects.select_for_update().get(pk=line.pk)
    if line.status != ShiftAssetManifestLine.Status.PENDING:
        raise ValidationError({"status": "Only pending lines can be edited."})
    if expected_qty is not None:
        line.expected_qty = max(1, int(expected_qty))
    if notes is not None:
        line.notes = notes
    line.save(update_fields=["expected_qty", "notes", "updated_at"])
    return line


@transaction.atomic
def delete_manifest_line(line: ShiftAssetManifestLine) -> None:
    line = ShiftAssetManifestLine.objects.select_for_update().get(pk=line.pk)
    if line.status != ShiftAssetManifestLine.Status.PENDING:
        raise ValidationError({"status": "Only pending lines can be removed."})
    line.delete()


def _get_or_create_stock(asset_type: GuardAssetType, depot: GuardAssetDepot) -> GuardAssetStock:
    if asset_type.tracking_mode != GuardAssetType.TrackingMode.QUANTITY:
        raise ValidationError({"asset_type": "Stock records apply only to quantity-tracked types."})
    stock, _ = GuardAssetStock.objects.select_for_update().get_or_create(
        asset_type=asset_type,
        depot=depot,
        defaults={"quantity_on_hand": 0, "quantity_reserved": 0},
    )
    return stock


@transaction.atomic
def issue_manifest_line(
    line: ShiftAssetManifestLine,
    *,
    asset_unit: GuardAssetUnit | None = None,
    quantity: int = 1,
    condition_out: str = "",
    issued_by=None,
    depot: GuardAssetDepot | None = None,
) -> ShiftAssetManifestLine:
    manifest = ShiftAssetManifest.objects.select_for_update().get(pk=line.manifest_id)
    line = ShiftAssetManifestLine.objects.select_for_update().get(pk=line.pk)
    asset_type = line.asset_type
    effective_depot = depot or manifest.depot

    if line.status not in {ShiftAssetManifestLine.Status.PENDING, ShiftAssetManifestLine.Status.ISSUED}:
        raise ValidationError({"status": "Line cannot be issued in its current state."})

    if asset_type.tracking_mode == GuardAssetType.TrackingMode.SERIAL:
        if asset_unit is None:
            raise ValidationError({"asset_unit": "Serial-tracked items require a specific unit."})
        if asset_unit.asset_type_id != asset_type.id:
            raise ValidationError({"asset_unit": "Unit does not match asset type."})
        if asset_unit.status != GuardAssetUnit.Status.AVAILABLE:
            raise ValidationError({"asset_unit": "Unit is not available for issue."})
        if effective_depot and asset_unit.depot_id != effective_depot.id:
            raise ValidationError({"asset_unit": "Unit is not at the selected depot."})
        asset_unit.status = GuardAssetUnit.Status.ISSUED
        asset_unit.save(update_fields=["status", "updated_at"])
        line.asset_unit = asset_unit
        line.issued_qty = 1
    else:
        if not effective_depot:
            raise ValidationError({"depot": "Depot is required for quantity-tracked items."})
        stock = _get_or_create_stock(asset_type, effective_depot)
        qty = max(1, int(quantity))
        if stock.quantity_available < qty:
            raise ValidationError({"quantity": f"Insufficient stock (available: {stock.quantity_available})."})
        stock.quantity_on_hand -= qty
        stock.save(update_fields=["quantity_on_hand", "updated_at"])
        line.issued_qty = line.issued_qty + qty

    line.status = ShiftAssetManifestLine.Status.ISSUED
    line.condition_out = condition_out or line.condition_out
    line.issued_at = timezone.now()
    line.save(
        update_fields=[
            "asset_unit",
            "issued_qty",
            "status",
            "condition_out",
            "issued_at",
            "updated_at",
        ]
    )

    if manifest.status == ShiftAssetManifest.Status.DRAFT:
        manifest.status = ShiftAssetManifest.Status.ISSUED
        manifest.issued_at = manifest.issued_at or timezone.now()
        manifest.issued_by = issued_by or manifest.issued_by
        manifest.depot = effective_depot or manifest.depot
        manifest.save(update_fields=["status", "issued_at", "issued_by", "depot", "updated_at"])

    create_workflow_event(
        event_type="asset_line_issued",
        title="Asset issued",
        message=f"{asset_type.name} issued for {manifest.assignment.guard.full_name}.",
        obj=line,
        guard=manifest.assignment.guard,
        site=manifest.assignment.shift.post.site,
        actor=issued_by,
    )
    return line


@transaction.atomic
def return_manifest_line(
    line: ShiftAssetManifestLine,
    *,
    quantity: int | None = None,
    condition_in: str = "",
    status: str | None = None,
    returned_by=None,
    notes: str = "",
) -> ShiftAssetManifestLine:
    manifest = ShiftAssetManifest.objects.select_for_update().get(pk=line.manifest_id)
    line = ShiftAssetManifestLine.objects.select_for_update().get(pk=line.pk)
    asset_type = line.asset_type

    if line.status not in {
        ShiftAssetManifestLine.Status.ISSUED,
        ShiftAssetManifestLine.Status.DAMAGED,
        ShiftAssetManifestLine.Status.LOST,
    }:
        raise ValidationError({"status": "Only issued lines can be returned or closed out."})

    return_status = status or ShiftAssetManifestLine.Status.RETURNED
    if return_status not in {
        ShiftAssetManifestLine.Status.RETURNED,
        ShiftAssetManifestLine.Status.LOST,
        ShiftAssetManifestLine.Status.DAMAGED,
    }:
        raise ValidationError({"status": "Invalid return status."})

    if asset_type.tracking_mode == GuardAssetType.TrackingMode.SERIAL:
        unit = line.asset_unit
        if unit:
            if return_status == ShiftAssetManifestLine.Status.RETURNED:
                unit.status = GuardAssetUnit.Status.AVAILABLE
            elif return_status == ShiftAssetManifestLine.Status.LOST:
                unit.status = GuardAssetUnit.Status.LOST
            else:
                unit.status = GuardAssetUnit.Status.MAINTENANCE
            unit.save(update_fields=["status", "updated_at"])
        line.returned_qty = line.issued_qty
    else:
        qty = quantity if quantity is not None else max(0, line.issued_qty - line.returned_qty)
        if qty <= 0:
            raise ValidationError({"quantity": "Return quantity must be positive."})
        if manifest.depot_id and return_status == ShiftAssetManifestLine.Status.RETURNED:
            stock = _get_or_create_stock(asset_type, manifest.depot)
            stock.quantity_on_hand += qty
            stock.save(update_fields=["quantity_on_hand", "updated_at"])
        line.returned_qty = min(line.issued_qty, line.returned_qty + qty)

    line.status = return_status
    line.condition_in = condition_in or line.condition_in
    line.returned_at = timezone.now()
    if notes:
        line.notes = notes
    line.save(
        update_fields=[
            "returned_qty",
            "status",
            "condition_in",
            "returned_at",
            "notes",
            "updated_at",
        ]
    )
    _refresh_manifest_status(manifest, closed_by=returned_by)
    billing_metadata = {}
    if return_status in {ShiftAssetManifestLine.Status.LOST, ShiftAssetManifestLine.Status.DAMAGED}:
        if asset_type.replacement_cost is not None:
            billing_metadata["replacement_cost"] = str(asset_type.replacement_cost)
            billing_metadata["billing_reason"] = return_status
    create_workflow_event(
        event_type="asset_line_returned",
        title=f"Asset {return_status}",
        message=f"{asset_type.name} marked {return_status} for {manifest.assignment.guard.full_name}.",
        obj=line,
        guard=manifest.assignment.guard,
        site=manifest.assignment.shift.post.site,
        actor=returned_by,
        severity=(
            GuardingEventLog.Severity.WARNING
            if return_status in {ShiftAssetManifestLine.Status.LOST, ShiftAssetManifestLine.Status.DAMAGED}
            else GuardingEventLog.Severity.INFO
        ),
        metadata=billing_metadata or None,
    )
    return line


def _refresh_manifest_status(manifest: ShiftAssetManifest, *, closed_by=None) -> None:
    lines = list(manifest.lines.all())
    if not lines:
        return
    open_lines = [
        ln
        for ln in lines
        if ln.status in {ShiftAssetManifestLine.Status.PENDING, ShiftAssetManifestLine.Status.ISSUED}
    ]
    unsettled = [
        ln
        for ln in lines
        if ln.status == ShiftAssetManifestLine.Status.ISSUED
        and ln.returned_qty < ln.issued_qty
        and ln.asset_type.requires_return
    ]
    if not open_lines and not unsettled:
        manifest.status = ShiftAssetManifest.Status.CLOSED
        manifest.closed_at = timezone.now()
        manifest.closed_by = closed_by or manifest.closed_by
    elif any(ln.status == ShiftAssetManifestLine.Status.ISSUED for ln in lines):
        manifest.status = ShiftAssetManifest.Status.PARTIAL_RETURN
    manifest.save(update_fields=["status", "closed_at", "closed_by", "updated_at"])


@transaction.atomic
def close_manifest(manifest: ShiftAssetManifest, *, closed_by=None) -> ShiftAssetManifest:
    manifest = ShiftAssetManifest.objects.select_for_update().get(pk=manifest.pk)
    pending = manifest.lines.filter(status=ShiftAssetManifestLine.Status.PENDING)
    if pending.exists():
        raise ValidationError({"manifest": "Cannot close manifest with pending lines."})
    manifest.status = ShiftAssetManifest.Status.CLOSED
    manifest.closed_at = timezone.now()
    manifest.closed_by = closed_by
    manifest.save(update_fields=["status", "closed_at", "closed_by", "updated_at"])
    return manifest


def guard_confirms_manifest(manifest: ShiftAssetManifest) -> ShiftAssetManifest:
    manifest.guard_confirmed_at = timezone.now()
    manifest.save(update_fields=["guard_confirmed_at", "updated_at"])
    return manifest


@transaction.atomic
def override_asset_enforcement(
    manifest: ShiftAssetManifest,
    *,
    phase: str,
    reason: str,
    actor,
) -> ShiftAssetManifest:
    policy = resolve_asset_policy_for_assignment(manifest.assignment)
    if policy and not policy.allow_supervisor_override:
        raise ValidationError({"override": "Supervisor override is not allowed for this site/post."})
    if phase == "clock_in":
        manifest.override_clock_in = True
    elif phase == "clock_out":
        manifest.override_clock_out = True
    else:
        raise ValidationError({"phase": "phase must be clock_in or clock_out."})
    manifest.override_by = actor
    manifest.override_at = timezone.now()
    manifest.override_reason = reason
    manifest.save(
        update_fields=[
            "override_clock_in",
            "override_clock_out",
            "override_by",
            "override_at",
            "override_reason",
            "updated_at",
        ]
    )
    create_workflow_event(
        event_type="asset_enforcement_override",
        title="Asset enforcement overridden",
        message=reason,
        obj=manifest,
        guard=manifest.assignment.guard,
        site=manifest.assignment.shift.post.site,
        actor=actor,
        severity=GuardingEventLog.Severity.WARNING,
        metadata={"phase": phase},
    )
    return manifest


def asset_readiness_for_assignment(
    assignment: ShiftAssignment,
    *,
    phase: str,
) -> AssetReadinessResult:
    """phase: clock_in | clock_out"""
    mode = resolve_enforcement_mode(assignment)
    blockers: list[str] = []
    warnings: list[str] = []

    try:
        manifest = assignment.asset_manifest
    except ShiftAssetManifest.DoesNotExist:
        kit = get_default_kit_for_post(assignment.shift.post)
        if kit and kit.lines.filter(is_optional=False).exists():
            msg = "No asset manifest created for this shift."
            if mode == GuardingAssetPolicy.EnforcementMode.STRICT:
                blockers.append(msg)
            else:
                warnings.append(msg)
        return AssetReadinessResult(
            ok=not blockers,
            mode=mode,
            blockers=blockers,
            advisory_warnings=warnings,
        )

    policy = resolve_asset_policy_for_assignment(assignment)

    if phase == "clock_in":
        if manifest.override_clock_in:
            return AssetReadinessResult(ok=True, mode=mode, blockers=[], advisory_warnings=warnings)
        if manifest.status not in {ShiftAssetManifest.Status.ISSUED, ShiftAssetManifest.Status.PARTIAL_RETURN, ShiftAssetManifest.Status.CLOSED}:
            msg = "Assets must be issued before clock-in."
            if mode == GuardingAssetPolicy.EnforcementMode.STRICT and (
                not policy or policy.enforce_issue_before_clock_in
            ):
                blockers.append(msg)
            else:
                warnings.append(msg)
        pending = manifest.lines.filter(status=ShiftAssetManifestLine.Status.PENDING, asset_type__requires_return=True)
        if pending.exists():
            msg = f"{pending.count()} required asset line(s) still pending issue."
            if mode == GuardingAssetPolicy.EnforcementMode.STRICT:
                blockers.append(msg)
            else:
                warnings.append(msg)
    elif phase == "clock_out":
        if manifest.override_clock_out:
            return AssetReadinessResult(ok=True, mode=mode, blockers=[], advisory_warnings=warnings)
        open_lines = manifest.lines.filter(
            status=ShiftAssetManifestLine.Status.ISSUED,
            asset_type__requires_return=True,
        )
        if open_lines.exists():
            msg = f"{open_lines.count()} asset(s) still out — return before clock-out."
            if mode == GuardingAssetPolicy.EnforcementMode.STRICT and (
                not policy or policy.enforce_return_before_clock_out
            ):
                blockers.append(msg)
            else:
                warnings.append(msg)
        if manifest.status not in {ShiftAssetManifest.Status.CLOSED, ShiftAssetManifest.Status.PARTIAL_RETURN}:
            if manifest.lines.filter(status=ShiftAssetManifestLine.Status.ISSUED).exists():
                warnings.append("Asset manifest is not fully closed.")

    return AssetReadinessResult(
        ok=not blockers,
        mode=mode,
        blockers=blockers,
        advisory_warnings=warnings,
    )


def sync_offboarding_equipment_flag(guard) -> None:
    from .models import GuardEquipmentIssue, GuardOffboardingChecklist

    open_hr = GuardEquipmentIssue.objects.filter(
        guard=guard,
        status=GuardEquipmentIssue.Status.ISSUED,
    ).exists()
    open_manifests = ShiftAssetManifest.objects.filter(
        assignment__guard=guard,
        status__in=[
            ShiftAssetManifest.Status.DRAFT,
            ShiftAssetManifest.Status.ISSUED,
            ShiftAssetManifest.Status.PARTIAL_RETURN,
        ],
    ).exists()
    if open_hr or open_manifests:
        return
    checklist, _ = GuardOffboardingChecklist.objects.get_or_create(guard=guard)
    if not checklist.equipment_returned:
        checklist.equipment_returned = True
        checklist.save(update_fields=["equipment_returned", "updated_at"])


def asset_analytics_summary() -> dict[str, Any]:
    from datetime import timedelta

    now = timezone.now()
    week_ago = now - timedelta(days=7)
    return {
        "open_manifests": ShiftAssetManifest.objects.filter(
            status__in=[
                ShiftAssetManifest.Status.DRAFT,
                ShiftAssetManifest.Status.ISSUED,
                ShiftAssetManifest.Status.PARTIAL_RETURN,
            ]
        ).count(),
        "units_out": GuardAssetUnit.objects.filter(status=GuardAssetUnit.Status.ISSUED).count(),
        "lost_this_week": ShiftAssetManifestLine.objects.filter(
            status=ShiftAssetManifestLine.Status.LOST,
            returned_at__gte=week_ago,
        ).count(),
        "overdue_returns": ShiftAssetManifest.objects.filter(
            status__in=[ShiftAssetManifest.Status.ISSUED, ShiftAssetManifest.Status.PARTIAL_RETURN],
            assignment__clocked_out_at__isnull=False,
            assignment__clocked_out_at__lt=now - timedelta(hours=2),
        ).count(),
    }
