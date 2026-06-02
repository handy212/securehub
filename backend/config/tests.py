from django.core.cache import cache
from django.test import RequestFactory, TestCase, override_settings
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from config.exceptions import securehub_exception_handler


class HealthCheckViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_healthz_ok_when_db_and_cache_available(self):
        response = self.client.get("/healthz/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
        self.assertEqual(response.json()["db"], "ok")
        self.assertEqual(response.json()["cache"], "ok")

    @override_settings(
        CACHES={
            "default": {
                "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                "LOCATION": "healthz-broken-test",
            }
        }
    )
    def test_healthz_reports_cache_status(self):
        cache.clear()
        response = self.client.get("/healthz/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["cache"], "ok")


class ExceptionHandlerTests(TestCase):
    def test_validation_error_includes_request_id(self):
        request = RequestFactory().get("/api/v1/example/")
        request.request_id = "test-req-id"
        response = securehub_exception_handler(
            ValidationError("bad"),
            {"request": request, "view": None},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["request_id"], "test-req-id")
        self.assertEqual(response["X-Request-ID"], "test-req-id")
