import os
from pathlib import Path

from django.conf import settings
from django.core.checks import Error, Tags, Warning, register

DEFAULT_DEV_SECRET_KEY = "alarmhub-dev-secret-key-change-me-before-production-2026"


def _validate_credentials_path(path_value: str, *, label: str, base_dir: Path):
    errors = []
    if not path_value:
        return errors

    credentials_path = Path(path_value).expanduser()
    if not credentials_path.is_absolute():
        errors.append(
            Warning(
                f"{label} should be an absolute path.",
                hint="Store the Firebase service-account JSON outside the repository and point this setting to that absolute path.",
                id="securehub.W001",
            )
        )
        credentials_path = (base_dir / credentials_path).resolve()
    else:
        credentials_path = credentials_path.resolve()

    if credentials_path.is_relative_to(base_dir):
        errors.append(
            Error(
                f"{label} points inside the repository.",
                hint="Move the Firebase service-account JSON outside the repo and update FIREBASE_CREDENTIALS_PATH.",
                id="securehub.E001",
            )
        )

    if not credentials_path.exists():
        errors.append(
            Error(
                f"{label} does not exist.",
                hint="Create the Firebase service-account JSON outside the repo and point FIREBASE_CREDENTIALS_PATH to it.",
                id="securehub.E002",
            )
        )

    return errors


@register(Tags.security)
def firebase_credentials_path_check(app_configs, **kwargs):
    base_dir = Path(settings.BASE_DIR).resolve()
    errors = []
    errors.extend(
        _validate_credentials_path(
            (getattr(settings, "FIREBASE_CREDENTIALS_PATH", "") or "").strip(),
            label="FIREBASE_CREDENTIALS_PATH",
            base_dir=base_dir,
        )
    )
    errors.extend(
        _validate_credentials_path(
            (os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "") or "").strip(),
            label="GOOGLE_APPLICATION_CREDENTIALS",
            base_dir=base_dir,
        )
    )
    return errors


@register(Tags.security)
def production_secret_key_check(app_configs, **kwargs):
    if getattr(settings, "DEBUG", False) or getattr(settings, "TESTING", False):
        return []

    if getattr(settings, "SECRET_KEY", "") == DEFAULT_DEV_SECRET_KEY:
        return [
            Error(
                "DJANGO_SECRET_KEY is using the built-in development fallback while DEBUG is disabled.",
                hint="Set a unique production secret via DJANGO_SECRET_KEY before deploying.",
                id="securehub.E003",
            )
        ]

    return []
