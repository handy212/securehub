from django.contrib import admin

from .models import (
    Checkpoint,
    CheckpointScan,
    ClockEvent,
    DispatchTask,
    FieldReport,
    FieldReportAttachment,
    FieldReportAcknowledgement,
    ClientPortalAccess,
    GuardApplicant,
    GuardApplicantDocument,
    GuardApplicantEducation,
    GuardApplicantEmployment,
    GuardApplicantProfile,
    GuardApplicantReference,
    GuardAvailability,
    GuardContract,
    GuardCredential,
    GuardDocument,
    GuardEquipmentIssue,
    GuardInvoice,
    GuardInvoiceLine,
    GuardOffboardingChecklist,
    GuardTimesheet,
    GuardTrainingRecord,
    GuardingEventLog,
    GuardLocationPing,
    GuardPanicAlert,
    GuardPost,
    GuardProfile,
    LeaveRequest,
    PatrolRoute,
    PatrolRouteCheckpoint,
    PatrolRound,
    PostOrder,
    ReportTemplate,
    Shift,
    ShiftAssignment,
    ShiftSwapRequest,
    ShiftTemplate,
    WelfareCheck,
)


class GuardCredentialInline(admin.TabularInline):
    model = GuardCredential
    extra = 0


class GuardDocumentInline(admin.TabularInline):
    model = GuardDocument
    extra = 0


class GuardTrainingInline(admin.TabularInline):
    model = GuardTrainingRecord
    extra = 0


class GuardEquipmentInline(admin.TabularInline):
    model = GuardEquipmentIssue
    extra = 0


class GuardApplicantDocumentInline(admin.TabularInline):
    model = GuardApplicantDocument
    extra = 0


class GuardApplicantEducationInline(admin.TabularInline):
    model = GuardApplicantEducation
    extra = 0


class GuardApplicantEmploymentInline(admin.TabularInline):
    model = GuardApplicantEmployment
    extra = 0


class GuardApplicantReferenceInline(admin.TabularInline):
    model = GuardApplicantReference
    extra = 0


@admin.register(GuardApplicant)
class GuardApplicantAdmin(admin.ModelAdmin):
    list_display = ("full_name", "national_id", "phone_number", "email", "status", "created_at")
    list_filter = ("status", "country", "background_check_status")
    search_fields = ("first_name", "last_name", "phone_number", "email", "national_id")
    inlines = (
        GuardApplicantDocumentInline,
        GuardApplicantEducationInline,
        GuardApplicantEmploymentInline,
        GuardApplicantReferenceInline,
    )


@admin.register(GuardApplicantProfile)
class GuardApplicantProfileAdmin(admin.ModelAdmin):
    list_display = ("applicant", "shift_preference", "available_start_date")


@admin.register(GuardProfile)
class GuardProfileAdmin(admin.ModelAdmin):
    list_display = ("employee_number", "full_name", "phone_number", "status", "hire_date", "supervisor")
    list_filter = ("status",)
    search_fields = ("employee_number", "first_name", "last_name", "phone_number", "email")
    inlines = (GuardCredentialInline, GuardDocumentInline, GuardTrainingInline, GuardEquipmentInline)


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


@admin.register(GuardTrainingRecord)
class GuardTrainingRecordAdmin(admin.ModelAdmin):
    list_display = ("guard", "name", "provider", "status", "completed_on", "expires_on")
    list_filter = ("status",)
    search_fields = ("guard__first_name", "guard__last_name", "name", "provider", "certificate_number")


@admin.register(GuardEquipmentIssue)
class GuardEquipmentIssueAdmin(admin.ModelAdmin):
    list_display = ("guard", "item_name", "item_code", "quantity", "status", "issued_at", "returned_at")
    list_filter = ("status",)
    search_fields = ("guard__first_name", "guard__last_name", "item_name", "item_code")


@admin.register(GuardOffboardingChecklist)
class GuardOffboardingChecklistAdmin(admin.ModelAdmin):
    list_display = ("guard", "is_complete", "equipment_returned", "access_revoked", "final_timesheet_approved", "completed_at")
    list_filter = ("equipment_returned", "documents_archived", "access_revoked", "final_timesheet_approved")
    search_fields = ("guard__first_name", "guard__last_name", "guard__employee_number")


class PostOrderInline(admin.TabularInline):
    model = PostOrder
    extra = 0


class GuardContractInline(admin.TabularInline):
    model = GuardContract
    extra = 0
    fk_name = "post"


@admin.register(GuardPost)
class GuardPostAdmin(admin.ModelAdmin):
    list_display = ("name", "site", "code", "geofence_radius_m", "is_active", "supervisor")
    list_filter = ("is_active", "site")
    search_fields = ("name", "code", "site__name")
    inlines = (PostOrderInline, GuardContractInline)


@admin.register(GuardContract)
class GuardContractAdmin(admin.ModelAdmin):
    list_display = ("name", "site", "post", "status", "starts_on", "ends_on", "bill_rate", "pay_rate")
    list_filter = ("status", "site")
    search_fields = ("name", "site__name", "post__name")


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


