"""Dashboard console views for guard asset management."""

import json

from django.contrib import messages
from django.db.models import Prefetch, ProtectedError
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.urls import reverse
from django.views.generic import TemplateView

from apps.guarding.asset_models import (
    GuardAssetDepot,
    GuardAssetMaintenanceLog,
    GuardAssetStock,
    GuardAssetType,
    GuardAssetUnit,
    GuardingAssetPolicy,
    PostAssetKit,
    PostAssetKitLine,
    ShiftAssetManifest,
    ShiftAssetManifestLine,
)
from apps.guarding.asset_services import (
    add_manifest_line,
    asset_analytics_summary,
    build_manifest_for_assignment,
    close_manifest,
    delete_manifest_line,
    issue_manifest_line,
    override_asset_enforcement,
    rebuild_manifest_for_assignment,
    return_manifest_line,
    sync_offboarding_equipment_flag,
    update_manifest_line,
)
from apps.guarding.models import GuardPost, ShiftAssignment
from apps.sites.models import Site

from .mixins import GuardingOverviewMixin
from .parsers import parse_decimal_field, parse_int_field
from .permissions import StaffRequiredMixin

MANIFEST_ACTIONS = frozenset(
    {
        "build_manifest",
        "rebuild_manifest",
        "issue_manifest_line",
        "return_manifest_line",
        "close_manifest",
        "override_asset_enforcement",
        "delete_draft_manifest",
        "add_manifest_line",
        "update_manifest_line",
        "delete_manifest_line",
    }
)


def _parse_metadata_field(raw: str) -> dict:
    raw = (raw or "").strip()
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Metadata must be valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("Metadata must be a JSON object.")
    return data


def _apply_asset_type_form(asset_type, request) -> None:
    asset_type.default_condition_check = bool(request.POST.get("default_condition_check"))
    asset_type.metadata = _parse_metadata_field(request.POST.get("metadata", ""))


def _apply_policy_scope(policy, request) -> None:
    site_id = request.POST.get("site_id", "").strip()
    post_id = request.POST.get("post_id", "").strip()
    if site_id and post_id:
        raise ValueError("Policy must be for a site OR a post, not both.")
    if not site_id and not post_id:
        raise ValueError("Select a site or a post for the policy.")
    if post_id:
        conflict = GuardingAssetPolicy.objects.filter(post_id=post_id).exclude(pk=policy.pk).first()
        if conflict:
            raise ValueError("A policy already exists for this post.")
        policy.site = None
        policy.post_id = post_id
    else:
        conflict = GuardingAssetPolicy.objects.filter(site_id=site_id).exclude(pk=policy.pk).first()
        if conflict:
            raise ValueError("A policy already exists for this site.")
        policy.post = None
        policy.site_id = site_id


def _clear_default_kit(post, *, exclude_kit_id=None):
    qs = PostAssetKit.objects.filter(post=post, is_default=True)
    if exclude_kit_id:
        qs = qs.exclude(pk=exclude_kit_id)
    qs.update(is_default=False)


