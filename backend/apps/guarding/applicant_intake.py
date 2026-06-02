"""Shared applicant intake helpers for console and public apply flows."""

from __future__ import annotations

from datetime import date

from django.http import HttpRequest
from django.utils import timezone

from .applicant_forms import populate_applicant_from_request, populate_applicant_profile_from_request
from .models import (
    GuardApplicant,
    GuardApplicantDocument,
    GuardApplicantEducation,
    GuardApplicantEmployment,
    GuardApplicantProfile,
    GuardApplicantReference,
)


def parse_date_value(raw_value: str, *, label: str) -> date:
    try:
        return date.fromisoformat(str(raw_value).strip())
    except (TypeError, ValueError, AttributeError) as exc:
        raise ValueError(f"{label} must be a valid date.") from exc


def applicant_form_choices() -> dict:
    return {
        "gender_choices": [
            ("male", "Male"),
            ("female", "Female"),
            ("other", "Other"),
            ("prefer_not", "Prefer not to say"),
        ],
        "marital_status_choices": [
            ("single", "Single"),
            ("married", "Married"),
            ("divorced", "Divorced"),
            ("widowed", "Widowed"),
            ("other", "Other"),
        ],
        "shift_preference_choices": GuardApplicantProfile.ShiftPreference.choices,
        "document_types": GuardApplicantDocument.DocumentType.choices,
    }


def _zip_post_lists(request: HttpRequest, field_names: list[str]) -> list[dict[str, str]]:
    lists = [request.POST.getlist(name) for name in field_names]
    if not any(lists):
        return []
    max_len = max(len(values) for values in lists)
    rows: list[dict[str, str]] = []
    for index in range(max_len):
        row = {}
        for name, values in zip(field_names, lists, strict=False):
            row[name] = values[index].strip() if index < len(values) else ""
        rows.append(row)
    return rows


def _save_education_rows(applicant: GuardApplicant, request: HttpRequest) -> None:
    for row in _zip_post_lists(
        request,
        ["education_level", "education_institution", "education_year", "education_certificates"],
    ):
        level = row["education_level"]
        if not level:
            continue
        year_raw = row["education_year"]
        GuardApplicantEducation.objects.create(
            applicant=applicant,
            education_level=level,
            institution_name=row["education_institution"],
            year_completed=int(year_raw) if year_raw else None,
            certificates_obtained=row["education_certificates"],
        )


def _save_employment_rows(applicant: GuardApplicant, request: HttpRequest, *, parse_dates) -> None:
    from decimal import Decimal, InvalidOperation

    for row in _zip_post_lists(
        request,
        [
            "employment_company",
            "employment_position",
            "employment_duties",
            "employment_supervisor",
            "employment_supervisor_contact",
            "employment_started_on",
            "employment_ended_on",
            "employment_years",
            "employment_reason",
        ],
    ):
        company = row["employment_company"]
        if not company:
            continue
        record = GuardApplicantEmployment(applicant=applicant, company_name=company)
        record.position = row["employment_position"]
        record.duties = row["employment_duties"]
        record.supervisor_name = row["employment_supervisor"]
        record.supervisor_contact = row["employment_supervisor_contact"]
        record.reason_for_leaving = row["employment_reason"]
        years_raw = row["employment_years"]
        if years_raw:
            try:
                record.years_experience = Decimal(years_raw)
            except InvalidOperation as exc:
                raise ValueError("Years of experience must be a number.") from exc
        if row["employment_started_on"]:
            record.started_on = parse_dates(row["employment_started_on"], label="Employment start date")
        if row["employment_ended_on"]:
            record.ended_on = parse_dates(row["employment_ended_on"], label="Employment end date")
        record.save()


def _save_reference_rows(applicant: GuardApplicant, request: HttpRequest) -> None:
    for row in _zip_post_lists(
        request,
        ["reference_name", "reference_company", "reference_position", "reference_phone"],
    ):
        name = row["reference_name"]
        if not name:
            continue
        GuardApplicantReference.objects.create(
            applicant=applicant,
            full_name=name,
            company=row["reference_company"],
            position=row["reference_position"],
            phone_number=row["reference_phone"],
        )


