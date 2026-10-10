"""`kiln contrat` : openapi.json exporté du code Django, puis les types du front ([OPENAPI])."""

import os
from pathlib import Path

from kiln.shell import run, step
from kiln.stack import BACKEND_DIR, FRONTEND_DIR, Stack

SCHEMA_FILE = "openapi.json"
EXPORT_COMMAND = [
    "uv",
    "run",
    "python",
    "manage.py",
    "export_openapi",
    "--output",
    f"../{SCHEMA_FILE}",
]
GENERATE_COMMAND = ["pnpm", "generate:api"]
# L'export ne lit que le code : une clé factice suffit quand backend/.env manque (worktree, CI).
EXPORT_SECRET_KEY = "kiln-export-openapi"


def has_api_contract(stack: Stack) -> bool:
    return stack.backend == "django" and stack.frontend == "nuxt"


def generate_api_contract(root: Path, stack: Stack) -> None:
    if not has_api_contract(stack):
        return
    step("Contrat d'API : openapi.json et types du front")
    export_env = {"DJANGO_SECRET_KEY": EXPORT_SECRET_KEY, **os.environ}
    run(EXPORT_COMMAND, root / BACKEND_DIR, env=export_env)
    run(GENERATE_COMMAND, root / FRONTEND_DIR)
