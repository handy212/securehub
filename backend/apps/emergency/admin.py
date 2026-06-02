from django.contrib import admin

from .models import (
    AccountEmergencyService,
    EmergencyLocationUpdate,
    EmergencyNotificationDelivery,
    EmergencyRequest,
    EmergencyServicePlan,
    SiteEmergencyService,
)


@admin.register(EmergencyServicePlan)
class EmergencyServicePlanAdmin(admin.ModelAdmin):
    list_display = ("name", "monthly_rate", "is_active", "created_at")
    search_fields = ("name",)


@admin.register(AccountEmergencyService)
class AccountEmergencyServiceAdmin(admin.ModelAdmin):
    list_display = ("user", "status", "monthly_rate", "next_due_date")
    search_fields = ("user__username", "user__email")
    list_filter = ("status",)


@admin.register(SiteEmergencyService)
class SiteEmergencyServiceAdmin(admin.ModelAdmin):
    list_display = ("site", "status", "monthly_rate", "next_due_date")
    search_fields = ("site__name",)
    list_filter = ("status",)


class EmergencyLocationUpdateInline(admin.TabularInline):
    model = EmergencyLocationUpdate
    extra = 0
    readonly_fields = ("created_at",)


class EmergencyNotificationDeliveryInline(admin.TabularInline):
    model = EmergencyNotificationDelivery
    extra = 0
    readonly_fields = ("created_at", "sent_at", "last_error")


@admin.register(EmergencyRequest)
class EmergencyRequestAdmin(admin.ModelAdmin):
    list_display = ("customer", "site", "status", "trigger_context", "latitude", "longitude", "created_at")
    list_filter = ("status", "trigger_context")
    search_fields = ("customer__username", "customer__email", "site__name", "contact_phone")
    inlines = (EmergencyLocationUpdateInline, EmergencyNotificationDeliveryInline)


@admin.register(EmergencyLocationUpdate)
class EmergencyLocationUpdateAdmin(admin.ModelAdmin):
    list_display = ("emergency_request", "latitude", "longitude", "accuracy_m", "created_at")
    search_fields = ("emergency_request__customer__username",)
