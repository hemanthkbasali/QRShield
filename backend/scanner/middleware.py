import logging

from django.core.exceptions import PermissionDenied, SuspiciousOperation
from django.http import Http404
from django.shortcuts import render


logger = logging.getLogger(__name__)


class FriendlyExceptionMiddleware:
    """Render a project error page instead of exposing traceback output."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        if isinstance(exception, (Http404, PermissionDenied)):
            return None
        if isinstance(exception, SuspiciousOperation):
            return render(
                request,
                "pages/error.html",
                {
                    "status_code": 400,
                    "title": "Request could not be processed",
                    "message": "Please review the submitted data and try again.",
                },
                status=400,
            )
        logger.error(
            "Unhandled QRShield request exception",
            exc_info=(type(exception), exception, exception.__traceback__),
        )
        return render(
            request,
            "pages/error.html",
            {
                "status_code": 500,
                "title": "Something went wrong",
                "message": "QRShield could not complete the request safely. Please try again from the scanner.",
            },
            status=500,
        )
