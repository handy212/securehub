"""Bridge alarm/emergency workflows into guard dispatch tasks."""

from __future__ import annotations

from django.db import transaction

from apps.emergency.models import EmergencyRequest

from .models import DispatchTask, SiteGuardDispatchPolicy
from .services import create_workflow_event, suggest_nearest_guards


def _policy_for_site(site):
    if site is None:
        return None
    return SiteGuardDispatchPolicy.objects.filter(site=site, is_active=True).first()


@transaction.atomic
def create_dispatch_from_emergency(emergency: EmergencyRequest, *, actor=None) -> DispatchTask | None:
    if emergency.site_id is None:
        return None
    existing = DispatchTask.objects.filter(emergency_request=emergency).exclude(
        status=DispatchTask.Status.CANCELLED
    ).first()
    if existing:
        return existing

    policy = _policy_for_site(emergency.site)
    if policy is not None and not policy.auto_from_emergency:
        return None

    priority = policy.default_priority if policy else DispatchTask.Priority.HIGH
    task = DispatchTask.objects.create(
        site=emergency.site,
        status=DispatchTask.Status.OPEN,
        priority=priority,
        title=f"Emergency patrol — {emergency.site.name}",
        description=emergency.note or "Customer emergency patrol request.",
        target_latitude=emergency.latitude,
        target_longitude=emergency.longitude,
        emergency_request=emergency,
        created_by=actor,
    )
    create_workflow_event(
        event_type="dispatch_from_emergency",
        title="Dispatch created from emergency",
        message=f"Emergency {emergency.id} linked to dispatch {task.id}.",
        obj=task,
        site=emergency.site,
        actor=actor,
        metadata={"emergency_request_id": str(emergency.id)},
    )

    if policy and policy.auto_assign_nearest:
        suggestions = suggest_nearest_guards(
            emergency.site,
            float(emergency.latitude),
            float(emergency.longitude),
            limit=1,
        )
        if suggestions:
            from .services import assign_dispatch_task

            guard = suggestions[0]["guard"]
            task = assign_dispatch_task(task, guard=guard, actor=actor)

    return task


@transaction.atomic
def create_dispatch_from_alarm(alarm_event, *, actor=None) -> DispatchTask | None:
    site = getattr(alarm_event, "site", None)
    if site is None:
        return None

    policy = _policy_for_site(site)
    if policy is None or not policy.auto_from_alarm:
        return None

    severities = policy.alarm_severities or []
    severity = getattr(alarm_event, "severity", "")
    if severities and severity not in severities:
        return None

    existing = DispatchTask.objects.filter(alarm_event=alarm_event).exclude(
        status=DispatchTask.Status.CANCELLED
    ).first()
    if existing:
        return existing

    task = DispatchTask.objects.create(
        site=site,
        status=DispatchTask.Status.OPEN,
        priority=policy.default_priority,
        title=f"Alarm response — {site.name}",
        description=getattr(alarm_event, "event_name", "") or "Automated dispatch from alarm event.",
        alarm_event=alarm_event,
        created_by=actor,
    )
    create_workflow_event(
        event_type="dispatch_from_alarm",
        title="Dispatch created from alarm",
        message=f"Alarm event linked to dispatch {task.id}.",
        obj=task,
        site=site,
        actor=actor,
        metadata={"alarm_event_id": str(alarm_event.id)},
    )
    return task
