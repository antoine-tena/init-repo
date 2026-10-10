import pytest
from django.db import DatabaseError, connection
from django.test import Client

from config import health


def test_health_returns_ok(client: Client) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.django_db
def test_ready_returns_ok_when_database_answers(client: Client) -> None:
    response = client.get("/api/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_returns_503_when_database_is_down(
    client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("config.api.is_database_reachable", lambda: False)

    response = client.get("/api/ready")

    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}


def test_database_check_reports_a_failed_connection(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse_connection() -> None:
        raise DatabaseError

    monkeypatch.setattr(connection, "ensure_connection", refuse_connection)

    assert health.is_database_reachable() is False
