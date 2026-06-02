"""Operational KPI calculations for guarding dashboards."""

from __future__ import annotations

from django.db.models import Count, Q
from django.utils import timezone

from .models import (
    CheckpointScan,
    ClockEvent,
    DispatchTask,
    GuardingEventLog,
    PatrolRound,
    Shift,
    ShiftAssignment,
)


def guarding_kpis(*, days: int = 7):
    now = timezone.now()
    start = now - timezone.timedelta(days=days)
    shifts = Shift.objects.filter(starts_at__gte=start, starts_at__lte=now)
    assignments = ShiftAssignment.objects.filter(shift__in=shifts)
    total_assignments = assignments.count()
    no_shows = assignments.filter(status=ShiftAssignment.Status.NO_SHOW).count()
    late_clock_ins = GuardingEventLog.objects.filter(
        event_type="clock_in_late",
        created_at__gte=start,
    ).count()
    patrol_rounds = PatrolRound.objects.filter(scheduled_start__gte=start, scheduled_start__lte=now)
    missed_patrols = patrol_rounds.filter(status=PatrolRound.Status.MISSED).count()
    completed_patrols = patrol_rounds.filter(status=PatrolRound.Status.COMPLETED).count()
    patrol_total = patrol_rounds.count()
    scans = CheckpointScan.objects.filter(scanned_at__gte=start).count()
    sla_breaches = GuardingEventLog.objects.filter(
        event_type__startswith="dispatch_",
        severity=GuardingEventLog.Severity.CRITICAL,
        created_at__gte=start,
    ).count()
    open_dispatch = DispatchTask.objects.exclude(
        status__in=[DispatchTask.Status.RESOLVED, DispatchTask.Status.CANCELLED]
    ).count()

    coverage_assignments = assignments.exclude(
        status__in=[ShiftAssignment.Status.DECLINED, ShiftAssignment.Status.REMOVED]
    ).count()
    required = shifts.aggregate(total=Count("id"))["total"] or 0

    asset_stats = {}
    try:
        from .asset_services import asset_analytics_summary

        asset_stats = asset_analytics_summary()
    except Exception:
        asset_stats = {
            "open_manifests": 0,
            "units_out": 0,
            "lost_this_week": 0,
            "overdue_returns": 0,
        }

    return {
        "period_days": days,
        "total_assignments": total_assignments,
        "coverage_assignments": coverage_assignments,
        "no_show_rate": round((no_shows / total_assignments) * 100, 1) if total_assignments else 0,
        "late_clock_in_count": late_clock_ins,
        "missed_patrol_rate": round((missed_patrols / patrol_total) * 100, 1) if patrol_total else 0,
        "patrol_completion_rate": round((completed_patrols / patrol_total) * 100, 1) if patrol_total else 0,
        "checkpoint_scans": scans,
        "dispatch_sla_breaches": sla_breaches,
        "open_dispatch_tasks": open_dispatch,
        "shifts_in_period": required,
        "open_asset_manifests": asset_stats.get("open_manifests", 0),
        "asset_units_out": asset_stats.get("units_out", 0),
        "asset_lost_week": asset_stats.get("lost_this_week", 0),
        "asset_overdue_returns": asset_stats.get("overdue_returns", 0),
    }