def _save_document_uploads(applicant: GuardApplicant, request: HttpRequest) -> None:
    types = request.POST.getlist("document_type")
    titles = request.POST.getlist("document_title")
    files = request.FILES.getlist("document_file")
    for index, upload in enumerate(files):
        if not upload:
            continue
        doc_type = types[index] if index < len(types) else GuardApplicantDocument.DocumentType.OTHER
        title = titles[index].strip() if index < len(titles) and titles[index].strip() else upload.name
        GuardApplicantDocument.objects.create(
            applicant=applicant,
            document_type=doc_type or GuardApplicantDocument.DocumentType.OTHER,
            title=title,
            file=upload,
            uploaded_by=request.user if request.user.is_authenticated else None,
        )


def _validate_optional_rating_field(request: HttpRequest, field: str, label: str) -> None:
    raw = request.POST.get(field, "").strip()
    if not raw:
        return
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be a whole number from 1 to 5, or left blank.") from exc
    if value < 1 or value > 5:
        raise ValueError(f"{label} must be a whole number from 1 to 5, or left blank.")


def _validate_optional_positive_int_field(request: HttpRequest, field: str, label: str) -> None:
    raw = request.POST.get(field, "").strip()
    if not raw:
        return
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be a positive whole number, or left blank.") from exc
    if value < 1:
        raise ValueError(f"{label} must be a positive whole number, or left blank.")


def _validate_public_profile_fields(request: HttpRequest) -> None:
    for field, label in (
        ("skill_communication", "Communication"),
        ("skill_report_writing", "Report writing"),
        ("skill_computer", "Computer"),
        ("skill_radio", "Radio"),
        ("skill_conflict_resolution", "Conflict resolution"),
    ):
        _validate_optional_rating_field(request, field, label)
    _validate_optional_positive_int_field(request, "height_cm", "Height")
    _validate_optional_positive_int_field(request, "weight_kg", "Weight")


def validate_public_application(request: HttpRequest) -> None:
    from .public_intake import validate_public_documents

    first = request.POST.get("first_name", "").strip()
    last = request.POST.get("last_name", "").strip()
    if not first or not last:
        raise ValueError("First name and last name are required.")
    phone = request.POST.get("phone_number", "").strip()
    email = request.POST.get("email", "").strip()
    if not phone and not email:
        raise ValueError("Provide a phone number or email address.")
    _validate_public_profile_fields(request)
    validate_public_documents(request)
    if not request.POST.get("declaration_signed"):
        raise ValueError("You must accept the declaration to submit.")
    signature = request.POST.get("declaration_signature_name", "").strip()
    if not signature:
        raise ValueError("Type your full name as your declaration signature.")


def create_application_from_request(
    request: HttpRequest,
    *,
    source: str,
    created_by=None,
    is_public: bool = False,
) -> GuardApplicant:
    if is_public:
        validate_public_application(request)

    parse_dates = lambda raw, label: parse_date_value(raw, label=label)  # noqa: E731

    applicant = GuardApplicant(
        created_by=created_by,
        status=GuardApplicant.Status.APPLIED,
        source=source,
    )
    populate_applicant_from_request(applicant, request, parse_dates=parse_dates)
    applicant.source = source
    if is_public:
        applicant.metadata = {
            **(applicant.metadata or {}),
            "public_submission": True,
            "submitted_at": timezone.now().isoformat(),
            "user_agent": (request.META.get("HTTP_USER_AGENT") or "")[:500],
        }
        applicant.interview_notes = ""
        applicant.rejection_reason = ""
        applicant.background_check_status = ""
        applicant.interview_score = None
        applicant.assigned_branch = ""
    applicant.save()
    populate_applicant_profile_from_request(applicant, request, parse_dates=parse_dates)
    _save_education_rows(applicant, request)
    _save_employment_rows(applicant, request, parse_dates=parse_dates)
    _save_reference_rows(applicant, request)
    _save_document_uploads(applicant, request)
    return applicant