class GuardingAssetsView(StaffRequiredMixin, GuardingOverviewMixin, TemplateView):
    template_name = "dashboard/guarding/assets.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["asset_types"] = GuardAssetType.objects.order_by("name")
        context["depots"] = GuardAssetDepot.objects.select_related("site").order_by("name")
        context["units"] = (
            GuardAssetUnit.objects.select_related("asset_type", "depot", "site")
            .prefetch_related(
                Prefetch(
                    "maintenance_logs",
                    queryset=GuardAssetMaintenanceLog.objects.select_related("performed_by").order_by(
                        "-started_at"
                    ),
                )
            )
            .order_by("asset_tag")[:300]
        )
        context["stock_levels"] = GuardAssetStock.objects.select_related("asset_type", "depot").order_by("depot__name")[:300]
        context["sites"] = Site.objects.order_by("name")
        context["posts"] = GuardPost.objects.filter(is_active=True).select_related("site").order_by("site__name", "name")
        context["kits"] = PostAssetKit.objects.select_related("post", "post__site").prefetch_related("lines__asset_type")[:100]
        context["open_manifests"] = (
            ShiftAssetManifest.objects.select_related(
                "assignment__guard",
                "assignment__shift__post",
                "assignment__shift__post__site",
                "depot",
            )
            .prefetch_related("lines__asset_type", "lines__asset_unit")
            .filter(
                status__in=[
                    ShiftAssetManifest.Status.DRAFT,
                    ShiftAssetManifest.Status.ISSUED,
                    ShiftAssetManifest.Status.PARTIAL_RETURN,
                ]
            )
            .order_by("-created_at")[:50]
        )
        context["asset_depots"] = GuardAssetDepot.objects.filter(is_active=True).order_by("name")
        context["available_units"] = GuardAssetUnit.objects.filter(
            status=GuardAssetUnit.Status.AVAILABLE,
        ).select_related("asset_type", "depot")[:500]
        context["assignments"] = (
            ShiftAssignment.objects.select_related("shift", "shift__post", "shift__post__site", "guard")
            .order_by("-shift__starts_at")[:200]
        )
        context["asset_categories"] = GuardAssetType.Category.choices
        context["tracking_modes"] = GuardAssetType.TrackingMode.choices
        context["unit_statuses"] = GuardAssetUnit.Status.choices
        context["enforcement_modes"] = GuardingAssetPolicy.EnforcementMode.choices
        context["asset_policies"] = GuardingAssetPolicy.objects.select_related("site", "post", "post__site").order_by(
            "site__name", "post__name"
        )
        context["asset_summary"] = asset_analytics_summary()
        context["counts"] = self.get_guarding_counts()
        return context

    def post(self, request):
        action = request.POST.get("action", "")
        redirect_url = reverse("dashboard:guarding-assets")
        if action in MANIFEST_ACTIONS:
            try:
                if handle_shifts_asset_action(request):
                    return redirect(f"{redirect_url}?tab=manifests")
            except ProtectedError:
                messages.error(request, "Cannot delete: this record is still referenced by other data.")
            except Exception as exc:
                messages.error(request, str(exc))
            return redirect(f"{redirect_url}?tab=manifests")

        try:
            if action == "asset_type":
                asset_type = GuardAssetType(
                    name=request.POST.get("name", "").strip(),
                    code=request.POST.get("code", "").strip(),
                    category=request.POST.get("category") or GuardAssetType.Category.OTHER,
                    tracking_mode=request.POST.get("tracking_mode") or GuardAssetType.TrackingMode.SERIAL,
                    requires_return=not bool(request.POST.get("no_return")),
                    is_active=not bool(request.POST.get("inactive")),
                    replacement_cost=(
                        parse_decimal_field(request.POST.get("replacement_cost"), label="Replacement cost")
                        if request.POST.get("replacement_cost")
                        else None
                    ),
                )
                _apply_asset_type_form(asset_type, request)
                asset_type.save()
                messages.success(request, "Asset type created.")
            elif action == "update_asset_type":
                asset_type = get_object_or_404(GuardAssetType, pk=request.POST.get("asset_type_id"))
                asset_type.name = request.POST.get("name", "").strip()
                asset_type.code = request.POST.get("code", "").strip()
                asset_type.category = request.POST.get("category") or asset_type.category
                asset_type.tracking_mode = request.POST.get("tracking_mode") or asset_type.tracking_mode
                asset_type.requires_return = not bool(request.POST.get("no_return"))
                asset_type.is_active = not bool(request.POST.get("inactive"))
                asset_type.replacement_cost = (
                    parse_decimal_field(request.POST.get("replacement_cost"), label="Replacement cost")
                    if request.POST.get("replacement_cost")
                    else None
                )
                _apply_asset_type_form(asset_type, request)
                asset_type.save()
                messages.success(request, "Asset type updated.")
            elif action == "delete_asset_type":
                asset_type = get_object_or_404(GuardAssetType, pk=request.POST.get("asset_type_id"))
                if asset_type.units.exists():
                    raise ValueError("Cannot delete a type that has registered units. Deactivate it instead.")
                if asset_type.kit_lines.exists() or asset_type.manifest_lines.exists():
                    raise ValueError("Cannot delete a type used in kits or shift manifests. Deactivate it instead.")
                asset_type.delete()
                messages.success(request, "Asset type deleted.")
            elif action == "depot":
                site = Site.objects.filter(pk=request.POST.get("site_id")).first()
                GuardAssetDepot.objects.create(
                    name=request.POST.get("name", "").strip(),
                    site=site,
                    is_active=not bool(request.POST.get("inactive")),
                )
                messages.success(request, "Depot created.")
            elif action == "update_depot":
                depot = get_object_or_404(GuardAssetDepot, pk=request.POST.get("depot_id"))
                depot.name = request.POST.get("name", "").strip()
                depot.site = Site.objects.filter(pk=request.POST.get("site_id")).first()
                depot.is_active = not bool(request.POST.get("inactive"))
                depot.save()
                messages.success(request, "Depot updated.")
            elif action == "delete_depot":
                depot = get_object_or_404(GuardAssetDepot, pk=request.POST.get("depot_id"))
                if depot.units.exists() or depot.stock_levels.exists():
                    raise ValueError("Cannot delete a depot that still has units or stock. Deactivate it instead.")
                depot.delete()
                messages.success(request, "Depot deleted.")
            elif action == "asset_unit":
                asset_type = get_object_or_404(GuardAssetType, pk=request.POST.get("asset_type_id"))
                depot = get_object_or_404(GuardAssetDepot, pk=request.POST.get("depot_id"))
                GuardAssetUnit.objects.create(
                    asset_type=asset_type,
                    depot=depot,
                    site=Site.objects.filter(pk=request.POST.get("site_id")).first(),
                    asset_tag=request.POST.get("asset_tag", "").strip(),
                    serial_number=request.POST.get("serial_number", "").strip(),
                    status=request.POST.get("status") or GuardAssetUnit.Status.AVAILABLE,
                    notes=request.POST.get("notes", "").strip(),
                )
                messages.success(request, "Asset unit registered.")
            elif action == "update_asset_unit":
                unit = get_object_or_404(GuardAssetUnit, pk=request.POST.get("unit_id"))
                unit.asset_type = get_object_or_404(GuardAssetType, pk=request.POST.get("asset_type_id"))
                unit.depot = get_object_or_404(GuardAssetDepot, pk=request.POST.get("depot_id"))
                unit.site = Site.objects.filter(pk=request.POST.get("site_id")).first()
                unit.asset_tag = request.POST.get("asset_tag", "").strip()
                unit.serial_number = request.POST.get("serial_number", "").strip()
                unit.status = request.POST.get("status") or unit.status
                unit.notes = request.POST.get("notes", "").strip()
                unit.save()
                messages.success(request, "Asset unit updated.")
            elif action == "delete_asset_unit":
                unit = get_object_or_404(GuardAssetUnit, pk=request.POST.get("unit_id"))
                if unit.status == GuardAssetUnit.Status.ISSUED:
                    raise ValueError("Cannot delete a unit that is currently issued.")
                if unit.manifest_lines.filter(status__in=["issued", "pending"]).exists():
                    raise ValueError("Cannot delete a unit referenced on an open manifest line.")
                unit.delete()
                messages.success(request, "Asset unit deleted.")
            elif action == "maintenance_log":
                unit = get_object_or_404(GuardAssetUnit, pk=request.POST.get("unit_id"))
                status_after = request.POST.get("status_after", "").strip() or GuardAssetUnit.Status.MAINTENANCE
                completed = bool(request.POST.get("completed"))
                log = GuardAssetMaintenanceLog.objects.create(
                    unit=unit,
                    status_before=unit.status,
                    status_after=status_after,
                    notes=request.POST.get("notes", "").strip(),
                    performed_by=request.user,
                    completed_at=timezone.now() if completed else None,
                )
                if completed:
                    unit.status = GuardAssetUnit.Status.AVAILABLE
                elif status_after:
                    unit.status = status_after
                unit.save(update_fields=["status", "updated_at"])
                messages.success(request, "Maintenance log recorded.")
            elif action == "update_maintenance_log":
                log = get_object_or_404(GuardAssetMaintenanceLog, pk=request.POST.get("log_id"))
                unit = log.unit
                log.notes = request.POST.get("notes", "").strip()
                log.status_after = request.POST.get("status_after", "").strip() or log.status_after
                completed = bool(request.POST.get("completed"))
                log.completed_at = timezone.now() if completed else None
                log.save()
                if completed:
                    unit.status = GuardAssetUnit.Status.AVAILABLE
                else:
                    unit.status = log.status_after or unit.status
                unit.save(update_fields=["status", "updated_at"])
                messages.success(request, "Maintenance log updated.")
            elif action == "delete_maintenance_log":
                get_object_or_404(GuardAssetMaintenanceLog, pk=request.POST.get("log_id")).delete()
                messages.success(request, "Maintenance log deleted.")
            elif action == "stock_adjust":
                asset_type = get_object_or_404(GuardAssetType, pk=request.POST.get("asset_type_id"))
                depot = get_object_or_404(GuardAssetDepot, pk=request.POST.get("depot_id"))
                stock, _ = GuardAssetStock.objects.get_or_create(asset_type=asset_type, depot=depot)
                stock.quantity_on_hand = parse_int_field(
                    request.POST.get("quantity_on_hand") or 0,
                    label="Quantity on hand",
                    min_value=0,
                )
                stock.save()
                messages.success(request, "Stock level updated.")
            elif action == "update_stock":
                stock = get_object_or_404(GuardAssetStock, pk=request.POST.get("stock_id"))
                stock.quantity_on_hand = parse_int_field(
                    request.POST.get("quantity_on_hand") or 0,
                    label="Quantity on hand",
                    min_value=0,
                )
                stock.quantity_reserved = parse_int_field(
                    request.POST.get("quantity_reserved") or 0,
                    label="Quantity reserved",
                    min_value=0,
                )
                if stock.quantity_reserved > stock.quantity_on_hand:
                    raise ValueError("Reserved quantity cannot exceed quantity on hand.")
                stock.save()
                messages.success(request, "Stock level updated.")
            elif action == "delete_stock":
                get_object_or_404(GuardAssetStock, pk=request.POST.get("stock_id")).delete()
                messages.success(request, "Stock record deleted.")
            elif action == "post_kit":
                post = get_object_or_404(GuardPost, pk=request.POST.get("post_id"))
                kit = PostAssetKit.objects.create(
                    post=post,
                    name=request.POST.get("name", "").strip() or "Default kit",
                    is_default=bool(request.POST.get("is_default")),
                    is_active=not bool(request.POST.get("inactive")),
                )
                if kit.is_default:
                    _clear_default_kit(post, exclude_kit_id=kit.pk)
                messages.success(request, "Post kit created.")
            elif action == "update_post_kit":
                kit = get_object_or_404(PostAssetKit, pk=request.POST.get("kit_id"))
                kit.post = get_object_or_404(GuardPost, pk=request.POST.get("post_id"))
                kit.name = request.POST.get("name", "").strip() or kit.name
                kit.is_default = bool(request.POST.get("is_default"))
                kit.is_active = not bool(request.POST.get("inactive"))
                kit.save()
                if kit.is_default:
                    _clear_default_kit(kit.post, exclude_kit_id=kit.pk)
                messages.success(request, "Post kit updated.")
            elif action == "delete_post_kit":
                kit = get_object_or_404(PostAssetKit, pk=request.POST.get("kit_id"))
                kit.delete()
                messages.success(request, "Post kit deleted.")
            elif action == "kit_line":
                kit = get_object_or_404(PostAssetKit, pk=request.POST.get("kit_id"))
                PostAssetKitLine.objects.update_or_create(
                    kit=kit,
                    asset_type=get_object_or_404(GuardAssetType, pk=request.POST.get("asset_type_id")),
                    defaults={
                        "quantity_required": parse_int_field(
                            request.POST.get("quantity_required") or 1,
                            label="Quantity",
                            min_value=1,
                        ),
                        "is_optional": bool(request.POST.get("is_optional")),
                    },
                )
                messages.success(request, "Kit line saved.")
            elif action == "update_kit_line":
                line = get_object_or_404(PostAssetKitLine, pk=request.POST.get("kit_line_id"))
                line.asset_type = get_object_or_404(GuardAssetType, pk=request.POST.get("asset_type_id"))
                line.quantity_required = parse_int_field(
                    request.POST.get("quantity_required") or 1,
                    label="Quantity",
                    min_value=1,
                )
                line.is_optional = bool(request.POST.get("is_optional"))
                line.save()
                messages.success(request, "Kit line updated.")
            elif action == "delete_kit_line":
                get_object_or_404(PostAssetKitLine, pk=request.POST.get("kit_line_id")).delete()
                messages.success(request, "Kit line removed.")
            elif action == "asset_policy":
                site_id = request.POST.get("site_id", "").strip()
                post_id = request.POST.get("post_id", "").strip()
                if site_id and post_id:
                    raise ValueError("Policy must be for a site OR a post, not both.")
                if not site_id and not post_id:
                    raise ValueError("Select a site or a post for the policy.")
                defaults = {
                    "default_mode": request.POST.get("default_mode")
                    or GuardingAssetPolicy.EnforcementMode.ADVISORY,
                    "enforce_issue_before_clock_in": bool(request.POST.get("enforce_issue_before_clock_in")),
                    "enforce_return_before_clock_out": bool(request.POST.get("enforce_return_before_clock_out")),
                    "allow_supervisor_override": bool(request.POST.get("allow_supervisor_override")),
                    "is_active": not bool(request.POST.get("inactive")),
                }
                if post_id:
                    GuardingAssetPolicy.objects.update_or_create(post_id=post_id, defaults=defaults)
                else:
                    GuardingAssetPolicy.objects.update_or_create(site_id=site_id, defaults=defaults)
                messages.success(request, "Asset policy saved.")
            elif action == "update_asset_policy":
                policy = get_object_or_404(GuardingAssetPolicy, pk=request.POST.get("policy_id"))
                _apply_policy_scope(policy, request)
                policy.default_mode = request.POST.get("default_mode") or policy.default_mode
                policy.enforce_issue_before_clock_in = bool(request.POST.get("enforce_issue_before_clock_in"))
                policy.enforce_return_before_clock_out = bool(request.POST.get("enforce_return_before_clock_out"))
                policy.allow_supervisor_override = bool(request.POST.get("allow_supervisor_override"))
                policy.is_active = not bool(request.POST.get("inactive"))
                policy.full_clean()
                policy.save()
                messages.success(request, "Asset policy updated.")
            elif action == "delete_asset_policy":
                get_object_or_404(GuardingAssetPolicy, pk=request.POST.get("policy_id")).delete()
                messages.success(request, "Asset policy deleted.")
            else:
                messages.error(request, "Unknown action.")
        except ProtectedError:
            messages.error(request, "Cannot delete: this record is still referenced by other data.")
        except Exception as exc:
            messages.error(request, str(exc))
        tab = request.POST.get("return_tab", "")
        if tab:
            return redirect(f"{redirect_url}?tab={tab}")
        return redirect(redirect_url)


