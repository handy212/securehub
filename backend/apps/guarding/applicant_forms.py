"""Helpers for populating guard applicant records from dashboard POST data."""

from decimal import Decimal, InvalidOperation

from django.utils import timezone

from .models import GuardApplicant, GuardApplicantProfile


def _parse_bool(value) -> bool:
    return str(value or "").lower() in {"1", "true", "on", "yes"}


def _parse_optional_int(value):
    raw = str(value or "").strip()
    if not raw:
        return None
    return int(raw)


def _parse_optional_decimal(value):
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return Decimal(raw)
    except InvalidOperation as exc:
        raise ValueError("Invalid decimal value.") from exc


def _parse_optional_skill_rating(value):
    rating = _parse_optional_int(value)
    if rating is None:
        return None
    if rating < 1 or rating > 5:
        raise ValueError("Skill ratings must be between 1 and 5.")
    return rating


def populate_applicant_from_request(applicant: GuardApplicant, request, *, parse_dates) -> list[str]:
    """Apply shared applicant fields from POST. Returns list of field names set."""
    applicant.first_name = request.POST.get("first_name", applicant.first_name or "").strip()
    applicant.last_name = request.POST.get("last_name", applicant.last_name or "").strip()
    applicant.email = request.POST.get("email", "").strip()
    applicant.phone_number = request.POST.get("phone_number", "").strip()
    applicant.alternate_phone = request.POST.get("alternate_phone", "").strip()
    applicant.source = request.POST.get("source", "").strip()
    applicant.address = request.POST.get("address", "").strip()
    applicant.city = request.POST.get("city", "").strip()
    applicant.country = request.POST.get("country", "").strip()
    applicant.gps_address = request.POST.get("gps_address", "").strip()
    applicant.nationality = request.POST.get("nationality", "").strip()
    applicant.national_id = request.POST.get("national_id", "").strip()
    applicant.gender = request.POST.get("gender", "").strip()
    applicant.marital_status = request.POST.get("marital_status", "").strip()
    applicant.background_check_status = request.POST.get("background_check_status", "").strip()
    applicant.interview_notes = request.POST.get("interview_notes", "").strip()
    applicant.rejection_reason = request.POST.get("rejection_reason", "").strip()
    applicant.emergency_contact_name = request.POST.get("emergency_contact_name", "").strip()
    applicant.emergency_contact_relationship = request.POST.get("emergency_contact_relationship", "").strip()
    applicant.emergency_contact_phone = request.POST.get("emergency_contact_phone", "").strip()
    applicant.emergency_contact_address = request.POST.get("emergency_contact_address", "").strip()
    applicant.convicted_of_crime = _parse_bool(request.POST.get("convicted_of_crime"))
    applicant.conviction_explanation = request.POST.get("conviction_explanation", "").strip()
    applicant.prior_security_experience = _parse_bool(request.POST.get("prior_security_experience"))
    applicant.uniform_size = request.POST.get("uniform_size", "").strip()
    applicant.assigned_branch = request.POST.get("assigned_branch", "").strip()
    applicant.declaration_signature_name = request.POST.get("declaration_signature_name", "").strip()
    applicant.interview_score = _parse_optional_decimal(request.POST.get("interview_score"))
    applicant.salary_expectation = _parse_optional_decimal(request.POST.get("salary_expectation"))

    dob_raw = request.POST.get("date_of_birth", "").strip()
    if dob_raw:
        applicant.date_of_birth = parse_dates(dob_raw, label="Date of birth")

    if request.FILES.get("photo"):
        applicant.photo = request.FILES["photo"]

    if _parse_bool(request.POST.get("declaration_signed")):
        applicant.declaration_signed_at = timezone.now()
        applicant.declaration_ip = request.META.get("REMOTE_ADDR")

    return [
        "first_name",
        "last_name",
        "email",
        "phone_number",
        "alternate_phone",
        "source",
        "address",
        "city",
        "country",
        "gps_address",
        "nationality",
        "national_id",
        "gender",
        "marital_status",
        "background_check_status",
        "interview_notes",
        "rejection_reason",
        "emergency_contact_name",
        "emergency_contact_relationship",
        "emergency_contact_phone",
        "emergency_contact_address",
        "convicted_of_crime",
        "conviction_explanation",
        "prior_security_experience",
        "uniform_size",
        "assigned_branch",
        "declaration_signature_name",
        "declaration_signed_at",
        "declaration_ip",
        "interview_score",
        "salary_expectation",
        "date_of_birth",
        "photo",
    ]


def populate_applicant_profile_from_request(applicant: GuardApplicant, request, *, parse_dates) -> GuardApplicantProfile:
    profile, _created = GuardApplicantProfile.objects.get_or_create(applicant=applicant)
    profile.security_training_completed = _parse_bool(request.POST.get("security_training_completed"))
    profile.fire_safety_training = _parse_bool(request.POST.get("fire_safety_training"))
    profile.first_aid_certification = _parse_bool(request.POST.get("first_aid_certification"))
    profile.cctv_monitoring_experience = _parse_bool(request.POST.get("cctv_monitoring_experience"))
    profile.access_control_experience = _parse_bool(request.POST.get("access_control_experience"))
    profile.military_police_background = _parse_bool(request.POST.get("military_police_background"))
    profile.driving_license_class = request.POST.get("driving_license_class", "").strip()
    profile.has_medical_condition = _parse_bool(request.POST.get("has_medical_condition"))
    profile.medical_condition_notes = request.POST.get("medical_condition_notes", "").strip()
    profile.has_physical_disability = _parse_bool(request.POST.get("has_physical_disability"))
    profile.physical_disability_notes = request.POST.get("physical_disability_notes", "").strip()
    profile.can_work_night_shifts = _parse_bool(request.POST.get("can_work_night_shifts"))
    profile.can_stand_long_hours = _parse_bool(request.POST.get("can_stand_long_hours"))
    profile.willing_to_travel = _parse_bool(request.POST.get("willing_to_travel"))
    profile.preferred_location = request.POST.get("preferred_location", "").strip()
    profile.shift_preference = request.POST.get("shift_preference", "").strip()
    profile.skill_communication = _parse_optional_skill_rating(request.POST.get("skill_communication"))
    profile.skill_report_writing = _parse_optional_skill_rating(request.POST.get("skill_report_writing"))
    profile.skill_computer = _parse_optional_skill_rating(request.POST.get("skill_computer"))
    profile.skill_radio = _parse_optional_skill_rating(request.POST.get("skill_radio"))
    profile.skill_conflict_resolution = _parse_optional_skill_rating(request.POST.get("skill_conflict_resolution"))
    profile.height_cm = _parse_optional_int(request.POST.get("height_cm"))
    profile.weight_kg = _parse_optional_int(request.POST.get("weight_kg"))

    start_raw = request.POST.get("available_start_date", "").strip()
    if start_raw:
        profile.available_start_date = parse_dates(start_raw, label="Available start date")

    profile.save()
    return profile
