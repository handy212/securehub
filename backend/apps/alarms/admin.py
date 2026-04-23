from django.contrib import admin

from .models import AlarmEvent, ArmDisarmCommand, NotificationDelivery


@admin.register(AlarmEvent)
class AlarmEventAdmin(admin.ModelAdmin):
    list_display = ("event_type", "performed_by", "site", "subsystem", "zone", "occurred_at")
    search_fields = (
        "event_type",
        "site__name",
        "zone__name",
        "source_event_id",
        "performed_by",
    )


@admin.register(ArmDisarmCommand)
class ArmDisarmCommandAdmin(admin.ModelAdmin):
    list_display = ("action", "site", "subsystem", "requested_by", "status", "created_at")
    search_fields = ("action", "site__name", "requested_by__username")


@admin.register(NotificationDelivery)
class NotificationDeliveryAdmin(admin.ModelAdmin):
    list_display = ("channel", "recipient", "status", "sent_at")
    search_fields = ("recipient", "channel")
