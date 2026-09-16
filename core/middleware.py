from django.conf import settings
from django.http import HttpResponseNotFound
from django.shortcuts import render

from content.models import SiteSetting


class OnlineTransactionsDisabledMiddleware:
    """Return a generic 404 for disabled transactional portal endpoints."""

    disabled_prefixes = ("/services/", "/appointments/", "/helpdesk/")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            not settings.ENABLE_ONLINE_TRANSACTIONS
            and request.path.startswith(self.disabled_prefixes)
        ):
            return HttpResponseNotFound("Page not found")
        return self.get_response(request)


class MaintenanceModeMiddleware:
    allowed_prefixes = ("/account/", "/dashboard/", "/secure-admin/", "/static/", "/media/", "/health/")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        enabled = SiteSetting.objects.filter(
            key="MAINTENANCE_MODE", value__iexact="true"
        ).exists()
        if enabled and not request.path.startswith(self.allowed_prefixes):
            return render(request, "errors/maintenance.html", status=503)
        return self.get_response(request)


class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com https://unpkg.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; "
            "object-src 'none'; base-uri 'self'; form-action 'self'",
        )
        response.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=(self)")
        response.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        return response
