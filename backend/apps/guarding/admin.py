from django.contrib import admin

from .models import (
    Checkpoint,
    CheckpointScan,
    ClockEvent,
    DispatchTask,
    FieldReport,
    FieldReportAttachment,
    GuardApplicant,
    GuardCredential,
    GuardDocument,
    GuardingEventLog,
    GuardLocationPing,
    GuardPanicAlert,
    GuardPost,
    GuardProfile,
    PatrolRoute,
    PatrolRouteCheckpoint,
    PatrolRound,
    PostOrder,
    Shift,
    ShiftAssignment,
    WelfareCheck,
)


class GuardCredentialInline(admin.TabularInline):
    model = GuardCredential
    extra = 0


class GuardDocumentInline(admin.TabularInline):
    model = GuardDocument
    extra = 0


@admin.register(GuardApplicant)
class GuardApplicantAdmin(admin.ModelAdmin):
    list_display = ("full_name", "phone_number", "email", "status", "created_at")
    list_filter = ("status", "country")
    search_fields = ("first_name", "last_name", "phone_number", "email")


@admin.register(GuardProfile)
class GuardProfileAdmin(admin.ModelAdmin):
    list_display = ("employee_number", "full_name", "phone_number", "status", "hire_date", "supervisor")
    list_filter = ("status",)
    search_fields = ("employee_number", "first_name", "last_name", "phone_number", "email")
    inlines = (GuardCredentialInline, GuardDocumentInline)


@admin.register(GuardCredential)
class GuardCredentialAdmin(admin.ModelAdmin):
    list_display = ("guard", "credential_type", "name", "expires_on", "verified")
    list_filter = ("credential_type", "verified")
    search_fields = ("guard__first_name", "guard__last_name", "name", "reference_number")


@admin.register(GuardDocument)
class GuardDocumentAdmin(admin.ModelAdmin):
    list_display = ("guard", "document_type", "title", "expires_on", "created_at")
    list_filter = ("document_type",)
    search_fields = ("guard__first_name", "guard__last_name", "title", "reference_number")


class PostOrderInline(admin.TabularInline):
    model = PostOrder
    extra = 0


@admin.register(GuardPost)
class GuardPostAdmin(admin.ModelAdmin):
    list_display = ("name", "site", "code", "geofence_radius_m", "is_active", "supervisor")
    list_filter = ("is_active", "site")
    search_fields = ("name", "code", "site__name")
    inlines = (PostOrderInline,)


@admin.register(PostOrder)
class PostOrderAdmin(admin.ModelAdmin):
    list_display = ("title", "post", "is_active", "effective_from", "effective_until")
    list_filter = ("is_active",)
    search_fields = ("title", "post__name", "post__site__name")


class ShiftAssignmentInline(admin.TabularInline):
    model = ShiftAssignment
    extra = 0


@admin.register(Shift)
class ShiftAdmin(admin.ModelAdmin):
    list_display = ("post", "starts_at", "ends_at", "status", "required_guards")
    list_filter = ("status", "post__site")
    search_fields = ("post__name", "post__site__name")
    inlines = (ShiftAssignmentInline,)


@admin.register(ShiftAssignment)
class ShiftAssignmentAdmin(admin.ModelAdmin):
    list_display = ("guard", "shift", "status", "clocked_in_at", "clocked_out_at")
    list_filter = ("status", "shift__post__site")
    search_fields = ("guard__first_name", "guard__last_name", "guard__employee_number", "shift__post__name")


@admin.register(ClockEvent)
class ClockEventAdmin(admin.ModelAdmin):
    list_display = ("assignment", "event_type", "within_geofence", "created_at")
    list_filter = ("event_type", "within_geofence")
    search_fields = ("assignment__guard__first_name", "assignment__guard__last_name")


class PatrolRouteCheckpointInline(admin.TabularInline):
    model = PatrolRouteCheckpoint
    extra = 0


@admin.register(Checkpoint)
class CheckpointAdmin(admin.ModelAdmin):
    list_display = ("name", "post", "checkpoint_type", "code", "is_active")
    list_filter = ("checkpoint_type", "is_active", "post__site")
    search_fields = ("name", "code", "post__name", "post__site__name")


@admin.register(PatrolRoute)
class PatrolRouteAdmin(admin.ModelAdmin):
    list_display = ("name", "post", "expected_duration_minutes", "is_active")
    list_filter = ("is_active", "post__site")
    search_fields = ("name", "post__name", "post__site__name")
    inlines = (PatrolRouteCheckpointInline,)


@admin.register(PatrolRound)
class PatrolRoundAdmin(admin.ModelAdmin):
    list_display = ("route", "assignment", "scheduled_start", "status", "completed_at")
    list_filter = ("status", "route__post__site")
    search_fields = ("route__name", "assignment__guard__first_name", "assignment__guard__last_name")


@admin.register(CheckpointScan)
class CheckpointScanAdmin(admin.ModelAdmin):
    list_display = ("checkpoint", "guard", "patrol_round", "within_geofence", "scanned_at")
    list_filter = ("within_geofence", "checkpoint__post__site")
    search_fields = ("checkpoint__name", "guard__first_name", "guard__last_name")


class FieldReportAttachmentInline(admin.TabularInline):
    model = FieldReportAttachment
    extra = 0


@admin.register(FieldReport)
class FieldReportAdmin(admin.ModelAdmin):
    list_display = ("title", "site", "guard", "report_type", "status", "visible_to_client", "submitted_at")
    list_filter = ("report_type", "status", "visible_to_client", "site")
    search_fields = ("title", "body", "guard__first_name", "guard__last_name", "site__name")
    inlines = (FieldReportAttachmentInline,)


@admin.register(GuardLocationPing)
class GuardLocationPingAdmin(admin.ModelAdmin):
    list_display = ("guard", "assignment", "latitude", "longitude", "created_at")
    search_fields = ("guard__first_name", "guard__last_name", "guard__employee_number")


@admin.register(WelfareCheck)
class WelfareCheckAdmin(admin.ModelAdmin):
    list_display = ("assignment", "status", "due_at", "responded_at")
    list_filter = ("status",)
    search_fields = ("assignment__guard__first_name", "assignment__guard__last_name")


@admin.register(GuardPanicAlert)
class GuardPanicAlertAdmin(admin.ModelAdmin):
    list_display = ("guard", "site", "status", "created_at", "acknowledged_at", "resolved_at")
    list_filter = ("status", "site")
    search_fields = ("guard__first_name", "guard__last_name", "site__name")


@admin.register(DispatchTask)
class DispatchTaskAdmin(admin.ModelAdmin):
    list_display = ("title", "site", "assigned_guard", "status", "priority", "created_at")
    list_filter = ("status", "priority", "site")
    search_fields = ("title", "description", "assigned_guard__first_name", "assigned_guard__last_name", "site__name")


@admin.register(GuardingEventLog)
class GuardingEventLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "severity", "event_type", "title", "guard", "site", "source")
    list_filter = ("severity", "source", "event_type", "site")
    search_fields = ("title", "message", "object_label", "object_id", "guard__first_name", "guard__last_name", "site__name")
    readonly_fields = ("created_at",)
