"""DRF exception handler with request correlation id."""

from __future__ import annotations

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

REQUEST_ID_HEADER = "X-Request-ID"


def _request_id(request) -> str:
    if request is None:
        return ""
    return getattr(request, "request_id", "") or request.META.get(REQUEST_ID_HEADER, "")


def securehub_exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    request = context.get("request")
    request_id = _request_id(request)

    if response is not None:
        data = response.data
        if request_id:
            if isinstance(data, dict):
                data = {**data, "request_id": request_id}
            else:
                data = {"detail": data, "request_id": request_id}
            response.data = data
            response["X-Request-ID"] = request_id
        return response

    if request_id:
        return Response(
            {
                "detail": "An unexpected error occurred.",
                "request_id": request_id,
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            headers={REQUEST_ID_HEADER: request_id},
        )
    return None
