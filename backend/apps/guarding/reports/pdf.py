"""PDF exports for patrol proof and field reports."""

from __future__ import annotations

from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def render_patrol_round_pdf(patrol_round) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, title="Patrol Proof")
    styles = getSampleStyleSheet()
    story = [
        Paragraph("SecureHub — Patrol Proof Report", styles["Title"]),
        Spacer(1, 12),
        Paragraph(f"Site: {patrol_round.route.post.site.name}", styles["Normal"]),
        Paragraph(f"Post: {patrol_round.route.post.name}", styles["Normal"]),
        Paragraph(f"Route: {patrol_round.route.name}", styles["Normal"]),
        Paragraph(f"Status: {patrol_round.get_status_display()}", styles["Normal"]),
        Paragraph(
            f"Scheduled: {patrol_round.scheduled_start:%Y-%m-%d %H:%M}"
            + (f" – {patrol_round.scheduled_end:%H:%M}" if patrol_round.scheduled_end else ""),
            styles["Normal"],
        ),
        Spacer(1, 16),
    ]
    guard_name = patrol_round.assignment.guard.full_name if patrol_round.assignment else "—"
    story.append(Paragraph(f"Guard: {guard_name}", styles["Heading2"]))
    story.append(Spacer(1, 8))

    scans = list(patrol_round.scans.select_related("checkpoint").order_by("scanned_at"))
    rows = [["Checkpoint", "Scanned at", "In geofence"]]
    for scan in scans:
        rows.append(
            [
                scan.checkpoint.name,
                scan.scanned_at.strftime("%Y-%m-%d %H:%M"),
                "Yes" if scan.within_geofence else "Review",
            ]
        )
    if len(rows) == 1:
        rows.append(["—", "No scans recorded", "—"])

    table = Table(rows, colWidths=[200, 120, 80])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ]
        )
    )
    story.append(table)
    doc.build(story)
    return buffer.getvalue()


def _yes_no(value) -> str:
    return "Yes" if value else "No"


def _dash(value) -> str:
    if value is None or value == "":
        return "—"
    return str(value)


def _section_table(rows: list[list[str]], col_widths=None) -> Table:
    table = Table(rows, colWidths=col_widths or [160, 320])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return table


