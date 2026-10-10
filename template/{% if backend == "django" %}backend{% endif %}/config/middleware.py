"""En-tête Permissions-Policy ([EN-TETES]), que Django ne pose pas lui-même."""

from collections.abc import Callable

from django.http import HttpRequest, HttpResponse

# Fonctions du navigateur refusées à toutes les pages : à ouvrir une par une, au besoin.
PERMISSIONS_POLICY = "camera=(), geolocation=(), microphone=(), payment=(), usb=()"


class PermissionsPolicyMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        response.headers.setdefault("Permissions-Policy", PERMISSIONS_POLICY)
        return response
