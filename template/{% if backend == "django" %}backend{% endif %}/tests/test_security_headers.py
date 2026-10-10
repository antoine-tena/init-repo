"""En-têtes de sécurité de toute réponse ([EN-TETES], [CSP-NONCE])."""

from django.conf import settings
from django.test import Client
from django.utils.csp import CSP


def test_https_response_carries_security_headers(client: Client) -> None:
    response = client.get("/api/health", secure=True)

    assert response.headers["Strict-Transport-Security"] == (
        "max-age=31536000; includeSubDomains; preload"
    )
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert response.headers["Cross-Origin-Opener-Policy"] == "same-origin"
    assert "camera=()" in response.headers["Permissions-Policy"]


def test_csp_forbids_inline_code_and_third_party_hosts(client: Client) -> None:
    policy = client.get("/api/health").headers["Content-Security-Policy"]

    assert "default-src 'self'" in policy
    assert "script-src 'self'" in policy
    assert "unsafe-inline" not in policy
    assert "unsafe-eval" not in policy
    assert "*" not in policy


def test_inline_scripts_and_styles_need_the_request_nonce() -> None:
    # Django n'écrit le nonce dans l'en-tête que si la page s'en sert.
    assert CSP.NONCE in settings.SECURE_CSP["script-src"]
    assert CSP.NONCE in settings.SECURE_CSP["style-src"]