def render_guard_applicant_pdf(applicant) -> bytes:
    """Full application packet for HR review."""
    from apps.guarding.models import GuardApplicant

    applicant = (
        GuardApplicant.objects.select_related("profile", "hired_guard")
        .prefetch_related("documents", "education_records", "employment_records", "references")
        .get(pk=applicant.pk)
    )
    profile = getattr(applicant, "profile", None)

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, title="Guard Application")
    styles = getSampleStyleSheet()
    story = [
        Paragraph("SecureHub — Security Guard Application", styles["Title"]),
        Spacer(1, 8),
        Paragraph(f"Applicant: {applicant.full_name}", styles["Heading2"]),
        Paragraph(
            f"Status: {applicant.get_status_display()} · Source: {_dash(applicant.source)} · "
            f"Submitted: {applicant.created_at:%Y-%m-%d %H:%M}",
            styles["Normal"],
        ),
        Spacer(1, 12),
    ]

    personal = [
        ["Field", "Value"],
        ["Phone", _dash(applicant.phone_number)],
        ["Alt phone", _dash(applicant.alternate_phone)],
        ["Email", _dash(applicant.email)],
        ["Date of birth", applicant.date_of_birth.isoformat() if applicant.date_of_birth else "—"],
        ["Gender", _dash(applicant.gender)],
        ["Nationality", _dash(applicant.nationality)],
        ["National ID", _dash(applicant.national_id)],
        ["Marital status", _dash(applicant.marital_status)],
        ["Address", _dash(applicant.address)],
        ["City / Country", f"{_dash(applicant.city)} / {_dash(applicant.country)}"],
        ["GPS", _dash(applicant.gps_address)],
    ]
    story.append(Paragraph("Personal information", styles["Heading3"]))
    story.append(Spacer(1, 6))
    story.append(_section_table(personal))
    story.append(Spacer(1, 12))

    emergency = [
        ["Field", "Value"],
        ["Name", _dash(applicant.emergency_contact_name)],
        ["Relationship", _dash(applicant.emergency_contact_relationship)],
        ["Phone", _dash(applicant.emergency_contact_phone)],
        ["Address", _dash(applicant.emergency_contact_address)],
    ]
    story.append(Paragraph("Emergency contact", styles["Heading3"]))
    story.append(Spacer(1, 6))
    story.append(_section_table(emergency))
    story.append(Spacer(1, 12))

    if profile:
        qualifications = [
            ["Item", "Value"],
            ["Security training", _yes_no(profile.security_training_completed)],
            ["Fire safety", _yes_no(profile.fire_safety_training)],
            ["First aid", _yes_no(profile.first_aid_certification)],
            ["CCTV experience", _yes_no(profile.cctv_monitoring_experience)],
            ["Access control", _yes_no(profile.access_control_experience)],
            ["Military/police", _yes_no(profile.military_police_background)],
            ["Driving license", _dash(profile.driving_license_class)],
            ["Height / Weight", f"{_dash(profile.height_cm)} cm / {_dash(profile.weight_kg)} kg"],
            ["Medical condition", _yes_no(profile.has_medical_condition)],
            ["Medical notes", _dash(profile.medical_condition_notes)],
            ["Disability", _yes_no(profile.has_physical_disability)],
            ["Disability notes", _dash(profile.physical_disability_notes)],
            ["Night shifts", _yes_no(profile.can_work_night_shifts)],
            ["Long hours", _yes_no(profile.can_stand_long_hours)],
            ["Shift preference", _dash(profile.get_shift_preference_display() if profile.shift_preference else "")],
            ["Available from", profile.available_start_date.isoformat() if profile.available_start_date else "—"],
            ["Preferred location", _dash(profile.preferred_location)],
            ["Willing to travel", _yes_no(profile.willing_to_travel)],
            ["Skills (1-5)", (
                f"Comm {profile.skill_communication or '—'}, "
                f"Reports {profile.skill_report_writing or '—'}, "
                f"PC {profile.skill_computer or '—'}, "
                f"Radio {profile.skill_radio or '—'}, "
                f"Conflict {profile.skill_conflict_resolution or '—'}"
            )],
        ]
        story.append(Paragraph("Qualifications, medical & availability", styles["Heading3"]))
        story.append(Spacer(1, 6))
        story.append(_section_table(qualifications))
        story.append(Spacer(1, 12))

    criminal = [
        ["Field", "Value"],
        ["Prior security experience", _yes_no(applicant.prior_security_experience)],
        ["Convicted of crime", _yes_no(applicant.convicted_of_crime)],
        ["Explanation", _dash(applicant.conviction_explanation)],
        ["Uniform size", _dash(applicant.uniform_size)],
        ["Salary expectation", _dash(applicant.salary_expectation)],
    ]
    story.append(Paragraph("Experience & declaration", styles["Heading3"]))
    story.append(Spacer(1, 6))
    story.append(_section_table(criminal))
    story.append(Spacer(1, 8))
    signed = applicant.declaration_signed_at.strftime("%Y-%m-%d %H:%M") if applicant.declaration_signed_at else "—"
    story.append(
        Paragraph(
            f"Declaration: {_dash(applicant.declaration_signature_name)} · Signed {signed}",
            styles["Normal"],
        )
    )
    story.append(Spacer(1, 12))

    edu_rows = [["Level", "Institution", "Year", "Certificates"]]
    for edu in applicant.education_records.all():
        edu_rows.append(
            [
                edu.education_level,
                _dash(edu.institution_name),
                _dash(edu.year_completed),
                _dash(edu.certificates_obtained)[:80],
            ]
        )
    if len(edu_rows) == 1:
        edu_rows.append(["—", "—", "—", "—"])
    story.append(Paragraph("Education", styles["Heading3"]))
    story.append(Spacer(1, 6))
    story.append(_section_table(edu_rows, [100, 140, 50, 190]))
    story.append(Spacer(1, 12))

    emp_rows = [["Company", "Position", "Period"]]
    for emp in applicant.employment_records.all():
        period = "—"
        if emp.started_on or emp.ended_on:
            start = emp.started_on.isoformat() if emp.started_on else "?"
            end = emp.ended_on.isoformat() if emp.ended_on else "present"
            period = f"{start} – {end}"
        emp_rows.append([emp.company_name, _dash(emp.position), period])
    if len(emp_rows) == 1:
        emp_rows.append(["—", "—", "—"])
    story.append(Paragraph("Employment history", styles["Heading3"]))
    story.append(Spacer(1, 6))
    story.append(_section_table(emp_rows, [160, 140, 180]))
    story.append(Spacer(1, 12))

    ref_rows = [["Name", "Company", "Phone"]]
    for ref in applicant.references.all():
        ref_rows.append([ref.full_name, _dash(ref.company), _dash(ref.phone_number)])
    if len(ref_rows) == 1:
        ref_rows.append(["—", "—", "—"])
    story.append(Paragraph("References", styles["Heading3"]))
    story.append(Spacer(1, 6))
    story.append(_section_table(ref_rows, [140, 180, 160]))
    story.append(Spacer(1, 12))

    doc_rows = [["Type", "Title", "Uploaded"]]
    for document in applicant.documents.all():
        doc_rows.append(
            [
                document.get_document_type_display(),
                document.title,
                document.created_at.strftime("%Y-%m-%d"),
            ]
        )
    if len(doc_rows) == 1:
        doc_rows.append(["—", "—", "—"])
    story.append(Paragraph("Documents", styles["Heading3"]))
    story.append(Spacer(1, 6))
    story.append(_section_table(doc_rows, [120, 200, 160]))

    doc.build(story)
    return buffer.getvalue()