def handle_shifts_asset_action(request):
    action = request.POST.get("action", "")

    if action == "add_manifest_line":
        manifest = get_object_or_404(ShiftAssetManifest, pk=request.POST.get("manifest_id"))
        add_manifest_line(
            manifest,
            asset_type=get_object_or_404(GuardAssetType, pk=request.POST.get("asset_type_id")),
            expected_qty=parse_int_field(request.POST.get("expected_qty") or 1, label="Expected qty", min_value=1),
            notes=request.POST.get("notes", "").strip(),
        )
        messages.success(request, "Manifest line added.")
        return True

    if action == "update_manifest_line":
        line = get_object_or_404(ShiftAssetManifestLine, pk=request.POST.get("line_id"))
        update_manifest_line(
            line,
            expected_qty=parse_int_field(request.POST.get("expected_qty") or 1, label="Expected qty", min_value=1),
            notes=request.POST.get("notes", "").strip(),
        )
        messages.success(request, "Manifest line updated.")
        return True

    if action == "delete_manifest_line":
        line = get_object_or_404(ShiftAssetManifestLine, pk=request.POST.get("line_id"))
        delete_manifest_line(line)
        messages.success(request, "Manifest line removed.")
        return True

    assignment_id = request.POST.get("assignment_id")
    if not assignment_id:
        raise ValueError("assignment_id is required.")
    assignment = get_object_or_404(
        ShiftAssignment.objects.select_related("shift__post", "guard"),
        pk=assignment_id,
    )
    depot = GuardAssetDepot.objects.filter(pk=request.POST.get("depot_id")).first()

    if action == "build_manifest":
        build_manifest_for_assignment(assignment, depot=depot, issued_by=request.user)
        messages.success(request, "Asset manifest created from post kit.")
    elif action == "rebuild_manifest":
        rebuild_manifest_for_assignment(assignment, depot=depot, issued_by=request.user)
        messages.success(request, "Manifest rebuilt from post kit.")
    elif action == "issue_manifest_line":
        line = get_object_or_404(ShiftAssetManifestLine, pk=request.POST.get("line_id"))
        unit = GuardAssetUnit.objects.filter(pk=request.POST.get("asset_unit_id")).first()
        issue_manifest_line(
            line,
            asset_unit=unit,
            quantity=parse_int_field(request.POST.get("quantity") or 1, label="Quantity", min_value=1),
            condition_out=request.POST.get("condition_out", "").strip(),
            issued_by=request.user,
            depot=depot,
        )
        messages.success(request, "Asset line issued.")
    elif action == "return_manifest_line":
        line = get_object_or_404(ShiftAssetManifestLine, pk=request.POST.get("line_id"))
        qty_raw = request.POST.get("quantity")
        return_manifest_line(
            line,
            quantity=parse_int_field(qty_raw, label="Quantity", min_value=1) if qty_raw else None,
            condition_in=request.POST.get("condition_in", "").strip(),
            status=request.POST.get("line_status") or None,
            returned_by=request.user,
            notes=request.POST.get("notes", "").strip(),
        )
        sync_offboarding_equipment_flag(assignment.guard)
        messages.success(request, "Asset line updated.")
    elif action == "close_manifest":
        manifest = get_object_or_404(ShiftAssetManifest, assignment=assignment)
        close_manifest(manifest, closed_by=request.user)
        sync_offboarding_equipment_flag(assignment.guard)
        messages.success(request, "Manifest closed.")
    elif action == "override_asset_enforcement":
        manifest = get_object_or_404(ShiftAssetManifest, assignment=assignment)
        override_asset_enforcement(
            manifest,
            phase=request.POST.get("phase") or "clock_in",
            reason=request.POST.get("reason", "").strip() or "Supervisor override",
            actor=request.user,
        )
        messages.success(request, "Asset enforcement overridden.")
    elif action == "delete_draft_manifest":
        manifest = get_object_or_404(ShiftAssetManifest, assignment=assignment)
        if manifest.status != ShiftAssetManifest.Status.DRAFT:
            raise ValueError("Only draft manifests can be deleted.")
        if manifest.lines.exclude(status=ShiftAssetManifestLine.Status.PENDING).exists():
            raise ValueError("Cannot delete a manifest with issued or returned lines.")
        manifest.delete()
        messages.success(request, "Draft manifest deleted.")
    else:
        return False
    return True


