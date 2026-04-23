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

        payload = {
            "status": "ok" if db_ok else "degraded",
            "db": "ok" if db_ok else "error",
        }
        code = http_status.HTTP_200_OK if db_ok else http_status.HTTP_503_SERVICE_UNAVAILABLE
        return Response(payload, status=code)
