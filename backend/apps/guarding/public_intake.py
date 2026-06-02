"""Constants and validation for the public guard application flow."""

from django.http import HttpRequest

from .models import GuardApplicantDocument

PUBLIC_DOCUMENT_SLOTS = [
    {
        "type": GuardApplicantDocument.DocumentType.NATIONAL_ID,
        "title": "National ID",
        "label": "Ghana Card / National ID",
        "hint": "Upload a clear photo or PDF scan of your valid national ID.",
        "required": True,
        "accept": "image/*,.pdf",
    },
    {
        "type": GuardApplicantDocument.DocumentType.PHOTO,
        "title": "Passport photo",
        "label": "Passport photograph",
        "hint": "Recent head-and-shoulders photo on a plain background.",
        "required": True,
        "accept": "image/*",
    },
    {
        "type": GuardApplicantDocument.DocumentType.CV,
        "title": "CV / Resume",
        "label": "CV / Resume",
        "hint": "PDF or Word document listing your work history.",
        "required": True,
        "accept": ".pdf,.doc,.docx",
    },
    {
        "type": GuardApplicantDocument.DocumentType.POLICE_CLEARANCE,
        "title": "Police clearance",
        "label": "Police clearance certificate",
        "hint": "Upload if available; HR may request this later during screening.",
        "required": False,
        "accept": "image/*,.pdf",
    },
    {
        "type": GuardApplicantDocument.DocumentType.CERTIFICATE,
        "title": "Training certificate",
        "label": "Training / qualification certificate",
        "hint": "Security training, first aid, fire safety, or similar certificates.",
        "required": False,
        "accept": "image/*,.pdf",
    },
    {
        "type": GuardApplicantDocument.DocumentType.REFERENCE_LETTER,
        "title": "Reference letter",
        "label": "Reference letter (optional)",
        "hint": "Character or employment reference from a previous employer.",
        "required": False,
        "accept": "image/*,.pdf",
    },
]

REQUIRED_PUBLIC_DOCUMENT_TYPES = {
    slot["type"] for slot in PUBLIC_DOCUMENT_SLOTS if slot["required"]
}


def validate_public_documents(request: HttpRequest) -> None:
    types = request.POST.getlist("document_type")
    files = request.FILES.getlist("document_file")
    uploaded_types: set[str] = set()
    for doc_type, upload in zip(types, files, strict=False):
        if upload and upload.size > 0:
            uploaded_types.add(doc_type)

    missing_labels = [
        slot["label"]
        for slot in PUBLIC_DOCUMENT_SLOTS
        if slot["required"] and slot["type"] not in uploaded_types
    ]
    if missing_labels:
        raise ValueError(
            "Please upload the required documents: " + ", ".join(missing_labels) + "."
        )
