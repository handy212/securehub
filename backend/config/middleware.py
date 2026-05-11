import uuid
from urllib.parse import urlencode
from django.shortcuts import redirect


class ConsoleAuthMiddleware:
    """
    Protects every URL under /console/ with session-based authentication.
    Unauthenticated requests are redirected to /console/login/.
    The login and logout URLs themselves are always accessible.
    """

    OPEN_PATHS = {"/console/login/", "/console/logout/"}
    OPEN_PREFIXES = ("/console/password-reset/",)

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            request.path.startswith("/console/")
            and request.path not in self.OPEN_PATHS
            and not request.path.startswith(self.OPEN_PREFIXES)
            and not request.user.is_authenticated
        ):
            query = urlencode({"next": request.get_full_path()})
            return redirect(f"/console/login/?{query}")
        return self.get_response(request)


class RequestCorrelationMiddleware:
    """
    Propagates or generates an X-Request-ID header on every response.
    If the client sends X-Request-ID it is echoed back; otherwise a new UUID4
    is generated. The value is available as ``request.request_id`` inside views.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.request_id = request_id
        response = self.get_response(request)
        response["X-Request-ID"] = request_id
        return response
