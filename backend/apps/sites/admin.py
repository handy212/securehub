from django.contrib import admin

from .models import AlarmOutput, AlarmPanelDevice, AlarmPeripheral, CustomerSiteAccess, Site, Subsystem, Zone


@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    list_display = ("name", "city", "country", "hik_site_id", "is_active")
    search_fields = ("name", "hik_site_id", "city", "country")


@admin.register(CustomerSiteAccess)
class CustomerSiteAccessAdmin(admin.ModelAdmin):
    list_display = ("user", "site", "role", "can_control_alarm", "created_at")
    search_fields = ("user__username", "site__name")


@admin.register(AlarmPanelDevice)
class AlarmPanelDeviceAdmin(admin.ModelAdmin):
    list_display = ("name", "site", "serial_number", "model_number", "firmware_version", "is_online")
    search_fields = ("name", "serial_number", "model_number", "hik_device_id")


@admin.register(Subsystem)
class SubsystemAdmin(admin.ModelAdmin):
    list_display = ("name", "site", "device", "hik_subsystem_id", "status")
    search_fields = ("name", "hik_subsystem_id")


@admin.register(Zone)
class ZoneAdmin(admin.ModelAdmin):
    list_display = ("name", "subsystem", "zone_number", "device_type", "zone_type", "state")
    search_fields = ("name",)


@admin.register(AlarmPeripheral)
class AlarmPeripheralAdmin(admin.ModelAdmin):
    list_display = ("name", "site", "device", "peripheral_type", "peripheral_number", "is_online")
    search_fields = ("name", "serial_number", "device__serial_number")


@admin.register(AlarmOutput)
class AlarmOutputAdmin(admin.ModelAdmin):
    list_display = ("name", "site", "device", "output_number", "status", "is_online")
    search_fields = ("name", "serial_number", "device__serial_number")