def posts_asset_context():
    return {
        "asset_kits": PostAssetKit.objects.select_related("post", "post__site")
        .prefetch_related("lines__asset_type")
        .order_by("post__site__name", "post__name", "name")[:200],
        "asset_types": GuardAssetType.objects.filter(is_active=True).order_by("name"),
    }


def handle_posts_asset_action(request):
    action = request.POST.get("action", "")
    if action == "post_kit":
        post = get_object_or_404(GuardPost, pk=request.POST.get("post_id"))
        kit = PostAssetKit.objects.create(
            post=post,
            name=request.POST.get("name", "").strip() or "Default kit",
            is_default=bool(request.POST.get("is_default")),
            is_active=not bool(request.POST.get("inactive")),
        )
        if kit.is_default:
            PostAssetKit.objects.filter(post=post, is_default=True).exclude(pk=kit.pk).update(is_default=False)
        messages.success(request, "Post kit created.")
        return True
    if action == "kit_line":
        kit = get_object_or_404(PostAssetKit, pk=request.POST.get("kit_id"))
        PostAssetKitLine.objects.update_or_create(
            kit=kit,
            asset_type=get_object_or_404(GuardAssetType, pk=request.POST.get("asset_type_id")),
            defaults={
                "quantity_required": parse_int_field(
                    request.POST.get("quantity_required") or 1,
                    label="Quantity",
                    min_value=1,
                ),
                "is_optional": bool(request.POST.get("is_optional")),
            },
        )
        messages.success(request, "Kit line saved.")
        return True
    if action == "delete_kit_line":
        get_object_or_404(PostAssetKitLine, pk=request.POST.get("kit_line_id")).delete()
        messages.success(request, "Kit line removed.")
        return True
    if action == "update_post_kit":
        kit = get_object_or_404(PostAssetKit, pk=request.POST.get("kit_id"))
        kit.post = get_object_or_404(GuardPost, pk=request.POST.get("post_id"))
        kit.name = request.POST.get("name", "").strip() or kit.name
        kit.is_default = bool(request.POST.get("is_default"))
        kit.is_active = not bool(request.POST.get("inactive"))
        kit.save()
        if kit.is_default:
            _clear_default_kit(kit.post, exclude_kit_id=kit.pk)
        messages.success(request, "Post kit updated.")
        return True
    if action == "delete_post_kit":
        get_object_or_404(PostAssetKit, pk=request.POST.get("kit_id")).delete()
        messages.success(request, "Post kit deleted.")
        return True
    return False
