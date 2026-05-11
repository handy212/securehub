from datetime import timedelta
from pathlib import Path
import os
import sys

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY",
    "alarmhub-dev-secret-key-change-me-before-production-2026",
)
DEBUG = os.getenv("DJANGO_DEBUG", "True").lower() == "true"
TESTING = "test" in sys.argv
QUIET_TEST_LOGS = os.getenv(
    "DJANGO_QUIET_TEST_LOGS",
    "True" if TESTING else "False",
).lower() == "true"

ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")
    if host.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "drf_spectacular",
    "apps.accounts",
    "apps.sites",
    "apps.alarms",
    "apps.hik_adapter",
    "apps.dashboard.apps.DashboardConfig",
    "apps.communication",
    "apps.emergency",
    "apps.guarding.apps.GuardingConfig",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "config.middleware.RequestCorrelationMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "config.middleware.ConsoleAuthMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.dashboard.context_processors.global_dashboard_stats",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

USE_SQLITE = os.getenv("DJANGO_USE_SQLITE", "True").lower() == "true"

if USE_SQLITE:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
            "OPTIONS": {
                "timeout": 30,
            },
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("DJANGO_DB_NAME", "alarmhub"),
            "USER": os.getenv("DJANGO_DB_USER", "postgres"),
            "PASSWORD": os.getenv("DJANGO_DB_PASSWORD", "postgres"),
            "HOST": os.getenv("DJANGO_DB_HOST", "127.0.0.1"),
            "PORT": os.getenv("DJANGO_DB_PORT", "5432"),
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": (
            "whitenoise.storage.CompressedManifestStaticFilesStorage"
            if not DEBUG
            else "django.contrib.staticfiles.storage.StaticFilesStorage"
        ),
    },
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "60/min",
        "user": "600/min",
        "site_poll": "1200/min",
        "login": "10/min",
    },
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Alarm Hub API",
    "DESCRIPTION": "REST API for SecureHub alarm management.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SCHEMA_PATH_PREFIX": "/api/v1/",
}

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://127.0.0.1:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", CELERY_BROKER_URL)
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 300  # seconds
CELERY_TASK_DEFAULT_QUEUE = "celery"
CELERY_TASK_CREATE_MISSING_QUEUES = True
CELERY_WORKER_PREFETCH_MULTIPLIER = int(os.getenv("CELERY_WORKER_PREFETCH_MULTIPLIER", "1"))
CELERY_TASK_ROUTES = {
    "apps.alarms.tasks.process_webhook_messages": {"queue": "webhook"},
}
# Set CELERY_TASK_ALWAYS_EAGER=True in .env to run tasks synchronously (no worker needed — dev only).
CELERY_TASK_ALWAYS_EAGER = os.getenv("CELERY_TASK_ALWAYS_EAGER", "False").lower() == "true"
CELERY_TASK_EAGER_PROPAGATES = CELERY_TASK_ALWAYS_EAGER

HIK_DELIVERY_MODE = os.getenv("HIK_PARTNER_DELIVERY_MODE", "mq").lower()
HIK_MQ_POLL_INTERVAL_SECONDS = float(os.getenv("HIK_MQ_POLL_INTERVAL_SECONDS", "25"))
HIK_DEVICE_HEALTH_INTERVAL_SECONDS = float(os.getenv("HIK_DEVICE_HEALTH_INTERVAL_SECONDS", "300"))
HIK_STATUS_SYNC_INTERVAL_SECONDS = float(os.getenv("HIK_STATUS_SYNC_INTERVAL_SECONDS", "300"))

CELERY_BEAT_SCHEDULE = {
    # Run once every 24 hours — mark overdue subscriptions and auto-suspend
    "check-subscription-statuses": {
        "task": "apps.alarms.tasks.check_subscription_statuses",
        "schedule": 86400.0,
    },
    # Run once every 24 hours — send payment due reminders
    "send-payment-reminders": {
        "task": "apps.alarms.tasks.send_payment_reminders",
        "schedule": 86400.0,
    },
    # Guard operations: close missed rounds/checks, raise SLA events, and notify guards.
    "run-guarding-automation": {
        "task": "apps.guarding.tasks.run_guarding_automation",
        "schedule": 60.0,
    },
}

if HIK_DELIVERY_MODE == "mq" and HIK_MQ_POLL_INTERVAL_SECONDS > 0:
    # MQ long-poll blocks up to 20 s when no events are pending.
    CELERY_BEAT_SCHEDULE["poll-mq-events"] = {
        "task": "apps.alarms.tasks.poll_mq_events",
        "schedule": HIK_MQ_POLL_INTERVAL_SECONDS,
    }

if HIK_DEVICE_HEALTH_INTERVAL_SECONDS > 0:
    # Poll device/zone health (battery, tamper, online status).
    CELERY_BEAT_SCHEDULE["poll-device-health"] = {
        "task": "apps.alarms.tasks.poll_device_health",
        "schedule": HIK_DEVICE_HEALTH_INTERVAL_SECONDS,
    }

