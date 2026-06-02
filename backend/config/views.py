from django.core.cache import cache
from django.core.cache.backends.base import InvalidCacheBackendError
from django.db import connection
from django.db.utils import OperationalError
from rest_framework import status as http_status
from rest_framework.response import Response
from rest_framework.views import APIView


class ApiRootView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        return Response(
            {
                "service": "Alarm Hub Backend",
                "status": "ok",
                "message": "Alarm Hub API is running.",
                "endpoints": {
                    "root": "/",
                    "health": "/healthz/",
                    "admin": "/admin/",
                    "auth_login": "/api/v1/auth/login/",
                    "auth_refresh": "/api/v1/auth/refresh/",
                    "profile": "/api/v1/profile/",
                    "sites": "/api/v1/sites/",
                    "hik_health": "/api/v1/integrations/hik/health/",
                },
            }
        )


class HealthCheckView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        db_ok = True
        try:
            connection.ensure_connection()
        except OperationalError:
            db_ok = False

        cache_ok = True
        probe_key = "healthz-probe"
        try:
            cache.set(probe_key, "1", timeout=5)
            cache_ok = cache.get(probe_key) == "1"
            cache.delete(probe_key)
        except (InvalidCacheBackendError, OSError, ConnectionError):
            cache_ok = False

        healthy = db_ok and cache_ok
        payload = {
            "status": "ok" if healthy else "degraded",
            "db": "ok" if db_ok else "error",
            "cache": "ok" if cache_ok else "error",
        }
        code = (
            http_status.HTTP_200_OK
            if healthy
            else http_status.HTTP_503_SERVICE_UNAVAILABLE
        )
        return Response(payload, status=code)
