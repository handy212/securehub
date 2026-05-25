from django.shortcuts import get_object_or_404
from django.db.models import Max
from django.urls import reverse
from django.utils.timesince import timesince
from rest_framework.authentication import SessionAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from apps.accounts.permissions import HasConsolePermission
from apps.accounts.rbac import Perm

from apps.sites.models import AlarmOutput, AlarmPeripheral, Site, Zone
from apps.sites.permissions import HasSiteAccess
from apps.alarms.models import AlarmEvent
from apps.hik_adapter.services import HikPartnerService
from apps.dashboard.event_presenters import serialize_console_event
from apps.dashboard.views import _build_active_faults, _visible_console_events
from apps.guarding.services import build_command_center_snapshot
from apps.guarding.models import SiteGuardDispatchPolicy


def build_dispatch_poll_payload():
    snapshot = build_command_center_snapshot()
    active_policies = SiteGuardDispatchPolicy.objects.filter(is_active=True).count()
    return {
        "counts": {
            "open_panic": snapshot["open_panic_count"],
            "open_dispatch": snapshot["active_dispatch_count"],
        },
        "dispatch_tab_counts": {
            "open_panic": snapshot["open_panic_count"],
            "open_tasks": snapshot["active_dispatch_count"],
            "active_policies": active_policies,
        },
        "generated_at": snapshot["generated_at"],
    }


def build_guard_map_payload():
    guard_snapshot = build_command_center_snapshot()
    site_ids = {g["site_id"] for g in guard_snapshot["guards"]}
    site_zones = {}
    if site_ids:
        site_zones = {
            str(row["id"]): {
                "zone_id": str(row["operations_zone_id"]) if row["operations_zone_id"] else None,
                "zone_name": row["operations_zone__name"] or "",
                "zone_color": row["operations_zone__color"] or "",
            }
            for row in Site.objects.filter(id__in=site_ids).values(
                "id", "operations_zone_id", "operations_zone__name", "operations_zone__color"
            )
        }
    guards_data = []
    for guard in guard_snapshot["guards"]:
        if guard["latitude"] is None or guard["longitude"] is None:
            continue
        last_ping = guard["last_ping_at"]
        zone = site_zones.get(guard["site_id"], {})
        guards_data.append(
            {
                "id": guard["guard_id"],
                "name": guard["guard_name"],
                "site_id": guard["site_id"],
                "site": guard["site_name"],
                "post": guard["post_name"],
                "zone_id": zone.get("zone_id"),
                "zone_name": zone.get("zone_name", ""),
                "zone_color": zone.get("zone_color", ""),
                "lat": float(guard["latitude"]),
                "lng": float(guard["longitude"]),
                "open_panic": guard["open_panic"],
                "active_dispatch": guard["active_dispatch"],
                "last_ping_at": last_ping.isoformat() if last_ping else None,
                "last_ping_label": f"{timesince(last_ping)} ago" if last_ping else None,
                "dispatch_url": reverse("dashboard:guarding-dispatch"),
            }
        )
    return {
        "guards": guards_data,
        "snapshot": {
            "on_duty_count": len(guard_snapshot["guards"]),
            "on_map_count": len(guards_data),
            "open_panic_count": guard_snapshot["open_panic_count"],
            "active_dispatch_count": guard_snapshot["active_dispatch_count"],
            "generated_at": guard_snapshot["generated_at"],
        },
    }


class GuardMapSnapshotPollView(APIView):
    """Lightweight guard positions for the global map side panel."""

    authentication_classes = [SessionAuthentication, JWTAuthentication]
    permission_classes = [IsAuthenticated, HasConsolePermission]
    required_console_permission = Perm.VIEW_GUARDING


    def get(self, request):
        return Response(build_guard_map_payload())


class GuardDispatchPollView(APIView):
    """Lightweight SOS/dispatch counts for the guarding dispatch console."""

    authentication_classes = [SessionAuthentication, JWTAuthentication]
    permission_classes = [IsAuthenticated, HasConsolePermission]
    required_console_permission = Perm.VIEW_GUARDING

    def get(self, request):
        return Response(build_dispatch_poll_payload())


class SiteStatusPollThrottle(UserRateThrottle):
    scope = "site_poll"


class SiteStatusPollView(APIView):
    """
    Lightweight site status endpoint for frontend polling.
    Unlike SiteStatusView, this DOES NOT perform a network call to Hikvision.
    It reads exclusively from the local database to ensure sub-millisecond responses.
    """
    authentication_classes = [JWTAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated, HasSiteAccess]
    throttle_classes = [SiteStatusPollThrottle]

    def get(self, request, site_id):
        site = get_object_or_404(Site, id=site_id)
        service = HikPartnerService()
        
        # Get purely local status
        site_status = service.get_site_status(site=site)
        
        # Get most recent events
        recent_events = _visible_console_events(site, limit=15)
        active_faults = _build_active_faults(site)

        return Response({
            "siteId": str(site.id),
            "armedSubsystems": site_status["armed_subsystems"],
            "disarmedSubsystems": site_status["disarmed_subsystems"],
            "activeAlarmCount": site_status["active_alarm_count"],
            "offlineDeviceCount": site_status["offline_device_count"],
            "activeFaultCount": len(active_faults),
            "activeFaults": active_faults[:5],
            "recentEvents": [serialize_console_event(event) for event in recent_events],
            "subsystems": [
                {
                    "id": str(sub.id),
                    "number": sub.subsystem_number,
                    "status": sub.status,
                    "name": sub.name,
                    "panelIsOnline": sub.device.is_online,
                    "zones": [
                        {
                            "id": str(z.id),
                            "name": z.name,
                            "deviceNumber": z.device_number,
                            "deviceType": z.device_type,
                            "detectorType": z.detector_type,
                            "zoneType": z.zone_type,
                            "reason": z.reason,
                            "healthStatus": z.health_status,
                            "modelNumber": z.model_number,
                            "accessModuleType": z.access_module_type,
                            "zoneAttribute": z.zone_attribute,
                            "state": z.state,
                            "signalStrength": z.signal_strength,
                            "lowBattery": z.low_battery,
                            "isOnline": z.is_online,
                            "chargeValue": z.charge_value,
                            "tamper": z.tamper,
                            "shielded": z.shielded,
                            "magnetOpen": z.magnet_open,
                            "networkStatus": z.network_status,
                            "displayType": z.display_type,
                            "iconType": z.icon_type,
                        }
                        for z in sub.zones.all()
                    ],
                } for sub in site_status["subsystems"]
            ],
            "peripherals": [
                {
                    "id": str(p.id),
                    "name": p.name,
                    "type": p.peripheral_type,
                    "number": p.peripheral_number,
                    "serialNumber": p.serial_number,
                    "batteryStatus": p.battery_status,
                    "signalStrength": p.signal_strength,
                    "tamper": p.tamper,
                    "bypassed": p.bypassed,
                    "networkStatus": p.network_status,
                    "isOnline": p.is_online,
                }
                for p in AlarmPeripheral.objects.filter(site=site).order_by("peripheral_type", "peripheral_number")
            ],
            "outputs": [
                {
                    "id": str(o.id),
                    "name": o.name,
                    "number": o.output_number,
                    "status": o.status,
                    "batteryStatus": o.battery_status,
                    "signalStrength": o.signal_strength,
                    "linkage": o.linkage,
                    "scenarioTypes": o.scenario_types,
                    "isOnline": o.is_online,
                }
                for o in AlarmOutput.objects.filter(site=site).order_by("output_number")
            ],
        })
