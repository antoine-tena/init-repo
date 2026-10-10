"""Exporte le schéma OpenAPI de l'API ([OPENAPI]), source des types du frontend.

Lancée par `kiln contrat` (`--output ../openapi.json`) ; `--check` sert à la CI.
"""

import json
from argparse import ArgumentParser
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from config.api import api


class Command(BaseCommand):
    help = "Exporte le schéma OpenAPI de l'API au format JSON."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("--output", type=Path, required=True, help="Fichier de sortie.")
        parser.add_argument(
            "--check",
            action="store_true",
            help="N'écrit rien ; échoue si le fichier diffère du schéma du code.",
        )

    def handle(self, *args: object, **options: object) -> None:
        rendered_schema = render_schema()
        output_path = Path(str(options["output"]))
        if options["check"]:
            check_schema(output_path, rendered_schema)
            self.stdout.write(f"{output_path} est à jour.")
            return
        output_path.write_text(rendered_schema, encoding="utf-8")
        self.stdout.write(f"Schéma OpenAPI écrit dans {output_path}.")


def render_schema() -> str:
    """Rendu déterministe : deux exports du même code donnent le même fichier."""
    schema = api.get_openapi_schema()
    return json.dumps(schema, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def check_schema(output_path: Path, rendered_schema: str) -> None:
    regenerate = f"uv run python manage.py export_openapi --output {output_path}"
    if not output_path.exists():
        raise CommandError(f"{output_path} est absent. Lancer : {regenerate}")
    if output_path.read_text(encoding="utf-8") != rendered_schema:
        raise CommandError(
            f"{output_path} a dérivé du code. Lancer : {regenerate}, "
            "puis pnpm generate:api dans frontend/."
        )
