"""Export du schéma OpenAPI et détection de sa dérive ([OPENAPI], [DERIVE])."""

from io import StringIO
from pathlib import Path

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

COMMITTED_SCHEMA = Path(__file__).resolve().parents[2] / "openapi.json"


def export(output_path: Path, *options: str) -> None:
    call_command("export_openapi", *options, "--output", str(output_path), stdout=StringIO())


def test_export_is_deterministic(tmp_path: Path) -> None:
    export(tmp_path / "first.json")
    export(tmp_path / "second.json")

    assert (tmp_path / "first.json").read_text() == (tmp_path / "second.json").read_text()


def test_check_fails_when_schema_drifted(tmp_path: Path) -> None:
    schema_path = tmp_path / "openapi.json"
    schema_path.write_text("{}\n")

    with pytest.raises(CommandError, match="a dérivé"):
        export(schema_path, "--check")


def test_committed_schema_matches_the_code() -> None:
    if not COMMITTED_SCHEMA.exists():
        pytest.skip("openapi.json pas encore généré (kiln update le crée)")
    export(COMMITTED_SCHEMA, "--check")