if HIK_STATUS_SYNC_INTERVAL_SECONDS > 0:
    # Sync zone states (open/close/arm) from ISAPI as a safety net for webhook delivery.
    CELERY_BEAT_SCHEDULE["sync-alarm-status"] = {
        "task": "apps.alarms.tasks.sync_all_alarm_status",
        "schedule": HIK_STATUS_SYNC_INTERVAL_SECONDS,
    }

# Email
EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"
)
EMAIL_HOST = os.getenv("EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "25"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "False").lower() == "true"
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "noreply@securehub.local")
SECUREHUB_APP_LINKS = {
    "android": os.getenv("SECUREHUB_ANDROID_APP_URL", ""),
    "ios": os.getenv("SECUREHUB_IOS_APP_URL", ""),
    "web": os.getenv("SECUREHUB_WEB_APP_URL", ""),
    "support": os.getenv("SECUREHUB_SUPPORT_URL", ""),
}
SECUREHUB_EMERGENCY_SMS_RECIPIENTS = os.getenv("SECUREHUB_EMERGENCY_SMS_RECIPIENTS", "")
SECUREHUB_EMERGENCY_SMS_PROVIDER = os.getenv("SECUREHUB_EMERGENCY_SMS_PROVIDER", "hubtel")
SECUREHUB_EMERGENCY_SMS_WEBHOOK_URL = os.getenv("SECUREHUB_EMERGENCY_SMS_WEBHOOK_URL", "")
SECUREHUB_GOOGLE_AUTO_CREATE_USERS = os.getenv(
    "SECUREHUB_GOOGLE_AUTO_CREATE_USERS",
    "False",
).lower() == "true"

HIK_PARTNER = {
    "BASE_URL": os.getenv("HIK_PARTNER_BASE_URL", ""),
    "API_KEY": os.getenv("HIK_PARTNER_API_KEY", ""),
    "API_SECRET": os.getenv("HIK_PARTNER_API_SECRET", ""),
    "WEBHOOK_SIGN_SECRET": os.getenv("HIK_PARTNER_WEBHOOK_SIGN_SECRET", ""),
    "DELIVERY_MODE": os.getenv("HIK_PARTNER_DELIVERY_MODE", "mq").lower(),
    "DRY_RUN": os.getenv("HIK_PARTNER_DRY_RUN", "True").lower() == "true",
    "STATUS_TIMEOUT": int(os.getenv("HIK_PARTNER_STATUS_TIMEOUT", "20")),
}

SITE_GEOCODING = {
    "ENABLED": os.getenv("SITE_GEOCODING_ENABLED", "True").lower() == "true",
    "URL": os.getenv("SITE_GEOCODING_URL", "https://nominatim.openstreetmap.org/search"),
    "USER_AGENT": os.getenv("SITE_GEOCODING_USER_AGENT", "securehub/1.0"),
    "TIMEOUT": int(os.getenv("SITE_GEOCODING_TIMEOUT", "10")),
}

# Firebase Cloud Messaging
# Set FIREBASE_CREDENTIALS_PATH to the absolute path of your service account JSON file,
# or use Google Application Default Credentials / GOOGLE_APPLICATION_CREDENTIALS.
# Store backend service-account JSON outside the repository.
# Leave empty to disable FCM push notifications (email/log delivery still works).
FIREBASE_CREDENTIALS_PATH = os.getenv("FIREBASE_CREDENTIALS_PATH", "")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")

# Hubtel SMS
HUBTEL_CLIENT_ID = os.getenv("HUBTEL_CLIENT_ID", "")
HUBTEL_CLIENT_SECRET = os.getenv("HUBTEL_CLIENT_SECRET", "")
HUBTEL_SENDER_NAME = os.getenv("HUBTEL_SENDER_NAME", "SecureHub")
ENABLE_API_DOCS = os.getenv("ENABLE_API_DOCS", "True" if DEBUG else "False").lower() == "true"

# CORS configuration
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000").split(",")
    if origin.strip()
]

# Security headers and cookie settings
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")
CSRF_COOKIE_SAMESITE = os.getenv("CSRF_COOKIE_SAMESITE", "Lax")

if not DEBUG:
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
            "level": "CRITICAL" if QUIET_TEST_LOGS else "NOTSET",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "ERROR" if QUIET_TEST_LOGS else "WARNING",
    },
    "loggers": {
        "apps": {
            "handlers": ["console"],
            "level": "CRITICAL" if QUIET_TEST_LOGS else ("DEBUG" if DEBUG else "INFO"),
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR" if QUIET_TEST_LOGS else "WARNING",
            "propagate": False,
        },
        "django.server": {
            "handlers": ["console"],
            "level": "ERROR" if QUIET_TEST_LOGS else "WARNING",
            "propagate": False,
        },
        "celery": {
            "handlers": ["console"],
            "level": "ERROR" if QUIET_TEST_LOGS else "WARNING",
            "propagate": False,
        },
    },
}
