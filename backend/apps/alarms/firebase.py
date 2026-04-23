import logging

logger = logging.getLogger(__name__)


def get_firebase_messaging():
    """
    Return the firebase_admin.messaging module if Firebase Admin can be
    initialized, otherwise return None.

    Supports either:
    - FIREBASE_CREDENTIALS_PATH pointing to a service-account JSON file, or
    - Application Default Credentials / GOOGLE_APPLICATION_CREDENTIALS
    """
    from django.conf import settings

    try:
        import firebase_admin
        from firebase_admin import credentials, messaging
    except ImportError:
        logger.warning("FCM: firebase-admin is not installed; skipping push")
        return None

    try:
        firebase_admin.get_app()
        return messaging
    except ValueError:
        pass

    cred_path = (getattr(settings, "FIREBASE_CREDENTIALS_PATH", "") or "").strip()
    try:
        if cred_path:
            firebase_admin.initialize_app(credentials.Certificate(cred_path))
        else:
            firebase_admin.initialize_app()
        return messaging
    except Exception as exc:
        logger.warning(
            "FCM: Firebase Admin is not configured. Set FIREBASE_CREDENTIALS_PATH "
            "to an external service-account JSON file or configure ADC/"
            "GOOGLE_APPLICATION_CREDENTIALS. Error: %s",
            exc,
        )
        return None
