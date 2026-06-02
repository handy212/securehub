from django.contrib import admin

from .models import CustomerProfile, StaffOperatorProfile


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "phone_number", "is_mobile_user", "created_at")
    search_fields = ("user__username", "user__email", "phone_number")


@admin.register(StaffOperatorProfile)
class StaffOperatorProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "updated_at")
    list_filter = ("role",)
    search_fields = ("user__username", "user__email")