@admin.register(ShiftSwapRequest)
class ShiftSwapRequestAdmin(admin.ModelAdmin):
    list_display = ("assignment", "requested_by", "target_guard", "status", "created_at", "reviewed_at")
    list_filter = ("status", "assignment__shift__post__site")
    search_fields = ("requested_by__first_name", "requested_by__last_name", "target_guard__first_name", "target_guard__last_name")


@admin.register(GuardAvailability)
class GuardAvailabilityAdmin(admin.ModelAdmin):
    list_display = ("guard", "availability_type", "starts_at", "ends_at", "reason")
    list_filter = ("availability_type",)
    search_fields = ("guard__first_name", "guard__last_name", "guard__employee_number", "reason")


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ("guard", "status", "starts_at", "ends_at", "reviewed_by", "reviewed_at")
    list_filter = ("status",)
    search_fields = ("guard__first_name", "guard__last_name", "guard__employee_number", "reason")


@admin.register(ShiftTemplate)
class ShiftTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "post", "start_time", "end_time", "required_guards", "is_active")
    list_filter = ("is_active", "post__site")
    search_fields = ("name", "post__name", "post__site__name")


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


class FieldReportAcknowledgementInline(admin.TabularInline):
    model = FieldReportAcknowledgement
    extra = 0
    readonly_fields = ("acknowledged_at",)


@admin.register(FieldReport)
class FieldReportAdmin(admin.ModelAdmin):
    list_display = ("title", "site", "guard", "report_type", "status", "visible_to_client", "submitted_at")
    list_filter = ("report_type", "status", "visible_to_client", "site")
    search_fields = ("title", "body", "guard__first_name", "guard__last_name", "site__name")
    inlines = (FieldReportAttachmentInline, FieldReportAcknowledgementInline)


@admin.register(ReportTemplate)
class ReportTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "report_type", "site", "is_active", "created_at")
    list_filter = ("report_type", "is_active", "site")
    search_fields = ("name", "site__name")


@admin.register(GuardTimesheet)
class GuardTimesheetAdmin(admin.ModelAdmin):
    list_display = ("guard", "site", "period_start", "period_end", "regular_minutes", "overtime_minutes", "status")
    list_filter = ("status", "site")
    search_fields = ("guard__first_name", "guard__last_name", "guard__employee_number", "site__name")


class GuardInvoiceLineInline(admin.TabularInline):
    model = GuardInvoiceLine
    extra = 0


@admin.register(GuardInvoice)
class GuardInvoiceAdmin(admin.ModelAdmin):
    list_display = ("invoice_number", "site", "contract", "status", "period_start", "period_end", "total")
    list_filter = ("status", "site")
    search_fields = ("invoice_number", "site__name", "contract__name")
    inlines = (GuardInvoiceLineInline,)


@admin.register(GuardInvoiceLine)
class GuardInvoiceLineAdmin(admin.ModelAdmin):
    list_display = ("invoice", "description", "quantity_hours", "bill_rate", "amount")
    search_fields = ("invoice__invoice_number", "description")


@admin.register(ClientPortalAccess)
class ClientPortalAccessAdmin(admin.ModelAdmin):
    list_display = ("user", "site", "role", "can_view_reports", "can_view_patrols", "can_view_attendance", "can_view_guards")
    list_filter = ("role", "can_view_reports", "can_view_patrols", "can_view_attendance", "can_view_guards")
    search_fields = ("user__username", "user__email", "site__name")


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


from .asset_models import (  # noqa: E402
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


@admin.register(GuardAssetType)
class GuardAssetTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "category", "tracking_mode", "is_active")
    list_filter = ("category", "tracking_mode", "is_active")
    search_fields = ("name", "code")


@admin.register(GuardAssetDepot)
class GuardAssetDepotAdmin(admin.ModelAdmin):
    list_display = ("name", "site", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "site__name")


@admin.register(GuardAssetUnit)
class GuardAssetUnitAdmin(admin.ModelAdmin):
    list_display = ("asset_tag", "asset_type", "depot", "status")
    list_filter = ("status", "asset_type")
    search_fields = ("asset_tag", "serial_number")


@admin.register(GuardAssetStock)
class GuardAssetStockAdmin(admin.ModelAdmin):
    list_display = ("asset_type", "depot", "quantity_on_hand", "quantity_reserved")


@admin.register(PostAssetKit)
class PostAssetKitAdmin(admin.ModelAdmin):
    list_display = ("name", "post", "is_default", "is_active")
    list_filter = ("is_active", "is_default")


@admin.register(ShiftAssetManifest)
class ShiftAssetManifestAdmin(admin.ModelAdmin):
    list_display = ("assignment", "status", "enforcement_mode", "issued_at", "closed_at")
    list_filter = ("status", "enforcement_mode")


@admin.register(GuardingAssetPolicy)
class GuardingAssetPolicyAdmin(admin.ModelAdmin):
    list_display = ("site", "post", "default_mode", "is_active")
    list_filter = ("default_mode", "is_active")
