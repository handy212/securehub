"""Small helpers shared by guarding console views."""

from __future__ import annotations

from apps.dashboard.parsers import parse_optional_date_field
from apps.guarding.guard_forms import populate_guard_profile_from_request
from apps.guarding.models import GuardCredential
from apps.guarding.services import apply_credential_verification, guard_compliance_issues


def populate_guard_profile_from_post(guard, request) -> None:
    populate_guard_profile_from_request(
        guard,
        request,
        parse_optional_date=parse_optional_date_field,
    )


def attach_guard_compliance_flags(guards) -> None:
    for guard in guards:
        guard.compliance_issues = guard_compliance_issues(guard)
        guard.is_compliance_ready = not guard.compliance_issues


def apply_credential_from_post(credential, request, *, actor) -> None:
    credential.credential_type = (
        request.POST.get("credential_type") or GuardCredential.CredentialType.OTHER
    )
    credential.name = request.POST.get("name", "").strip()
    credential.issuing_authority = request.POST.get("issuing_authority", "").strip()
    credential.reference_number = request.POST.get("reference_number", "").strip()
    credential.issued_on = request.POST.get("issued_on") or None
    credential.expires_on = request.POST.get("expires_on") or None
    credential.notes = request.POST.get("notes", "").strip()
    apply_credential_verification(
        credential,
        verified=bool(request.POST.get("verified")),
        actor=actor,
    )
