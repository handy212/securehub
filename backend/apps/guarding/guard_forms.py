"""Helpers for guard profile forms in the operations console."""

from __future__ import annotations

from datetime import date

from .models import GuardProfile

METADATA_TEXT_FIELDS = (
    "national_id",
    "alternate_phone",
    "city",
    "country",
    "gps_address",
    "nationality",
    "gender",
    "marital_status",
    "emergency_contact_relationship",
    "assigned_branch",
    "uniform_size",
)


def guard_form_choices() -> dict:
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
    }


def metadata_value(guard: GuardProfile, key: str, default: str = "") -> str:
    if not guard or not guard.metadata:
        return default
    value = guard.metadata.get(key)
    if value is None:
        return default
    return str(value)


def populate_guard_profile_from_request(guard: GuardProfile, request, *, parse_optional_date) -> None:
    """Apply console guard create/edit fields including JSON metadata."""
    guard.phone_number = request.POST.get("phone_number", "").strip()
    guard.email = request.POST.get("email", "").strip()
    guard.home_address = request.POST.get("home_address", "").strip()
    guard.emergency_contact_name = request.POST.get("emergency_contact_name", "").strip()
    guard.emergency_contact_phone = request.POST.get("emergency_contact_phone", "").strip()
    guard.notes = request.POST.get("notes", "").strip()

    hire_date = parse_optional_date(request.POST.get("hire_date"), label="Hire date")
    if hire_date is not None:
        guard.hire_date = hire_date
    guard.termination_date = parse_optional_date(
        request.POST.get("termination_date"),
        label="Termination date",
    )

    metadata = dict(guard.metadata or {})
    for key in METADATA_TEXT_FIELDS:
        raw = request.POST.get(key, "").strip()
        if raw:
            metadata[key] = raw
        else:
            metadata.pop(key, None)

    dob = parse_optional_date(request.POST.get("date_of_birth"), label="Date of birth")
    if dob is not None:
        metadata["date_of_birth"] = dob.isoformat()
    else:
        metadata.pop("date_of_birth", None)

    salary = request.POST.get("salary_expectation", "").strip()
    if salary:
        metadata["salary_expectation"] = salary
    else:
        metadata.pop("salary_expectation", None)

    interview_score = request.POST.get("interview_score", "").strip()
    if interview_score:
        metadata["interview_score"] = interview_score
    else:
        metadata.pop("interview_score", None)

    guard.metadata = metadata


def parse_metadata_date(guard: GuardProfile) -> date | None:
    raw = metadata_value(guard, "date_of_birth")
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None
